"""Acceptance metrics must not turn shared bias or missing evidence into a pass."""
import numpy as np
from types import SimpleNamespace
from ekas_press_intelligence.native.qualification import envelope_metrics, measured_effects


def test_masking_uses_absolute_nominal_setpoint_not_twin_difference_or_tag_span():
    bad=envelope_metrics(np.full(100,102.),np.full(100,102.),100.,1.)
    assert bad['fault_minus_twin_peak']==0 and not bad['within_one_percent']
    assert bad['within_fraction']==0
    good=envelope_metrics(np.full(100,100.5),np.full(100,100.),100.,1.)
    assert good['within_one_percent'] and good['within_fraction']==1


def test_union_effects_require_actual_measurements_on_every_cause():
    twin=SimpleNamespace(values={'A':np.zeros(20),'B':np.arange(20,dtype=float)})
    fault=SimpleNamespace(values={'A':np.r_[np.zeros(5),np.ones(15)],'B':np.arange(20,dtype=float)+np.r_[np.zeros(5),-np.ones(15)]})
    result=measured_effects(fault,twin,['A','B'],5,20,3600.,{'A':.01,'B':.02})
    assert result['A']['sustained']==1 and result['B']['sustained']==-1
    import pytest
    with pytest.raises(ValueError,match='MISSING_MEASURED_EVIDENCE'):
        measured_effects(fault,twin,['C'],5,20,3600.,{})


def test_masking_requires_actual_closed_loop_mode_and_configured_headroom():
    from ekas_press_intelligence.native.qualification import masking_gate
    physical={'within_one_percent':True};load={'snr':10.,'sustained':2.,'noise_floor':.1}
    assert masking_gate(physical,load,np.full(10,50.),np.ones(10),3.,.1,.8)['qualifies']
    assert not masking_gate(physical,load,np.full(10,50.),np.zeros(10),3.,.1,.8)['qualifies']
    saturated=masking_gate(physical,load,np.full(10,80.),np.ones(10),3.,.1,.8)
    assert not saturated['qualifies'] and saturated['headroom_percent']==0


def test_measured_effects_reject_silently_truncated_or_unbound_pairs():
    import pytest
    a=SimpleNamespace(values={'A':np.arange(20,dtype=float)})
    b=SimpleNamespace(values={'A':np.arange(20,dtype=float)})
    with pytest.raises(ValueError,match='INVALID_MEASURED_EVIDENCE'):
        measured_effects(a,b,['A'],5,21,20.,{'A':.1})
    with pytest.raises(ValueError,match='INVALID_NOISE_FLOOR'):
        measured_effects(a,b,['A'],5,20,20.,{})


def test_matrix_config_rejects_wrong_rate_or_shortened_native_exposure():
    import pytest
    from ekas_press_intelligence.native.qualification import validate_matrix_config
    cfg=SimpleNamespace(unit='stamping_press',seed=19,ballast_tags=0,
        time=SimpleNamespace(days=14.,dt_scan=20.,n_steps=60480),
        episodes=SimpleNamespace(n_faults=0,n_benign=0,background_fouling=False),
        loops=[SimpleNamespace(name='SIC-271',sp=45.)])
    validate_matrix_config(cfg,19,45,60480,60480)
    with pytest.raises(ValueError,match='MATRIX_CONFIG_MISMATCH'):validate_matrix_config(cfg,19,75,60480,60480)
    cfg.time.days=7.
    with pytest.raises(ValueError,match='MATRIX_CONFIG_MISMATCH'):validate_matrix_config(cfg,19,45,60480,60480)


