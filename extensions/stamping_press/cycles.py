"""Phase boundaries and discrete material ledger inside native integration.

The envelope inventory is a mean quantity. This ledger retains the discrete
within-cycle withdrawal. No recorded historian value is edited here.
"""
from __future__ import annotations
import math
from array import array

class EventLog:
    """Compact event columns; dictionaries are materialised only on read."""
    def __init__(self):
        self.time=array("d"); self.pitch=array("d"); self.count=array("q"); self.kind=array("b"); self.rejected=array("b")
    def public_status_columns(self):
        # Physical pitch, inspection/reject and conservation ledgers stay private.
        return (self.time,self.kind,self.count,
                {0:'DI-271',1:'COUNT-271',2:'DI-272',3:'COUNT-274'})
    def measurement_event_series(self,source):
        if source not in ('QI-271','QI-272'): return None
        import numpy as np
        selected=np.frombuffer(self.kind,dtype=np.int8)==3
        return (np.frombuffer(self.time,dtype=float)[selected],np.frombuffer(self.pitch,dtype=float)[selected],100.)
    def measurement_statuses(self,acquired,t_grid,values):
        import numpy as np
        if 'QI-271' not in acquired:return {}
        times,readings=acquired['QI-271']
        good=np.abs(readings-100.)<=.25
        cumulative_good=np.cumsum(good,dtype=np.int64)
        cumulative_reject=np.cumsum(~good,dtype=np.int64)
        indices=np.searchsorted(times,t_grid,side='right')-1
        def held(data):return np.where(indices>=0,data[np.maximum(indices,0)],0.) if len(data) else np.zeros(len(t_grid))
        accepted=held(cumulative_good);rejected=held(cumulative_reject)
        return {'COUNT-272':accepted,'COUNT-273':rejected,'COUNT-274':values['COUNT-271']-accepted-rejected}
    def __len__(self): return len(self.time)
    def append(self,event):
        self.time.append(event["time_s"]);self.pitch.append(event.get("dimension_mm",event.get("pitch_mm",float("nan"))))
        self.count.append(event["count"]);self.kind.append({"permissive_hold":0,"stroke_complete":1,"feed_complete":2,"inspection_delivery":3}[event["kind"]]);self.rejected.append(int(event.get("rejected",False)))
    def __getitem__(self,i):
        event=dict(time_s=self.time[i],count=self.count[i],kind={0:"permissive_hold",1:"stroke_complete",2:"feed_complete",3:"inspection_delivery"}[self.kind[i]])
        if self.kind[i]==3:event['dimension_mm']=self.pitch[i]
        else:event.update(pitch_mm=self.pitch[i],rejected=bool(self.rejected[i]))
        return event
    def __iter__(self):
        for i in range(len(self)): yield self[i]

from historiansim.core.integrator import rk4_step

