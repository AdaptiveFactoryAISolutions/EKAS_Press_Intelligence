"""Real native press integration and engineering contracts."""
import importlib.util
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def test_press_native_registration_and_equilibrium():
    from historiansim.plants import get_plant
    plant = get_plant('stamping_press')
    from historiansim.plants.stamping_press.loops import design_point, DESIGN_D
    unit, u, x, sig = design_point()
    assert len(x) == 6
    assert np.max(np.abs(unit.derivatives(0,x,u,DESIGN_D,unit.params))) < 1e-10
    assert len(plant.catalog) == 19
    assert all(.3 < v < .7 for v in u.values())

def test_cycle_material_and_force_work_contract():
    from historiansim.plants.stamping_press.loops import design_point, DESIGN_D
    unit,u,x,_=design_point()
    events=unit.cycle_event_source(x,u,DESIGN_D,unit.params)
    for k in range(100):
        x=events.advance(k*.1,x,u,DESIGN_D,unit.params,.1,1)
    assert events.completed == 10
    assert events.good + events.reject + len(events.pending) == events.completed
    assert abs(events.supplied_mass-events.withdrawn_mass-events.buffer_mass) < 1e-10
    assert abs(unit.force_work(unit.params, DESIGN_D)-1000) < 1e-8
    assert events.energy_relative_residual < .001

def test_native_sim_uses_cycle_hook():
    from historiansim.plants.stamping_press.loops import design_point, DESIGN_D, plant_loops
    from historiansim.core.sim import simulate, ConstantDisturbance
    from historiansim.config.schema import ScenarioConfig, TimeConfig
    cfg=ScenarioConfig(name='press-test',unit='stamping_press',time=TimeConfig(days=20/86400,dt_scan=1,dt_sim=.1),loops=plant_loops())
    result=simulate(cfg,ConstantDisturbance(DESIGN_D))
    assert result.signals['COUNT-271'][-1] == 19
    assert len(result.events) >= 19

def test_controlled_encoder_bias_changes_physical_feed():
    from historiansim.core.sim import simulate,ConstantDisturbance
    from historiansim.config.schema import ScenarioConfig,TimeConfig
    from historiansim.plants.stamping_press.loops import DESIGN_D,plant_loops
    cfg=ScenarioConfig(name='feedback',unit='stamping_press',time=TimeConfig(days=1200/86400,dt_scan=1,dt_sim=.1),loops=plant_loops())
    def bias(signals,k):
        measured=dict(signals); measured['ZI-271']*=1.03; return measured
    result=simulate(cfg,ConstantDisturbance(DESIGN_D),sensor_fn=bias)
    assert abs(result.signals['ZI-272'][-1]-100/1.03)<.01
    assert abs(result.setpoints['FDC-271.SP'][-1]-100)<1e-12

def test_feed_permissive_requires_material_and_lubrication():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    unit,u,x,_=design_point();x[3]=1.
    event=unit.cycle_event_source(x,u,DESIGN_D,unit.params)
    u['PUMP-272']=0
    x=event.advance(0,x,u,DESIGN_D,unit.params,.1,20)
    assert event.completed==0
    assert event.withdrawn_mass==0
    assert event.good==event.reject==0

def test_transient_energy_and_step_convergence():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    histories=[]
    for dt in (.1,.05):
        unit,u,x,_=design_point();event=unit.cycle_event_source(x,u,DESIGN_D,unit.params)
        u['DRIVE-271']*=1.05
        for k in range(round(30/dt)):
            x=event.advance(k*dt,x,u,DESIGN_D,unit.params,dt,1)
        assert event.energy_relative_residual<.001
        histories.append((x,event))
    a,b=histories
    assert a[1].completed==b[1].completed
    assert np.max(np.abs((a[0]-b[0])/np.maximum(np.abs(b[0]),1)))<.001
    times_a=[e['time_s'] for e in a[1].events]
    times_b=[e['time_s'] for e in b[1].events]
    assert np.max(np.abs(np.array(times_a)-times_b))<.001