def _script(name):
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location(name,Path(__file__).resolve().parents[1]/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_matrix_source_epoch_rejects_replaced_manifest_and_is_write_once(tmp_path,monkeypatch):
    import pytest,json
    module=_script('qualify_press_matrix')
    runtime=tmp_path/'runtime';runtime.mkdir()
    manifest=runtime/'NATIVE_RUNTIME_PROVENANCE.json';manifest.write_text('{}')
    monkeypatch.setenv('EKAS_NATIVE_RUNTIME',str(runtime))
    epoch=tmp_path/'epoch.json';module.write_once(epoch,module.source_epoch())
    assert module.verify_epoch(epoch)
    assert epoch.stat().st_mode&0o777==0o400
    with pytest.raises(FileExistsError):module.write_once(epoch,{})
    manifest.write_text('{"changed":true}')
    with pytest.raises(RuntimeError,match='SOURCE_EPOCH_CHANGED'):module.verify_epoch(epoch)


def test_required_test_layer_rejects_failure_even_with_success_exit(tmp_path):
    module=_script('run_native_tests');report=tmp_path/'tests.xml'
    for body in ('<failure/>','<error/>','<skipped/>'):
        report.write_text('<testsuite><testcase name="real">'+body+'</testcase></testsuite>')
        assert module.assess_report(report,0,'core')[0]==1
    report.write_text('<testsuite><testcase name="real"/></testsuite>')
    assert module.assess_report(report,0,'core')[:2]==(0,None)
    assert module.assess_report(report,0,'upstream')[0]==1
    report.write_text('<broken')
    assert module.assess_report(report,0,'core')[1]=='MISSING_OR_INVALID_TEST_REPORT'


def test_matrix_cancellation_terminates_owned_batch_and_retains_failure(tmp_path,monkeypatch):
    import json,subprocess,sys,threading,time
    import pytest
    module=_script('qualify_press_matrix');real_popen=subprocess.Popen;owned=[]
    def spawn(*args,**kwargs):
        process=real_popen([sys.executable,'-c','import time;time.sleep(30)'],**kwargs)
        owned.append(process);module.STOP.set();return process
    monkeypatch.setattr(module.subprocess,'Popen',spawn)
    args=SimpleNamespace(output=tmp_path,epoch=tmp_path/'epoch',timeout=10)
    try:
        with pytest.raises(RuntimeError,match='MATRIX_CANCELLED'):module.launch(args,7,45,'subtle')
        assert owned and owned[0].poll() is not None
        result=json.loads(next(tmp_path.glob('*/runner_failure.json')).read_text())
        assert result['code']=='MATRIX_CANCELLED' and result['returncode']!=0
    finally:
        module.STOP.clear()
        for process in owned:
            if process.poll() is None:process.kill();process.wait()


def test_matrix_cancellation_reaps_descendant_that_ignores_term(tmp_path,monkeypatch):
    import os,subprocess,sys,time,signal
    import pytest
    module=_script('qualify_press_matrix');real_popen=subprocess.Popen;owned=[];pidfile=tmp_path/'child.pid'
    child="import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(30)"
    parent="import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c',%r]);Path(%r).write_text(str(p.pid));time.sleep(30)"%(child,str(pidfile))
    def spawn(*args,**kwargs):
        process=real_popen([sys.executable,'-c',parent],**kwargs);owned.append(process)
        deadline=time.monotonic()+5
        while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.01)
        time.sleep(.1);module.STOP.set();return process
    monkeypatch.setattr(module.subprocess,'Popen',spawn)
    try:
        with pytest.raises(RuntimeError,match='MATRIX_CANCELLED'):module.launch(SimpleNamespace(output=tmp_path,epoch=tmp_path/'epoch',timeout=10),7,45,'subtle')
        pid=int(pidfile.read_text());stat=__import__('pathlib').Path(f'/proc/{pid}/stat')
        assert not stat.exists() or stat.read_text().rsplit(')',1)[1].split()[0] in ('Z','X')
    finally:
        module.STOP.clear()
        if pidfile.exists():
            try:os.kill(int(pidfile.read_text()),signal.SIGKILL)
            except ProcessLookupError:pass
        for p in owned:
            if p.poll() is None:p.kill();p.wait()


def test_distribution_verifier_rejects_divergent_canonical_clients():
    import io,zipfile,pytest
    module=_script('verify_distributions')
    def wheel(content):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as archive:archive.writestr('ekas_historian_client/__init__.py',content)
        buffer.seek(0);return zipfile.ZipFile(buffer)
    with wheel('one') as sdk,wheel('two') as server:
        with pytest.raises(ValueError,match='different canonical'):module.verify_shared_client(sdk,server)
    with wheel('one') as sdk,wheel('one') as server:module.verify_shared_client(sdk,server)