class PressCycleEvents:
    def __init__(self,unit,x,u,d,p):
        self.stop_requested=False
        self.gate_enabled=bool(unit.quantities(x,u,d,p)['permitted']); self.unit=unit; self.cycle_work=unit.force_work(p,d); self.cycle_pitch_m=unit.strip_travel(float(x[1]),d,p)*.001; self.phase=0.; self.clutch_closed=self.gate_enabled and x[0]>=1.; self.paused_work=self.cycle_work
        if not self.clutch_closed: self.cycle_work=0.
        self.completed=0; self.good=0; self.reject=0
        self.pitch=unit.strip_travel(float(x[1]),d,p); self.encoder_pitch=unit.quantities(x,u,d,p)['encoder_pitch']; self.cycle_encoder_pitch=self.encoder_pitch; self.feed_complete=0.; self.running=1.; self.feed_token=None
        self.buffer_mass=x[2]*p['strip_width']*d['thickness']*p['strip_density']
        self.supplied_mass=self.buffer_mass; self.withdrawn_mass=0.; self.trim_mass=0.; self.product_mass=0.
        self.events=EventLog(); self.pending=[]; self.inspection=100.; self.checked=100.
        self.motor_energy=0.; self.loss_energy=0.; self.forming_energy=0.; self.actual_forming_energy=0.
        self.initial_energy=.5*p['inertia']*x[0]**2; self.energy_residual=0.; self.energy_relative_residual=0.

    @staticmethod
    def forming_fraction(phase):
        a=max(0.,min(1.,(phase-.5)*2))
        return 2*a*a if a<=.5 else 1-2*(1-a)**2

    def set_cycle_work(self,x,new_work,p):
        # Mean energy is a coordinate projection of instantaneous flywheel
        # storage. A work-latch change preserves the instantaneous energy.
        potential=self.phase-self.forming_fraction(self.phase)
        energy=.5*p['inertia']*x[0]**2+(self.cycle_work-new_work)*potential
        if energy<0: raise ValueError('insufficient flywheel storage for cycle projection')
        x[0]=math.sqrt(2*energy/p['inertia']);self.cycle_work=new_work

    @staticmethod
    def feed_fraction(phase):
        # Symmetric acceleration-limited trajectory over half a revolution.
        progress=min(max(phase*2,0.),1.)
        return 2*progress**2 if progress<=.5 else 1-2*(1-progress)**2

    def on_controls(self,controllers):
        self.stop_requested=controllers['SIC-271'].sp<=0.

    def observations(self,t,x,u,d,p):
        q=self.unit.quantities(x,u,d,{**p,'_cycle_enabled':self.gate_enabled,'_cycle_stop':self.stop_requested,'_cycle_clutch':self.clutch_closed})
        # A triangular force-displacement law integrates to forming work.
        # Linear ram displacement over the working half cycle is an explicit
        # quasi-static kinematic assumption, separate from mean envelope speed.
        a=max(0.,min(1.,(self.phase-.5)*2))
        cumulative=2*a*a if a<=.5 else 1-2*(1-a)**2
        demand=q['work']*cumulative
        mean=q['work']*self.phase
        kinetic=.5*p['inertia']*x[0]**2+self.cycle_work*(self.phase-self.forming_fraction(self.phase))
        return {'WI-273':2*self.cycle_work/p['forming_travel']/1000*max(0.,1-abs(2*a-1)), 'COUNT-271':float(self.completed),'COUNT-272':float(self.good),'COUNT-273':float(self.reject),'COUNT-274':float(len(self.pending)),
                'DI-272':self.feed_complete,'DI-271':float(self.gate_enabled and self.clutch_closed and not self.stop_requested),'JI-271':q['motor']/p['efficiency']/1000,'PHASE-271':self.phase,
                'ZI-271':self.encoder_pitch,'ZI-272':self.pitch,
                'ZI-276':self.encoder_pitch,'ZI-274':self.cycle_encoder_pitch*self.feed_fraction(self.phase), 'ZI-275':self.cycle_pitch_m*1000*self.feed_fraction(self.phase),'SI-272':math.sqrt(max(0,2*kinetic/p['inertia']))*60/(2*math.pi),
                'QI-271':self.inspection,'QI-272':self.checked,
                'CALC-MATERIAL-RESIDUAL':self.supplied_mass-self.withdrawn_mass-self.buffer_mass,
                'CALC-ENERGY-RESIDUAL':self.energy_residual,
                # Private native truth only: no TagSpec or acquisition path.
                'AUDIT-ENERGY-RELATIVE-RESIDUAL':self.energy_relative_residual,
                'AUDIT-MATERIAL-RELATIVE-RESIDUAL':abs(self.supplied_mass-self.withdrawn_mass-self.buffer_mass)/max(self.supplied_mass,1.),
                'AUDIT-COUNTER-RESIDUAL':float(self.completed-self.good-self.reject-len(self.pending)),
                'AUDIT-MOTOR-ENERGY-J':self.motor_energy,
                'AUDIT-SUPPLIED-MASS-KG':self.supplied_mass}

    def gate_margin(self,x,d,p):
        if self.gate_enabled:
            return min(float(x[3])-2.,float(x[2])-.15,80-float(x[5]),2500-self.unit.force_work(p,d),self.unit.strip_travel(float(x[1]),d,p)-50.,150-self.unit.strip_travel(float(x[1]),d,p))
        return min(float(x[3])-2.5,float(x[2])-.25,75-float(x[5]),2200-self.unit.force_work(p,d),self.unit.strip_travel(float(x[1]),d,p)-55.,145-self.unit.strip_travel(float(x[1]),d,p))

    def clutch_margin(self,x,p):
        required=self.paused_work*(self.phase-self.forming_fraction(self.phase))+.5*p['inertia']
        return .5*p['inertia']*float(x[0])**2-required

    def advance(self,t,x,u,d,p,dt_sim,n_sub):
        for sub in range(n_sub):
            now=t+sub*dt_sim; remaining=dt_sim
            while remaining>1e-12:
                margin=self.gate_margin(x,d,p)
                if self.gate_enabled and margin < -1e-9: self.gate_enabled=False
                elif not self.gate_enabled and margin > 1e-9: self.gate_enabled=True
                drive_enabled=self.gate_enabled and not self.stop_requested
                if self.clutch_closed and not drive_enabled:
                    self.paused_work=self.cycle_work
                    self.set_cycle_work(x,0.,p)
                    self.clutch_closed=False
                elif not self.clutch_closed and drive_enabled and self.clutch_margin(x,p)>=-1e-9:
                    self.set_cycle_work(x,self.paused_work,p)
                    self.clutch_closed=True
                if self.clutch_closed and self.phase<=1e-12:
                    self.cycle_pitch_m=self.unit.strip_travel(float(x[1]),d,p)*.001
                    self.cycle_encoder_pitch=self.unit.quantities(x,u,d,p)['encoder_pitch']
                effective={**p,'_cycle_work':self.cycle_work,'_cycle_pitch_m':self.cycle_pitch_m,'_cycle_enabled':self.gate_enabled,'_cycle_stop':self.stop_requested,'_cycle_clutch':self.clutch_closed}
                q=self.unit.quantities(x,u,d,effective)
                rate=max(q['rate'],1e-12)
                next_boundary=.5 if self.phase<.5-1e-10 else 1.
                phase_left=next_boundary-self.phase
                enabled=bool(q['clutch'])
                acceleration=self.unit.derivatives(now,x,u,d,p)[0]/(2*math.pi)
                discriminant=max(0,rate*rate+2*acceleration*phase_left)
                crossing=2*phase_left/max(rate+math.sqrt(discriminant),1e-12)
                h=min(remaining,crossing,.5) if enabled else min(remaining,.5)
                if self.pending: h=min(h,max(self.pending[0][0]-now,1e-12))
                boundary=enabled and crossing<=h
                before=x.copy()
                # Integrate phase with the same RK4 quadrature as angular
                # speed. Locate each boundary by a converged dense step.
                for locate in range(8):
                    stage=[]; phase_rates=[]
                    def derivative(tt,xx):
                        qq=self.unit.quantities(xx,u,d,effective); stage.append(qq)
                        phase_rates.append(max(float(xx[0]),0)/(2*math.pi) if qq['clutch'] else 0.)
                        return self.unit.derivatives(tt,xx,u,d,effective)
                    xnext=rk4_step(derivative,now,before,h)
                    phase_gain=h*sum(w*r for w,r in zip((1,2,2,1),phase_rates))/6
                    if not boundary or abs(phase_gain-phase_left)<1e-11: break
                    h*=phase_left/max(phase_gain,1e-12)
                margin_end=self.gate_margin(xnext,d,p)
                gate_cross=(self.gate_enabled and margin_end < -1e-10) or (not self.gate_enabled and margin_end > 1e-10)
                spin_cross=not self.clutch_closed and drive_enabled and self.clutch_margin(xnext,p)>1e-10
                if gate_cross or spin_cross:
                    candidates=[]
                    for event in ('gate','spin'):
                        if (event=='gate' and not gate_cross) or (event=='spin' and not spin_cross): continue
                        lo,hi=0.,h
                        for locate_boundary in range(40):
                            middle=(lo+hi)*.5
                            trial=rk4_step(derivative,now,before,middle)
                            if event=='gate': crossed=self.gate_margin(trial,d,p)<0 if self.gate_enabled else self.gate_margin(trial,d,p)>0
                            else: crossed=self.clutch_margin(trial,p)>0
                            if crossed: hi=middle
                            else: lo=middle
                            if hi-lo<1e-10: break
                        candidates.append(((lo+hi)*.5,event))
                    h,event=min(candidates)
                    gate_cross=event=='gate';spin_cross=event=='spin'
                    stage=[];phase_rates=[]
                    xnext=rk4_step(derivative,now,before,h)
                    phase_gain=h*sum(w*r for w,r in zip((1,2,2,1),phase_rates))/6
                    boundary=False
                x=xnext
                weights=(1,2,2,1)
                def quadrature(key):return h*sum(w*s[key] for w,s in zip(weights,stage))/6
                incoming=quadrature('delivery')*p['strip_width']*d['thickness']*p['strip_density']
                self.supplied_mass+=incoming; self.buffer_mass+=incoming
                self.motor_energy+=quadrature('motor')
                self.loss_energy+=quadrature('bearing')+quadrature('other')+quadrature('brake')
                self.forming_energy+=quadrature('forming')
                self.actual_forming_energy+=self.cycle_work*(self.forming_fraction(self.phase+phase_gain)-self.forming_fraction(self.phase))
                self.phase+=phase_gain; now+=h; remaining-=h
                if next_boundary==.5 and self.phase>=.5-1e-10 and self.feed_token is None:
                    pitch=max(self.cycle_pitch_m*1000,0.)
                    self.pitch=pitch
                    self.encoder_pitch=self.cycle_encoder_pitch
                    mass=pitch*.001*p['strip_width']*d['thickness']*p['strip_density']
                    permitted=x[3]>=2. and self.buffer_mass>=mass and 50<pitch<150 and x[0]>1
                    self.feed_complete=float(permitted)
                    old_pitch=self.cycle_pitch_m
                    self.cycle_pitch_m=pitch*.001 if permitted else 0.
                    x[2]+=(old_pitch-self.cycle_pitch_m)*self.phase
                    self.set_cycle_work(x,self.unit.force_work(p,d) if permitted else 0.,p)
                    self.paused_work=self.cycle_work
                    if permitted:
                        self.pitch=pitch
                        self.buffer_mass-=mass; self.withdrawn_mass+=mass
                        self.feed_token=(pitch,mass,d['thickness'])
                        self.events.append({'time_s':now,'kind':'feed_complete','pitch_mm':pitch,'count':self.completed})
                if self.phase>=1-1e-10:
                    self.phase=0.
                    self.cycle_pitch_m=self.unit.strip_travel(float(x[1]),d,p)*.001 if self.feed_token is None else 0.
                    self.cycle_encoder_pitch=self.unit.quantities(x,u,d,p)['encoder_pitch']
                    permitted=self.feed_token is not None and x[3]>=2. and x[0]>1
                    self.running=float(permitted)
                    if permitted:
                        pitch,mass,stock_thickness=self.feed_token;self.feed_token=None
                        self.completed+=1
                        self.cycle_pitch_m=self.unit.strip_travel(float(x[1]),d,p)*.001
                        self.trim_mass+=mass*p['trim_fraction']; self.product_mass+=mass*(1-p['trim_fraction'])
                        part_state=x.copy();part_state[1]=pitch
                        dimension=self.unit.part_dimension(pitch,float(x[5]),stock_thickness,p)
                        reject=abs(dimension-100)>.25
                        self.pending.append((now+10.,dimension))
                        self.events.append({'time_s':now,'kind':'stroke_complete','pitch_mm':pitch,'rejected':bool(reject),'count':self.completed})
                        self.feed_complete=0.
                    else:
                        self.events.append({'time_s':now,'kind':'permissive_hold','count':self.completed})
                if gate_cross: self.gate_enabled=not self.gate_enabled
                if spin_cross:
                    self.set_cycle_work(x,self.paused_work,p)
                    self.clutch_closed=True
                while self.pending and self.pending[0][0]<=now+1e-10:
                    _,dimension=self.pending.pop(0); self.inspection=dimension; self.checked=dimension
                    rejected=abs(dimension-100)>.25
                    self.reject+=int(rejected); self.good+=int(not rejected)
                    self.events.append(dict(time_s=now,kind='inspection_delivery',dimension_mm=dimension,count=self.good+self.reject))
                stored=.5*p['inertia']*x[0]**2+self.cycle_work*(self.phase-self.forming_fraction(self.phase))-self.initial_energy
                self.energy_residual=self.motor_energy-self.loss_energy-self.actual_forming_energy-stored
                self.energy_relative_residual=abs(self.energy_residual)/max(self.motor_energy,1.)
        return x
