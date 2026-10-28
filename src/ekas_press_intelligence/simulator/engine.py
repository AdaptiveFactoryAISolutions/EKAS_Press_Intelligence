"""One-second hybrid stamping cell. Truth is returned only to the evaluator.

Discrete strokes consume one strip pitch and create exactly one good/scrap part.
Continuous pressure uses the preserved upstream controller and RK4 integrator.
"""
from dataclasses import dataclass
import math
import numpy as np
from historiansim.core.rng import SeedBank
from historiansim.core.noise import ou_noise
from historiansim.core.pid import PID
from historiansim.core.integrator import rk4_step
from historiansim.config.schema import LoopConfig
from ekas_press_intelligence.domain import catalog, profile_signals
from ekas_press_intelligence.acquisition import AcquisitionMonitor, RULES

@dataclass
class SimulationResult:
    evidence: dict
    truth: list

def _schedule(duration, events, repair):
    cat={e["event_class"]:e for e in catalog()}
    if events is None:
        # Fixed two-hour baseline, ample independent recovery between episodes.
        spacing=(duration-7800)/len(cat)
        events=[] if spacing<=0 else [dict(event_class=c,start_s=int(7200+i*spacing),end_s=int(7200+i*spacing+min(1800,spacing*.6)),severity=1) for i,c in enumerate(cat)]
    result=[]
    for e in events:
        if e['event_class'] not in cat: raise ValueError('unknown event class')
        start,end=int(e['start_s']),int(e['end_s'])
        if not 0<=start<end<=duration: raise ValueError('event interval outside simulation')
        sev=float(e.get('severity',1))
        if not 0<sev<=1: raise ValueError('severity must be in (0,1]')
        end=min(end,int(repair)) if repair is not None and repair>start else end
        result.append(dict(cat[e['event_class']],start_s=start,end_s=end,severity=sev))
    return result

