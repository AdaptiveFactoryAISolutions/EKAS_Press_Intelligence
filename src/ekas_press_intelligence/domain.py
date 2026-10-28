"""Public engineering priors; contains no scenario schedule or hidden truth."""
from copy import deepcopy

_SPARSE='rate_setpoint press_run press_stop press_fault stroke_count spm part_count job die_id plc_state die_protection feeder_ready lube_ok'.split()
_ENHANCED='feeder_position material_present loop_height lube_pressure motor_current tonnage quality_measurement scrap_count feed_complete feeder_command strip_progression decoiler_ready'.split()
_SPECS=[
('feeder_sensor_drift','fault','Feeder 27','position transducer','calibration bias increases until feedback rejects feed','feeder_position', 'drift', ['feeder_mechanical_instability','misfeed']),
('feeder_mechanical_instability','fault','Feeder 27','feed roll coupling','backlash produces intermittent short feeds','feeder_position','variance', ['material_starvation','feeder_sensor_drift','misfeed']),
('misfeed','fault','Feeder 27','strip guide','guide obstruction prevents strip progression','strip_progression','decrease',['feeder_mechanical_instability','material_starvation']),
('material_starvation','fault','Material','coil stock','insufficient incoming material exhausts loop buffer','material_present','decrease',['feeder_mechanical_instability','decoiler_interruption','misfeed']),
('decoiler_interruption','fault','Decoiler 27','decoiler drive','drive interruption drains loop buffer','decoiler_ready','decrease',['material_starvation']),
('lubrication_pressure_loss','fault','Lubrication system','supply hose','leak exceeds compensated pump capacity','lube_pressure','decrease',['abnormal_tonnage','progressive_die_wear']),
('die_protection_trip','fault','Die','die protection input','intermittent slug obstruction trips die protection','die_protection','increase',['misfeed']),
('progressive_die_wear','fault','Die','cutting insert','edge wear raises load before delayed dimensional drift','quality_measurement','increase',['quality_deterioration','abnormal_tonnage','lubrication_pressure_loss']),
('abnormal_tonnage','fault','Press 27','die alignment','die misalignment raises forming force above load limit','tonnage','increase',['progressive_die_wear','lubrication_pressure_loss']),
('press_speed_degradation','fault','Press 27','drive belt','drive slip reduces achievable speed under load','motor_current','increase',['operator_speed_change','repeated_microstops']),
('repeated_microstops','fault','Feeder 27','ready relay','intermittent contact opens feed permissive','feed_complete','intermittent',['feeder_mechanical_instability','press_speed_degradation']),
('quality_deterioration','fault','Material','material temper','hardness variation causes delayed dimensional rejects','quality_measurement','increase',['progressive_die_wear']),
('operator_speed_change','benign','Press 27','operator setpoint','authorized reduced speed for process observation','rate_setpoint','decrease',['press_speed_degradation']),
('planned_stop','benign','Line 03','production schedule','planned changeover pauses production','press_stop','increase',['die_protection_trip','material_starvation']),
('historian_dropout','artifact','Historian','communication link','packet outage removes observations while plant continues','press_run','missing',['planned_stop','stuck_sensor']),
('stuck_sensor','artifact','Historian','SPM transmitter','sample register freezes while counters advance','spm','constant',['press_speed_degradation','historian_dropout'])]

def profile_signals(profile):
    if profile not in ('sparse','enhanced'): raise ValueError('unknown instrumentation profile')
    return list(_SPARSE + (_ENHANCED if profile=='enhanced' else []))

