"""Connected-line numerical contracts, using the actual native UnitModel interface."""
import importlib
import sys
from pathlib import Path
import pytest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/HistorianSim/src'))
sys.path.insert(0,str(ROOT/'src'))

def plant():
    return importlib.import_module('extensions.stamping_line')

def run(seconds=300,step=.1,changes=None):
    unit=plant().StampingLine(); p=unit.params.copy();p['compiled_cycles']=0.; d={'T_amb':20.}
    u=unit.steady_inputs({},d,p);x=unit.steady_state(u,d,p);e=unit.cycle_event_source(x,u,d,p)
    for t in np.arange(0,seconds,step):
        active={**p,**(changes(t) if changes else {})}
        x=e.advance(float(t),x,u,d,active,step,1)
    return unit,e,x

def test_native_unit_registration_and_accounting():
    from historiansim.plants.unit import UnitModel
    assert issubclass(plant().StampingLine,UnitModel)
    assert plant().PLANT.name=='stamping_line'
    unit,e,x=run()
    assert e.completed==40
    assert e.produced==31  # first finished piece on stroke ten
    assert e.packed>0
    assert abs(e.material_residual())<1e-8
    assert e.produced==e.packed+e.rejected+len(e.discharge)+len(e.washer)+e.pack_queue
    assert abs(e.energy_in-e.energy_forming-e.energy_loss)<1e-6
    assert all('AUDIT' not in t.name for t in plant().plant_tags())

def test_packing_bottleneck_blocks_without_losing_parts():
    _,e,_=run(900,changes=lambda t:{'packing_factor':0.})
    assert e.blocked and e.completed<120
    assert abs(e.material_residual())<1e-8
    assert e.produced==len(e.discharge)+len(e.washer)+e.pack_queue

def test_faults_are_real_and_sensor_fault_is_acquisition_only():
    catalog=plant().CATALOG
    assert len(catalog.causes)>=8
    _,a,_=run(120)
    _,b,_=run(120,changes=lambda t:{'feed_traction':.8})
    assert b.completed==0 and a.completed>0
    assert abs(b.material_residual())<1e-8

def test_convergence_and_stop_resume():
    _,a,_=run(300,.1)
    _,b,_=run(300,.25)
    assert (a.completed,a.produced,a.packed)==(b.completed,b.produced,b.packed)
    assert a.remaining_kg==pytest.approx(b.remaining_kg,rel=0,abs=.001)
    _,c,_=run(300,changes=lambda t:{'run_enable':0. if 90<=t<150 else 1.})
    assert c.completed<a.completed and c.completed>0
    assert abs(c.material_residual())<1e-8

def test_real_native_acquisition_failure_does_not_change_inventory():
    import os,subprocess
    code="import sys,numpy as np\nfrom pathlib import Path\nroot=Path.cwd()\nfrom scripts.prepare_native_runtime import prepare_runtime\nruntime=prepare_runtime(root,root/'work/test-native-line-runtime')\nsys.path.insert(0,str(runtime/'src'))\nsys.path.insert(0,str(root/'src'))\nfrom historiansim import pipeline\nfrom historiansim.config.schema import ScenarioConfig\nfrom ekas_press_intelligence.line_setup import LineSetup,native_config\n# A sensor-only fault must leave true physical inventory and stroke ledgers intact.\nhealthy=pipeline.generate(ScenarioConfig.model_validate(native_config(LineSetup(duration_minutes=10))))\nfailed=pipeline.generate(ScenarioConfig.model_validate(native_config(LineSetup(duration_minutes=10,test_case='station_sensor',fault_start_minutes=1))))\nfor name in ('WI-COIL','COUNT-STROKES','COUNT-PRODUCED','COUNT-PACKED'):\n    assert np.array_equal(healthy.truth.signals[name],failed.truth.signals[name])\nassert not np.array_equal(healthy.measured.values['DI-STATION-05'],failed.measured.values['DI-STATION-05'])\nassert 'AUDIT-MATERIAL-RELATIVE-RESIDUAL' not in healthy.measured.values"
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'},capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr


def test_private_engineering_rejects_tampered_ledger():
    from types import SimpleNamespace
    from extensions.stamping_line.cycles import engineering_acceptance
    _,e,x=run(30)
    signals={k:np.array([v]) for k,v in e.observations(30,x,{'DRIVE-1500':.8},{'T_amb':20},plant().StampingLine().params).items()}
    assert engineering_acceptance(SimpleNamespace(signals=signals))['passed']
    signals['AUDIT-COIL-REMAINING-KG']+=1
    with pytest.raises(ValueError,match='MISMATCH'):engineering_acceptance(SimpleNamespace(signals=signals))