def test_untouched_references_keep_exact_native_arrays(tmp_path):
    import os,subprocess,json
    import historiansim
    code='''
import hashlib,json
from historiansim.scenarios import build_scenario
from historiansim.pipeline import generate
out={}
for name in ('tank-rca','cstr-rca'):
    cfg=build_scenario(name,profile='quick',seed=7,days=.01)
    cfg.episodes.n_faults=0;cfg.episodes.n_benign=0;cfg.episodes.baseline_days=0
    dataset=generate(cfg)
    h=hashlib.sha256()
    for source in (dataset.truth.states,*dataset.truth.signals.values(),*dataset.measured.values.values()):
        h.update(source.tobytes())
    out[name]=h.hexdigest()
print(json.dumps(out,sort_keys=True))
'''
    results=[]
    active=Path(historiansim.__file__).resolve().parents[1]
    stock=ROOT/'vendor/HistorianSim/src'
    assert active!=stock,'Array parity requires an actually selected candidate runtime'
    for source in (stock,active):
        env={**os.environ,'PYTHONPATH':str(source)}
        run=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True,check=True)
        results.append(json.loads(run.stdout.strip().splitlines()[-1]))
    assert results[0]==results[1]

def test_lubrication_trip_removes_drive_energy_then_restart():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    unit,u,x,_=design_point(); x[3]=1.
    q=unit.quantities(x,u,DESIGN_D,unit.params)
    assert q['motor']==0
    assert q['forming']==0
    assert unit.derivatives(0,x,u,DESIGN_D,unit.params)[0]<0
    x[3]=5.
    assert unit.quantities(x,u,DESIGN_D,unit.params)['motor']>0