def signals():
    discrete=set('press_run press_stop press_fault stroke_count part_count scrap_count job die_id plc_state die_protection feeder_ready lube_ok material_present feed_complete feeder_command strip_progression decoiler_ready'.split())
    units={'spm':'strokes/min','rate_setpoint':'strokes/min','feeder_position':'mm','loop_height':'m','lube_pressure':'bar','motor_current':'A','tonnage':'tonne','quality_measurement':'mm'}
    return [dict(signal_id=s,asset='Feeder 27' if s.startswith('feed') else 'Press 27',description=s.replace('_',' '),unit=units.get(s,'state' if s in discrete else 'count'),existing=s in _SPARSE or s in ('feed_complete','feeder_command','decoiler_ready'),kind='discrete' if s in discrete else 'analog',priority=1 if s in _SPARSE else 2 if s in ('feed_complete','feeder_command','decoiler_ready') else 3 if s=='material_present' else 4,hardware_required=s not in _SPARSE and s not in ('feed_complete','feeder_command','decoiler_ready')) for s in _SPARSE+_ENHANCED]

def assets():
    names=['Plant','Line 03','Press 27','Feeder 27','Decoiler 27','Lubrication system','Die','Material','Part','Quality inspection','Maintenance history']
    return [dict(asset_id=n, name=n,parent=None if i==0 else 'Plant' if i==1 else 'Line 03',relationship='contains' if i<2 else 'part_of') for i,n in enumerate(names)]

def catalog():
    entries={}
    primary={x[0]:x[5] for x in _SPECS}
    for cls,kind,asset,item,mechanism,sig,direction,comp in _SPECS:
        entries[cls]=dict(event_class=cls,event_kind=kind,asset=asset,failed_item=item,failure_mechanism=mechanism,symptoms=['production rate or quality deviation',sig],observable_signals=[sig],expected_directionality={sig:direction},timing_relationships='mechanism precedes production response; quality inspection lags forming by 60 seconds',competing_causes=comp,discriminating_signals={c:sorted(set([sig,primary[c]])) for c in primary if c != cls},sparse_profile_observability='partial' if sig in _SPARSE else 'ambiguous',enhanced_profile_observability='distinguishable',verification_method='compare rate, stops and quality over matched job/die/material/exposure after physical correction')
    # Pair requirements describe observations AND their measured temporal feature.
    # Mere availability never demonstrates that a causal signature was observed.
    for cls, entry in entries.items():
        entry['discrimination_rules'] = {}
        for other, required in entry['discriminating_signals'].items():
            entry['discrimination_rules'][other] = {
                'required_signals': list(required),
                'features': {sig: 'compare direction, variability and onset against baseline' for sig in required},
                'expected_difference': f"{cls}: {entry['expected_directionality']}; {other}: {entries[other]['expected_directionality']}",
                'qualification': 'Available observations permit testing; measured evidence must satisfy the causal timing and alternative tests.'}
    def pair(a,b,required,features,difference):
        for left,right in ((a,b),(b,a)):
            entries[left]['discriminating_signals'][right]=required
            entries[left]['discrimination_rules'][right]={'required_signals':required,'features':features,'expected_difference':difference,'qualification':'Require observed feature difference; signal presence alone is insufficient.'}
    pair('feeder_sensor_drift','feeder_mechanical_instability',['feeder_position'],
         {'feeder_position':'signed trend versus increasing short-timescale residual variance'},
         'Sensor bias has a persistent signed ramp; backlash oscillates around target with increasing variance.')
    pair('progressive_die_wear','quality_deterioration',['tonnage','quality_measurement'],
         {'tonnage':'forming-load envelope rising before inspection drift','quality_measurement':'60-second delayed dimensional response'},
         'Wear raises forming load before quality drift; material-quality episode shifts dimensions without the wear load rise.')
    pair('feeder_mechanical_instability','material_starvation',['feeder_position','material_present'],
         {'feeder_position':'short-timescale oscillation while material present','material_present':'loss following loop depletion'},
         'Mechanical instability shows erratic position with stock present; starvation loses stock after reserve depletion.')
    pair('planned_stop','historian_dropout',[],{},
         'Cannot distinguish from missing samples alone; requires acquisition-quality metadata and authorized operator records.')
    return deepcopy(list(entries.values()))