def simulate(seed=7,duration_s=86400,profile='sparse',events=None,repair_at_s=None):
    if not isinstance(duration_s,int) or duration_s<1: raise ValueError('duration_s must be positive integer seconds')
    selected=profile_signals(profile)
    truth=_schedule(duration_s,events,repair_at_s)
    bank=SeedBank(seed)
    speed_noise=ou_noise(duration_s,.15,12,1,bank.get('speed'))
    feed_noise=ou_noise(duration_s,.08,3,1,bank.get('feed'))
    analog_noise=ou_noise(duration_s,.025,20,1,bank.get('pressure'))
    load_noise=ou_noise(duration_s,.3,8,1,bank.get('load'))
    rejects=bank.get('quality').random(duration_s)
    cfg=LoopConfig(name='lube control',pv_source='lube_pressure',mv_tag='pump',kc=.2,ti=25,sp=5,man_output=.5)
    pump=PID(cfg,pv0=5,out0=.5)
    pressure=5.; loop=1.; phase=0.; strokes=good=scrap=0; progression=0
    acquisition=AcquisitionMonitor()
    history=[]; samples=[]; records=[]; quality=[]; previous_state=None; previous_rate=60.; stuck_value=None
    for t in range(duration_s):
        active={e['event_class']:e for e in truth if e['start_s']<=t<e['end_s']}
        def level(c):
            e=active.get(c)
            return 0. if e is None else e['severity']*min(1.,(t-e['start_s']+1)/max(30,min(300,(e['end_s']-e['start_s'])*.3)))
        drift=level('feeder_sensor_drift'); instability=level('feeder_mechanical_instability')
        wear=level('progressive_die_wear'); loss=level('lubrication_pressure_loss')
        starvation=level('material_starvation'); decoiler=level('decoiler_interruption')
        rate=42. if 'operator_speed_change' in active else 60.
        if rate!=previous_rate:
            records.append(dict(t=t,type='operator_speed_setpoint',message=f'Authorized speed setpoint {rate:g} SPM',rate_spm=rate))
        previous_rate=rate
        planned='planned_stop' in active
        if planned and t==active['planned_stop']['start_s']:
            records.append(dict(t=t,type='planned_changeover',message='Scheduled die inspection and changeover'))
        # Buffer stock is replenished by decoiler and consumed only on strokes.
        supply=max(0.,1-1.4*max(starvation,decoiler))
        # Decoiler loop controller includes recovery reserve above normal draw.
        incoming_pitch_m=(.002+max(0.,1.-loop)*.004)*supply
        loop=min(1.5,max(0.,loop+incoming_pitch_m))
        material=loop>.12
        feedback_error=drift*2.5+instability*(1.8*math.sin(t*1.7)+1.1*math.sin(t*.31))+float(feed_noise[t])
        obstruction=level('misfeed')>.5 and t%24<12
        feed_complete=material and abs(feedback_error)<1.5 and not obstruction
        intermittent='repeated_microstops' in active and t%37<7
        feed_complete=feed_complete and not intermittent
        measured_pressure=pressure+float(analog_noise[t])
        output=pump.step(measured_pressure,1)
        pressure=float(rk4_step(lambda _t,x: np.array([(output*10-x[0])/12-loss*.85]),t,np.array([pressure]),1)[0])
        pressure=max(0.,pressure)
        lube_ok=pressure>2
        load=100+wear*20+level('abnormal_tonnage')*45+(5-pressure)*3+float(load_noise[t])
        die_trip=('die_protection_trip' in active and t%45<20) or obstruction
        overload=load>135
        blocked=not feed_complete or not lube_ok or die_trip or overload
        running=not planned and not blocked
        drive=level('press_speed_degradation')
        achieved=max(0.,rate*(1-.35*drive)+float(speed_noise[t])) if running else 0.
        # A phase accumulator makes integer stroke events even at fractional SPM.
        phase+=achieved/60
        made=int(phase); phase-=made
        # At this scan rate at most two strokes are permitted; the feed interlock gates all.
        if made:
            loop=max(0.,loop-.002*made)
            progression+=made
        strokes+=made
        # Scan-end observation: STROKE means one or more completions in this scan,
        # FEED means running between completions; no within-stroke trajectory implied.
        state='CHANGEOVER' if planned else 'FAULT_STOP' if blocked else 'STROKE' if made else 'FEED'
        if state!=previous_state and state in ('FAULT_STOP','CHANGEOVER'):
            records.append(dict(t=t,type='plc_transition',message=state))
        if running and previous_state in ("FAULT_STOP", "CHANGEOVER"):
            records.append(dict(t=t,type="plc_restart",message="Permissives restored; automatic sequence restarted"))
        previous_state=state
        # Dimensional response transported to inspection, not instantaneous fault flag.
        dimension=.02+wear*.18+level('quality_deterioration')*.22+max(0,3-pressure)*.02
        history.append(dimension)
        inspected=history[max(0,t-60)]
        defect_probability=.001+max(0,inspected-.08)*2
        bad=made if made and rejects[t]<defect_probability else 0
        scrap+=bad;good+=made-bad
        current=20+achieved*.15+drive*10+max(0,load-100)*.12
        vals=dict(rate_setpoint=rate,press_run=int(running),press_stop=int(not running),press_fault=int(blocked),stroke_count=strokes,spm=round(achieved,3),part_count=good,job='JOB-1042',die_id='DIE-27A',plc_state=state,die_protection=int(die_trip),feeder_ready=int(feed_complete),lube_ok=int(lube_ok),feeder_position=round(100+feedback_error,4),material_present=int(material),loop_height=round(loop,5),lube_pressure=round(pressure+float(analog_noise[t]),4),motor_current=round(current,4),tonnage=round(load if made else 0.,4),quality_measurement=round(inspected,5),scrap_count=scrap,feed_complete=int(feed_complete),feeder_command=int(not planned),strip_progression=progression,decoiler_ready=int(decoiler<.5))
        if 'historian_dropout' in active:
            for s in selected:
                vals[s]=None
        if 'stuck_sensor' in active:
            if stuck_value is None: stuck_value=vals['spm']
            vals['spm']=stuck_value
        else: stuck_value=None
        # Quality classification receives only acquired observations, never the schedule.
        data_quality=acquisition.observe(t,{s:vals[s] for s in selected})
        # Noncausal ambient and normal material variation are deliberately available.
        sample=dict(t=t,**{s:vals[s] for s in selected},data_quality=data_quality,ambient_temperature=round(22+2*math.sin(t/86400*2*math.pi),3),material_thickness=round(1.2+.005*math.sin(t/300),4))
        if t==duration_s//3: sample['ambient_temperature']+=8 # single-sample distractor
        samples.append(sample)
        if t%60==0:
            quality.append(dict(t=t,good_count=good,scrap_count=scrap,fpy=good/max(1,strokes),defect_class='dimensional' if inspected>.1 else 'none',quality_measurement=round(inspected,5),quality_drift=round(inspected-.02,5),hold_event=inspected>.15))
    maintenance=[dict(work_order_id='WO-260041',asset='Feeder 27',date='2026-10-01',failure_description='Intermittent feed-ready loss',repair_action='Inspect and reseat connections',component_replaced='ready relay',technician_note='Intermittent symptom; causal link not confirmed',repeat_failure=True,pm_status='due',pm_history=['2026-09-01 lubrication and fastener inspection'])]
    pfmea=[dict(asset='Feeder 27',signal_ids=['feed_complete','strip_progression'],process_step='Feed strip',failure_mode='Incomplete feed',potential_effect='Press stop / malformed part',potential_cause='Slip, starvation or sensing fault',prevention_control='Roll and guide PM',detection_control='Feed-complete permissive',characteristic='Strip progression',reaction_plan='Stop and inspect feed path')]
    evidence=dict(context=dict(origin='2026-10-28T00:00:00Z',duration_s=duration_s,profile=profile,job='JOB-1042',die_id='DIE-27A',material='CRS-1.2',rate=60,rate_spm=60,source='synthetic hybrid press simulation',sample_period_s=1,acquisition_quality_rules=dict(RULES)),samples=samples,events=records,maintenance=maintenance,quality=quality,pfmea=pfmea,control_plan=[dict(pfmea[0],inspection_frequency_s=60)])
    # Only evaluator-side truth has class, mechanism and schedule metadata.
    private=[{k:e[k] for k in ('start_s','end_s','event_class','event_kind','failed_item','failure_mechanism','asset')} for e in truth]
    return SimulationResult(evidence,private)