def test_prepared_runtime_rejects_tampering_and_cleans_stale_source():
    import tempfile
    spec=importlib.util.spec_from_file_location('prepare_native_runtime',ROOT/'scripts/prepare_native_runtime.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='native-test-',dir=ROOT/'work') as temp:
        runtime=module.prepare_runtime(ROOT,Path(temp))
        module.verify_runtime(ROOT,runtime)
        extra=runtime/'src/historiansim/plants/unexpected.py';extra.write_text('raise RuntimeError("unexpected")')
        import pytest
        with pytest.raises(ValueError,match='file hashes mismatch'):module.verify_runtime(ROOT,runtime)
        module.prepare_runtime(ROOT,runtime)
        assert not extra.exists()
        module.verify_runtime(ROOT,runtime)
        link=runtime/'src/historiansim/unsafe.py';link.symlink_to(ROOT/'README.md')
        with pytest.raises(ValueError,match='symbolic link'):module.verify_runtime(ROOT,runtime)

def test_mean_inventory_and_actual_cycle_work_reconcile_after_restart():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    unit,u,x,_=design_point();x[2]=.01
    event=unit.cycle_event_source(x,u,DESIGN_D,unit.params)
    for k in range(6000):x=event.advance(k*.1,x,u,DESIGN_D,unit.params,.1,1)
    mass_per_m=unit.params['strip_width']*DESIGN_D['thickness']*unit.params['strip_density']
    actual_buffer=event.buffer_mass/mass_per_m
    phase_projection=event.cycle_pitch_m*event.phase-(event.feed_token[0]*.001 if event.feed_token else 0.)
    assert abs(actual_buffer-float(x[2])-phase_projection)<1e-6
    completed_work=1000*event.completed
    partial_work=event.cycle_work*event.forming_fraction(event.phase)
    assert abs(event.actual_forming_energy-completed_work-partial_work)<1e-6*max(completed_work,1)
    assert event.energy_relative_residual<.001

def test_trip_restart_boundaries_converge_to_one_millisecond():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    histories=[]
    for dt in (.1,.05):
        unit,u,x,_=design_point();x[2]=.01
        event=unit.cycle_event_source(x,u,DESIGN_D,unit.params)
        for k in range(round(60/dt)):x=event.advance(k*dt,x,u,DESIGN_D,unit.params,dt,1)
        histories.append((x,event))
    a,b=histories
    assert a[1].completed==b[1].completed
    assert len(a[1].events)==len(b[1].events)
    assert np.max(np.abs(np.array(a[1].events.time)-np.array(b[1].events.time)))<.001
    assert np.max(np.abs(a[0]-b[0])/np.maximum(np.abs(b[0]),1))<.001

def test_original_reference_artifacts_match_untouched_source(tmp_path,request):
    import os,subprocess,json
    import historiansim
    reference_root=os.environ.get('EKAS_NATIVE_TEST_REFERENCE_RUNTIME')
    if reference_root is None:
        import tempfile
        (ROOT/'work').mkdir(exist_ok=True)
        scratch=tempfile.TemporaryDirectory(prefix='reference-parity-',dir=ROOT/'work')
        request.addfinalizer(scratch.cleanup)
        spec=importlib.util.spec_from_file_location('prepare_reference_runtime',ROOT/'scripts/prepare_reference_runtime.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        reference_root=module.prepare_runtime(ROOT,Path(scratch.name)/'reference-runtime')
    reference=Path(reference_root)/'src'
    assert reference.is_dir(),'Prepared untouched reference source is required'
    active=Path(historiansim.__file__).resolve().parents[1]
    code='''
import hashlib,json,tempfile
from pathlib import Path
from historiansim.scenarios import build_scenario
from historiansim.pipeline import generate,write_dataset
out={}
for name in ('tank-rca','cstr-rca'):
 cfg=build_scenario(name,profile='quick',seed=7,days=.01)
 cfg.episodes.n_faults=0;cfg.episodes.n_benign=0;cfg.episodes.baseline_days=0
 dataset=generate(cfg)
 with tempfile.TemporaryDirectory() as temp:
  folder=Path(temp);write_dataset(dataset,folder)
  out[name]={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file()}
print(json.dumps(out,sort_keys=True))
'''
    results=[]
    for source in (reference,active):
        env={**os.environ,'PYTHONPATH':str(source)}
        run=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True,check=True)
        results.append(json.loads(run.stdout.strip().splitlines()[-1]))
    assert results[0]==results[1]

def test_dcs_calculations_follow_measured_instruments():
    from historiansim.plants.stamping_press.tags import recompute_dcs_calculations
    values={'WI-271':np.array([120.]),'ZI-272':np.array([90.]),'SIC-271.PV':np.array([60.]),'DI-271':np.array([1.]),'FI-275':np.array([.08]),'CALC-WORK':np.array([9999.]),'CALC-SUPPLY':np.array([9999.]),'CALC-CONSUMPTION':np.array([9999.])}
    recompute_dcs_calculations(values)
    assert values['CALC-WORK'][0]==1200
    assert abs(values['CALC-SUPPLY'][0]-.08)<1e-12
    assert abs(values['CALC-CONSUMPTION'][0]-.09)<1e-12

def test_force_displacement_integral_matches_native_cycle_work():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    unit,_,_,_=design_point()
    for strength,thickness in ((1.,.0012),(1.08,.0012),(1.,.00123)):
        d={**DESIGN_D,'strength':strength,'thickness':thickness}
        positions=np.linspace(0,unit.params['forming_travel'],1001)
        force=np.array([unit.forming_force(float(position),unit.params,d) for position in positions])
        integral=np.trapezoid(force,positions)
        assert abs(integral-unit.force_work(unit.params,d))<1e-10*integral

def test_film_and_pump_heat_have_real_energy_sources():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    unit,u,x,_=design_point();normal=unit.quantities(x,u,DESIGN_D,unit.params)
    failed=unit.quantities(x,u,DESIGN_D,{**unit.params,'film_delivery':.7})
    assert failed['other']>normal['other']
    assert normal['pump_input']>5*normal['pump']*100000/60000
    dx=unit.derivatives(0,x,u,DESIGN_D,unit.params)
    mechanical_storage=unit.params['inertia']*x[0]*dx[0]
    thermal_storage=unit.params['oil_capacity']*dx[4]+unit.params['die_capacity']*dx[5]
    outputs=normal['part_energy']+normal['oil_cooling']+normal['cooling']+normal['die_ambient']+normal['other_ambient']+normal['brake']
    assert abs(normal['motor']+normal['pump_input']-mechanical_storage-thermal_storage-outputs)<1e-8

def test_runtime_provenance_rejects_manifest_forgery_siblings_and_parent_links():
    import tempfile,json,hashlib,pytest
    spec=importlib.util.spec_from_file_location('prepare_native_runtime',ROOT/'scripts/prepare_native_runtime.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='native-trust-test-',dir=ROOT/'work') as temp:
        runtime=module.prepare_runtime(ROOT,Path(temp)/'runtime')
        source=runtime/'src/historiansim/core/pid.py';source.write_text(source.read_text()+'\nFORGED_RUNTIME=True\n')
        provenance=runtime/'NATIVE_RUNTIME_PROVENANCE.json';manifest=json.loads(provenance.read_text())
        manifest['runtime_sha256']['core/pid.py']=hashlib.sha256(source.read_bytes()).hexdigest()
        provenance.write_text(json.dumps(manifest))
        with pytest.raises(ValueError,match='derived pinned source'):module.verify_runtime(ROOT,runtime)
        module.prepare_runtime(ROOT,runtime)
        sibling=runtime/'src/unverified.py';sibling.write_text('SHADOW=True\n')
        with pytest.raises(ValueError,match='unsupported sibling'):module.verify_runtime(ROOT,runtime)
        sibling.unlink()
        parent=Path(temp)/'linked';parent.symlink_to(runtime.parent,target_is_directory=True)
        with pytest.raises(ValueError,match='symbolic link'):module.verify_runtime(ROOT,parent/'runtime')

def test_compiled_stepper_matches_python_for_physical_catalog_and_restart():
    from historiansim.plants.stamping_press.compiled_backend import CompiledPressCycleEvents
    from historiansim.plants.stamping_press.cycles import PressCycleEvents
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    from historiansim.plants.stamping_press.faults import CATALOG
    from historiansim.faults.base import DisturbanceFault,ControlFault
    cases=[(None,'moderate')]+[(cause,severity) for cause in CATALOG.causes.values() for severity in ('subtle','moderate','obvious')]
    for cause,severity in cases:
        unit,u,x,_=design_point();d=dict(DESIGN_D);p=dict(unit.params)
        if cause is not None:
            fault=cause.make(0,severity)
            if hasattr(fault,'apply'):fault.apply(p,2*86400)
            elif isinstance(fault,DisturbanceFault):d[fault.channel]=float(fault.apply_channel(np.array([d[fault.channel]]),np.array([2*86400]))[0])
            elif isinstance(fault,ControlFault):u['FEED-271']=fault.value
        for low_buffer in (False,True):
            initial=x.copy()
            if low_buffer:initial[2]=.01
            python=PressCycleEvents(unit,initial,u,d,p)
            compiled=CompiledPressCycleEvents(unit,initial,u,d,p)
            xp=initial.copy();xc=initial.copy()
            for k in range(12):
                xp=python.advance(k*5,xp,u,d,p,5,1)
                xc=compiled.advance(k*5,xc,u,d,p,5,1)
            assert np.allclose(xp,xc,rtol=2e-12,atol=2e-11),(cause,severity,low_buffer,xp,xc)
            assert (python.completed,python.good,python.reject)==(compiled.completed,compiled.good,compiled.reject)
            assert list(python.events.kind)==list(compiled.events.kind)
            assert np.allclose(python.events.time,compiled.events.time,rtol=0,atol=1e-8)
            for field in ('buffer_mass','supplied_mass','withdrawn_mass','trim_mass','product_mass','actual_forming_energy','motor_energy','loss_energy'):
                assert np.isclose(getattr(python,field),getattr(compiled,field),rtol=2e-12,atol=2e-9),(field,cause,severity)

def test_native_operator_stop_holds_phase_and_restarts_without_empty_strokes():
    from historiansim.core.sim import simulate,ConstantDisturbance
    from historiansim.config.schema import ScenarioConfig,TimeConfig
    from historiansim.plants.stamping_press.loops import DESIGN_D,plant_loops
    cfg=ScenarioConfig(name='operator-stop',unit='stamping_press',time=TimeConfig(days=1200/86400,dt_scan=10,dt_sim=5),loops=plant_loops())
    def operator(k,t,controllers):
        if k==30:controllers['SIC-271'].sp=0.
        elif k==90:controllers['SIC-271'].sp=60.
    result=simulate(cfg,ConstantDisturbance(DESIGN_D),on_scan=operator)
    assert np.all(np.diff(result.signals['COUNT-271'][35:85])==0)
    assert np.ptp(result.signals['PHASE-271'][35:85])<1e-10
    assert np.all(result.signals['DI-271'][35:85]==0)
    assert result.signals['COUNT-271'][-1]>result.signals['COUNT-271'][95]

def test_midstroke_clutch_stop_dissipates_actual_flywheel_energy():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    unit,u,x,_=design_point();event=unit.cycle_event_source(x,u,DESIGN_D,unit.params)
    x=event.advance(0,x,u,DESIGN_D,unit.params,.1,7)
    before=event.actual_forming_energy
    event.stop_requested=True;u['DRIVE-271']=0
    for k in range(24):x=event.advance(.7+k*5,x,u,DESIGN_D,unit.params,5,1)
    assert event.actual_forming_energy==before
    assert event.observations(120.7,x,u,DESIGN_D,unit.params)['SI-272']<.1
    assert event.energy_relative_residual<.001

def test_inspection_is_bound_to_the_material_actually_fed():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    unit,u,x,_=design_point();event=unit.cycle_event_source(x,u,DESIGN_D,unit.params)
    x=event.advance(0,x,u,DESIGN_D,unit.params,.1,5)
    assert event.feed_token is not None
    changed={**DESIGN_D,'thickness':.00132}
    x=event.advance(.5,x,u,changed,unit.params,.1,5)
    event.stop_requested=True;u['DRIVE-271']=0
    x=event.advance(1.,x,u,changed,unit.params,.1,100)
    assert abs(event.inspection-100.)<.01
    assert event.good==1 and event.reject==0

def test_native_press_uses_verified_compiled_stepper_by_default():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    unit,u,x,_=design_point()
    event=unit.cycle_event_source(x,u,DESIGN_D,unit.params)
    assert event.__class__.__name__=='CompiledPressCycleEvents'
    assert event.backend=='compiled-cpp-rk4-events'

def test_runtime_preparation_reads_only_protected_committed_source(monkeypatch,tmp_path):
    import subprocess
    import tempfile
    spec=importlib.util.spec_from_file_location('prepare_native_runtime',ROOT/'scripts/prepare_native_runtime.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original_output=subprocess.check_output
    original_run=subprocess.run
    operations=[]
    def guarded_output(command,*args,**kwargs):
        if command[0]=='/usr/bin/git':
            assert str(ROOT/'work/HistorianSim-authoring') not in command
            operations.append(command)
        return original_output(command,*args,**kwargs)
    def guarded_run(command,*args,**kwargs):
        if 'apply' in command:
            assert command[0]=='/usr/bin/git'
            assert kwargs['env']['GIT_NO_REPLACE_OBJECTS']=='1'
            assert not any(k in kwargs['env'] for k in ('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR'))
        return original_run(command,*args,**kwargs)
    monkeypatch.setattr(subprocess,'check_output',guarded_output)
    monkeypatch.setattr(subprocess,'run',guarded_run)
    with tempfile.TemporaryDirectory(prefix='vendor-source-test-',dir=ROOT/'work') as temp:
        runtime=module.prepare_runtime(ROOT,Path(temp))
        module.verify_runtime(ROOT,runtime)
    assert any('show' in command and str(ROOT/'vendor/HistorianSim') in command for command in operations)

def test_sparse_profile_restricts_same_physical_run_only():
    from historiansim.plants import get_plant
    from historiansim.core.sim import simulate,ConstantDisturbance
    from historiansim.config.schema import ScenarioConfig,TimeConfig
    from historiansim.measurement.apply import measure
    from historiansim.core.rng import SeedBank
    from historiansim.plants.stamping_press.loops import DESIGN_D,plant_loops
    plant=get_plant('stamping_press')
    assert {'WI-272','ZI-273','QI-272','FI-274'} <= set(plant.hard_mode_withheld)
    cfg=ScenarioConfig(name='same-history-profiles',unit='stamping_press',time=TimeConfig(days=120/86400,dt_scan=1,dt_sim=.1),loops=plant_loops())
    truth=simulate(cfg,ConstantDisturbance(DESIGN_D))
    states=truth.states.copy()
    full=measure(truth,plant.tags(),SeedBank(7),unit_params=plant.unit().params,calcs=plant.recompute_calcs)
    sparse=measure(truth,plant.tags(),SeedBank(7),withheld=plant.hard_mode_withheld,unit_params=plant.unit().params,calcs=plant.recompute_calcs)
    np.testing.assert_array_equal(truth.states,states)
    for tag in full.values:
        if tag in plant.hard_mode_withheld:
            assert tag not in sparse.values
        else:
            np.testing.assert_array_equal(full.values[tag],sparse.values[tag])

def test_public_event_journal_uses_digital_clock_and_real_quality():
    import pandas as pd
    from historiansim.measurement.events import public_status_journal
    from historiansim.measurement.apply import MeasuredData
    from historiansim.plants.stamping_press.cycles import EventLog
    events=EventLog()
    events.append(dict(time_s=.10049,kind='feed_complete',count=0,pitch_mm=999,rejected=True))
    events.append(dict(time_s=1.10051,kind='stroke_complete',count=1,pitch_mm=999,rejected=True))
    values={tag:np.ones(3) for tag in ('DI-271','DI-272','COUNT-271')}
    quality={tag:np.zeros(3,dtype=np.uint8) for tag in values}
    quality['COUNT-271'][1]=2
    measured=MeasuredData(values,quality,{}, {},1.)
    origin=pd.Timestamp('2026-01-01',tz='UTC')
    journal=public_status_journal(events,measured,origin)
    assert list(journal.columns)==['timestamp','event_code','count','quality']
    assert (journal.timestamp-origin).dt.total_seconds().tolist()==[.100,1.101]
    assert journal.event_code.tolist()==[2,-1]
    assert journal['count'].iloc[0]==0 and np.isnan(journal['count'].iloc[1])
    assert journal.quality.tolist()==[0,2]
    assert not any('pitch' in c or 'reject' in c for c in journal.columns)

def test_native_writer_and_challenge_preserve_safe_cycle_journal(tmp_path):
    import pandas as pd
    from historiansim.scenarios import build_scenario
    from historiansim.pipeline import generate,write_dataset
    from historiansim.challenge import make_challenge
    cfg=build_scenario('stamping-press-rca',profile='quick',seed=7,days=300/86400)
    cfg.episodes.n_faults=0;cfg.episodes.n_benign=0;cfg.episodes.baseline_days=0
    dataset=generate(cfg)
    out=tmp_path/'private';write_dataset(dataset,out)
    journal=pd.read_parquet(out/'cycle_event_journal.parquet')
    assert set(journal.columns)=={'timestamp','event_code','count','quality'}
    good=journal[journal.quality==0]
    strokes=good[good.event_code==1]
    assert strokes['count'].is_monotonic_increasing
    assert (strokes['count'].diff().dropna()>=1).all()
    assert len(journal)==len(dataset.truth.events)
    assert journal.timestamp.is_monotonic_increasing
    assert (journal.timestamp.astype('int64')%1000000==0).all()
    observed=strokes[strokes.timestamp<=dataset.index[-1]]
    assert observed['count'].max()==dataset.truth.signals['COUNT-271'][-1]
    assert strokes['count'].max()==max(event['count'] for event in dataset.truth.events)
    public=tmp_path/'public';make_challenge(out,public)
    assert (public/'cycle_event_journal.parquet').read_bytes()==(out/'cycle_event_journal.parquet').read_bytes()

def test_independent_shaft_and_strip_measurements_separate_physical_slip():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    from historiansim.plants.stamping_press.tags import recompute_dcs_calculations
    unit,u,x,_=design_point()
    p={**unit.params,'traction':.8}
    x[1]=80.
    event=unit.cycle_event_source(x,u,DESIGN_D,p)
    event.phase=.25
    observed=event.observations(0,x,u,DESIGN_D,p)
    assert observed['ZI-274']>observed['ZI-275']
    assert observed['ZI-276']==100.
    values={k:np.array([v]) for k,v in observed.items()}
    recompute_dcs_calculations(values,p)
    assert values['CALC-TRAVEL-GAP'][0]==20.

def test_native_sweep_observer_receives_actual_measured_pair():
    from historiansim.plants import get_plant
    from historiansim.validation.catalog import sweep_catalog
    seen=[]
    def observer(cid,measured,twin,cfg,truth,truth_twin):
        assert cid=='RC-A1'
        assert measured.n==twin.n==cfg.time.n_steps
        assert 'SIC-271.PV' in measured.values and 'SIC-271.SP' in measured.values
        assert measured is not twin and truth is not truth_twin
        np.testing.assert_allclose(truth.signals['SI-271'],truth.states[:,0]*60/(2*np.pi))
        np.testing.assert_array_equal(truth.signals['PI-272'],truth.states[:,3])
        np.testing.assert_array_equal(truth.signals['TI-271'],truth.states[:,5])
        seen.append(cid)
    result=sweep_catalog(get_plant('stamping_press'),days=.002,onset_s=60,causes=['RC-A1'],observer=observer)
    assert list(result)==seen==['RC-A1']
    without=sweep_catalog(get_plant('stamping_press'),days=.002,onset_s=60,causes=['RC-A1'])
    assert without==result

def test_piece_classification_waits_for_exact_inspection_transport():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    unit,u,x,_=design_point();event=unit.cycle_event_source(x,u,DESIGN_D,unit.params)
    for k in range(100):x=event.advance(k*.1,x,u,DESIGN_D,unit.params,.1,1)
    assert event.completed==10
    assert event.good+event.reject==0
    assert event.completed==event.good+event.reject+len(event.pending)
    for k in range(100,115):x=event.advance(k*.1,x,u,DESIGN_D,unit.params,.1,1)
    arrivals=[e for e in event.events if e['kind']=='inspection_delivery']
    strokes=[e for e in event.events if e['kind']=='stroke_complete']
    assert len(arrivals)==1
    assert abs(arrivals[0]['time_s']-strokes[0]['time_s']-10)<1e-9
    assert event.good+event.reject==1

def test_public_quality_counters_use_delayed_measured_gauge_gain():
    from historiansim.plants import get_plant
    from historiansim.core.sim import simulate,ConstantDisturbance
    from historiansim.config.schema import ScenarioConfig,TimeConfig
    from historiansim.measurement.apply import measure
    from historiansim.faults.base import InstrumentFault,Step
    from historiansim.core.rng import SeedBank
    from historiansim.plants.stamping_press.loops import DESIGN_D,plant_loops
    plant=get_plant('stamping_press')
    cfg=ScenarioConfig(name='inspection-gain',unit='stamping_press',time=TimeConfig(days=21/86400,dt_scan=1,dt_sim=.1),loops=plant_loops())
    truth=simulate(cfg,ConstantDisturbance(DESIGN_D))
    fault=InstrumentFault(id='gain',tag='QI-271',mode='scale',magnitude=.01,onset_s=5,profile=Step())
    measured=measure(truth,plant.tags(),SeedBank(7),instrument_faults=[fault],unit_params=plant.unit().params,calcs=plant.recompute_calcs)
    assert np.all(measured.values['COUNT-272'][:11]==0)
    assert np.all(measured.values['COUNT-273'][:11]==0)
    assert measured.values['COUNT-273'][-1]>0
    assert truth.signals['COUNT-272'][-1]>0  # Physical part is good; acquired gauge rejects it.
    np.testing.assert_array_equal(measured.values['COUNT-271'],measured.values['COUNT-272']+measured.values['COUNT-273']+measured.values['COUNT-274'])

def test_pulse_encoder_quantization_is_the_actual_feedback_reading():
    from historiansim.pipeline import _build_sensor_fn
    from historiansim.core.rng import SeedBank
    from historiansim.scenarios import build_scenario
    from historiansim.faults.base import InstrumentFault,Step
    cfg=build_scenario('stamping-press-rca',profile='quick',seed=7,days=.001)
    fault=InstrumentFault(id='encoder',tag='FDC-271.PV',mode='scale',magnitude=.03,onset_s=0,profile=Step())
    sensor=_build_sensor_fn(cfg,[fault],cfg.time.n_steps,cfg.time.dt_scan,SeedBank(7))
    from historiansim.plants.stamping_press.loops import design_point
    seen=sensor(design_point()[3],0)
    step=250/65536
    assert seen['ZI-271']==round(103/step)*step

def test_feed_plan_is_continuous_and_debits_its_actual_completed_travel():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    from historiansim.plants.stamping_press.cycles import PressCycleEvents
    from historiansim.plants.stamping_press.compiled_backend import CompiledPressCycleEvents
    for backend in (PressCycleEvents,CompiledPressCycleEvents):
        unit,u,x,_=design_point();u['FEED-271']=.3
        event=backend(unit,x,u,DESIGN_D,unit.params)
        x=event.advance(0,x,u,DESIGN_D,unit.params,.499999,1)
        before=event.observations(.499999,x,u,DESIGN_D,unit.params)
        x=event.advance(.499999,x,u,DESIGN_D,unit.params,.000002,1)
        after=event.observations(.500001,x,u,DESIGN_D,unit.params)
        for tag in ('ZI-274','ZI-275'):
            assert 0<=after[tag]-before[tag]<1e-6
        assert after['ZI-272']==after['ZI-276']==100.
        expected_mass=.1*unit.params['strip_width']*DESIGN_D['thickness']*unit.params['strip_density']
        assert abs(event.withdrawn_mass-expected_mass)<1e-12
        # The changing envelope schedules the next cycle; it cannot rewrite
        # this feed's already executed endpoint or withdrawn physical stock.
        assert x[1]<after['ZI-272']
        x=event.advance(.500001,x,u,DESIGN_D,unit.params,.499999,1)
        next_plan=float(x[1])
        x=event.advance(1.,x,u,DESIGN_D,unit.params,.500001,1)
        assert abs(event.pitch-next_plan)<1e-6
        assert event.pitch<100.


def test_latched_feed_plan_has_finite_acceleration_in_both_backends():
    from historiansim.plants.stamping_press.loops import design_point,DESIGN_D
    from historiansim.plants.stamping_press.cycles import PressCycleEvents
    from historiansim.plants.stamping_press.compiled_backend import CompiledPressCycleEvents
    for backend in (PressCycleEvents,CompiledPressCycleEvents):
        unit,u,x,_=design_point();u['FEED-271']=.3
        event=backend(unit,x,u,DESIGN_D,unit.params)
        positions=[0.]
        for k in range(501):
            x=event.advance(k*.001,x,u,DESIGN_D,unit.params,.001,1)
            positions.append(event.observations((k+1)*.001,x,u,DESIGN_D,unit.params)['ZI-275'])
        velocities=np.diff(positions)/.001
        accelerations=np.diff(velocities)/.001
        assert np.min(velocities)>-1e-6
        assert np.max(velocities)<401.
        assert np.max(np.abs(accelerations))<1601.
        assert abs(positions[-1]-100)<1e-8