def test_actual_drive_power_and_lubrication_change_energy_demand():
    unit,e,x=run(300)
    p=unit.params;d={'T_amb':20};u={'DRIVE-1500':.8}
    observed=e.observations(300,x,u,d,p)
    assert observed['JI-DRIVE']*1000==pytest.approx(observed['II-DRIVE']*3**.5*p['voltage_v']*p['power_factor'])
    higher=e.observations(300,x,u,d,{**p,'lube_factor':.5})
    assert higher['JI-DRIVE']>observed['JI-DRIVE']
    assert observed['DI-STATION-10']==1
    _,empty,xx=run(0)
    assert empty.observations(0,xx,u,d,p)['DI-STATION-10']==0
    e.stop_requested=True;e.advance(300,x,u,d,p,.1,1)
    assert e.observations(300.1,x,u,d,p)['JI-DRIVE']<observed['JI-DRIVE']

def test_feed_slip_moves_strip_and_holds_physical_inventory():
    unit,e,x=run(30,changes=lambda t:{'feed_traction':.8})
    obs=e.observations(30,x,{'DRIVE-1500':.8},{'T_amb':20},{**unit.params,'feed_traction':.8})
    assert obs['ZI-FEED-SHAFT']>obs['ZI-FEED-STRIP']>0
    assert obs['DI-FEED']==0
    assert e.completed==0
    assert abs(e.material_residual())<1e-8

def test_washer_heater_is_actual_and_cleaning_responds_during_residence():
    unit,e,x=run(120)
    p={**unit.params,'compiled_cycles':0.};u={'DRIVE-1500':.8};d={'T_amb':20}
    # At equilibrium actual heater must cover losses, not report its installed rating.
    signals=unit.signals(0,unit.steady_state(u,d,p),u,d,p)
    assert 0<signals['JI-HEATER']<p['heater_kw']
    _,healthy,_=run(300)
    _,failed,_=run(300,changes=lambda t:{'spray_factor':0.} if t>=90 else {})
    assert failed.rejected>healthy.rejected
    assert signals['LI-WASH']==p['washer_volume_l']
    assert 'LI-LUBE' in signals

def test_coil_replacement_is_counted_and_mass_conserved():
    unit=plant().StampingLine({'coil_mass_kg':10.});p={**unit.params,'compiled_cycles':0.};u={'DRIVE-1500':.8};d={'T_amb':20};x=unit.steady_state(u,d,p);e=unit.cycle_event_source(x,u,d,p)
    for t in np.arange(0,300,.1):x=e.advance(t,x,u,d,p,.1,1)
    assert e.coils_loaded>1
    assert abs(e.material_residual())<1e-8

def test_washer_thermal_energy_and_water_inventory_close():
    unit,e,x=run(300,changes=lambda t:{'heater_factor':.1} if t>=100 else {})
    obs=e.observations(300,x,{'DRIVE-1500':.8},{'T_amb':20},unit.params)
    assert obs['AUDIT-WASHER-ENERGY-RELATIVE-RESIDUAL']<.001
    assert obs['AUDIT-WASHER-WATER-RELATIVE-RESIDUAL']<1e-6

def test_force_displacement_integral_matches_declared_work():
    unit,e,x=run(120);p={**unit.params,'compiled_cycles':0.};u={'DRIVE-1500':.8};d={'T_amb':20}
    e.feed_strip_m=p['progression_mm']*.001
    coords=[];loads=[]
    for phase in np.linspace(0,.5,20001):
        e.phase=phase;obs=e.observations(120,x,u,d,p);coords.append(obs['ZI-RAM']/1000);loads.append(obs['WI-TOTAL']*1000)
    assert np.trapezoid(loads,coords)==pytest.approx(p['work_per_stroke_j'],rel=.001)

def test_numerical_quantum_convergence_halves_actual_steps():
    _,a,xa=run(300,changes=lambda t:{'integration_step_s':.1})
    _,b,xb=run(300,changes=lambda t:{'integration_step_s':.05})
    assert b.integration_steps>=1.9*a.integration_steps
    assert (a.completed,a.produced,a.packed,a.rejected)==(b.completed,b.produced,b.packed,b.rejected)
    assert a.remaining_kg==pytest.approx(b.remaining_kg,rel=0,abs=.001)
    assert xa[1]==pytest.approx(xb[1],abs=.01)

def test_straightener_has_finite_speed_response_and_load_recipe():
    unit,e,x=run(8)
    p=unit.params;obs=e.observations(8,x,{'DRIVE-1500':.8},{'T_amb':20},p)
    assert obs['WI-STRAIGHTENER-LOAD']>0
    assert 0<=obs['SI-STRAIGHTENER']<=p['straightener_speed_m_s']
    assert obs['ZI-STRAIGHTENER-GAP']==pytest.approx(p['thickness_mm']*.95)

def test_native_journal_codes_preserve_existing_press_meanings():
    _,e,_=run(180)
    assert set(e.events.kind)>={1,4,5}
    assert all(event['kind'] in ('stroke_complete','product_discharge','packed','feed_complete') for event in e.events)
    assert e.events.public_status_columns()[3][1]=='COUNT-STROKES'
    assert e.events.public_status_columns()[3][4]=='COUNT-PRODUCED'
    assert e.events.public_status_columns()[3][5]=='COUNT-PACKED'

def test_geometry_changes_forming_force_work_and_drive_demand():
    unit,e,x=run(120);p={**unit.params,'compiled_cycles':0.};u={'DRIVE-1500':.8};d={'T_amb':20}
    e.feed_strip_m=.8;e.phase=.475
    normal=e.observations(120,x,u,d,p)
    thicker=e.observations(120,x,u,d,{**p,'thickness_mm':3.})
    assert thicker['WI-TOTAL']>normal['WI-TOTAL']
    assert thicker['JI-DRIVE']>normal['JI-DRIVE']

def test_multiout_reserves_entire_outgoing_batch_before_cycle():
    unit=plant().StampingLine({'parts_per_stroke':4.,'buffer_parts':4.});p={**unit.params,'compiled_cycles':0.};u={'DRIVE-1500':.8};d={'T_amb':20};x=unit.steady_state(u,d,p);e=unit.cycle_event_source(x,u,d,p)
    maximum=0
    for t in np.arange(0,300,.1):
        x=e.advance(t,x,u,d,p,.1,1);maximum=max(maximum,len(e.discharge))
    assert maximum<=4
    assert e.produced>0
    assert e.produced==e.packed+e.rejected+len(e.discharge)+len(e.washer)+e.pack_queue
    assert abs(e.material_residual())<1e-8

def test_native_multiout_with_insufficient_batch_capacity_never_overflows():
    unit=plant().StampingLine({'parts_per_stroke':4.,'buffer_parts':1.});p={**unit.params,'compiled_cycles':0.};u={'DRIVE-1500':.8};d={'T_amb':20};x=unit.steady_state(u,d,p);e=unit.cycle_event_source(x,u,d,p)
    for t in np.arange(0,120,.1):
        x=e.advance(t,x,u,d,p,.1,1)
        assert len(e.discharge)<=1
    assert e.blocked
    assert abs(e.material_residual())<1e-8

def test_compiled_line_backend_is_available_for_equivalence_contract():
    from extensions.stamping_line.compiled_backend import CompiledLineCycleEvents
    from extensions.stamping_line.cycles import LineCycleEvents
    assert issubclass(CompiledLineCycleEvents,LineCycleEvents)

def test_catalog_has_recognized_evidence_over_same_complete_instrument_union():
    causes=list(plant().CATALOG.causes.values())
    union={ev.tag for cause in causes for ev in cause.evidence}
    assert len(union)>=8
    for cause in causes:
        assert {ev.tag for ev in cause.evidence}==union
        assert all(ev.expectation in ('flat','rises','falls','steps','erratic','frozen') for ev in cause.evidence)


def test_compiled_and_reference_match_dynamic_faults_queues_stops_and_every_observation():
    import os,subprocess
    code="import sys,time,json\nfrom pathlib import Path\nimport numpy as np\nfrom scripts.prepare_native_runtime import prepare_runtime\nruntime=prepare_runtime(Path.cwd(),Path.cwd()/'work/test-line-equivalence-runtime')\nsys.path.insert(0,str(runtime/'src'))\nfrom historiansim.plants.stamping_line.model import StampingLine\nfrom historiansim.plants.stamping_line.cycles import LineCycleEvents,engineering_acceptance\nfrom historiansim.plants.stamping_line.compiled_backend import CompiledLineCycleEvents,SCALARS\ncases={'healthy':{},'feed':{'feed_traction':.8},'supply':{'supply_factor':0.},'lube':{'lube_factor':.2},'scrap':{'scrap_factor':0.},'cold':{'heater_factor':0.},'spray':{'spray_factor':.2},'pack':{'packing_factor':0.},'multi':{'parts_per_stroke':4.,'buffer_parts':4.},'coil':{'coil_mass_kg':10.}}\nsummary={};started=time.monotonic()\nfor case,overrides in cases.items():\n    unit=StampingLine({'compiled_cycles':0.,**(overrides if case in ('multi','coil') else {})});p=unit.params;u={'DRIVE-1500':.8};d={'T_amb':20.}\n    x=unit.steady_state(u,d,p);y=x.copy();a=LineCycleEvents(unit,x,u,d,p);b=CompiledLineCycleEvents(unit,y,u,d,p)\n    worst=0.\n    for t in range(300):\n        active={**p,**(overrides if 60<=t<210 else {})}\n        a.stop_requested=b.stop_requested=120<=t<150\n        x=a.advance(t,x,u,d,active,.1,10);y=b.advance(t,y,u,d,active,.1,10)\n        if not np.allclose(x,y,rtol=1e-11,atol=1e-9):raise AssertionError((case,t,'state',x,y))\n        for name in SCALARS:\n            av,bv=getattr(a,name),getattr(b,name)\n            if name in ('integration_steps','completed','produced','packed','rejected','pack_queue','containers','container_fill','coils_loaded','blocked','running','feed_complete','feed_failed'):\n                if av!=bv:raise AssertionError((case,t,name,av,bv))\n            elif not np.isclose(av,bv,rtol=1e-10,atol=1e-8):raise AssertionError((case,t,name,av,bv))\n        for left,right in ((a.discharge,b.discharge),(a.washer,b.washer)):\n            if not np.allclose(np.array(list(left)),np.array(list(right)),rtol=1e-10,atol=1e-8):raise AssertionError((case,t,'queue',list(left),list(right)))\n        if list(a.events.kind)!=list(b.events.kind) or list(a.events.count)!=list(b.events.count):raise AssertionError((case,t,'events'))\n        if not np.allclose(a.events.time,b.events.time,rtol=0,atol=1e-8):raise AssertionError((case,t,'event_times'))\n        oa=a.observations(t+1,x,u,d,active);ob=b.observations(t+1,y,u,d,active)\n        for key in oa:\n            if not np.isclose(oa[key],ob[key],rtol=1e-9,atol=1e-7):raise AssertionError((case,t,key,oa[key],ob[key]))\n        worst=max(worst,float(np.max(np.abs(x-y))))\n    summary[case]={'worst_state_abs':worst,'strokes':a.completed,'produced':a.produced,'events':len(a.events)}\n    print(case,summary[case],flush=True)\nsummary['elapsed_s']=time.monotonic()-started\nPath('work/line-compiled-equivalence.json').write_text(json.dumps(summary,indent=2))\n"
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'},capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr


def test_lube_makeup_preserves_finite_inventory_ledger():
    unit,e,x=run(300)
    obs=e.observations(300,x,{'DRIVE-1500':.8},{'T_amb':20},unit.params)
    assert obs['AUDIT-LUBE-MAKEUP-L']>0
    assert obs['AUDIT-LUBE-LOSS-L']>0
    assert 1<x[4]<50
    assert obs['AUDIT-LUBE-MATERIAL-RELATIVE-RESIDUAL']<1e-6

def test_loop_tags_enable_real_native_pv_acquisition_and_percent_scaling():
    tags={tag.name:tag for tag in plant().plant_tags()}
    assert tags['SIC-1500.PV'].role=='PV'
    assert tags['SIC-1500.OP'].role=='OP'
    assert tags['CALC-FEED-ERROR'].role=='CALC'
    assert tags['CALC-FEED-ERROR'].node==tags['ZI-FEED-SHAFT'].node==tags['ZI-FEED-STRIP'].node

def test_catalog_cross_references_never_eliminate_same_signature_competitors():
    causes=plant().CATALOG.causes
    for cause in causes.values():
        for evidence in cause.evidence:
            for competitor in evidence.rules_out:
                other=next(ev for ev in causes[competitor].evidence if ev.tag==evidence.tag)
                assert other.expectation!=evidence.expectation
            if evidence.expectation!='flat':
                compatible={cid for cid,other in causes.items() if next(ev for ev in other.evidence if ev.tag==evidence.tag).expectation==evidence.expectation}
                assert set(evidence.rules_in)==compatible
