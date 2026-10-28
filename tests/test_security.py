import json
import subprocess
import pytest
from pathlib import Path
from ekas_press_intelligence.sandbox import sandbox_command


def test_os_boundary_hides_truth_configuration_environment_and_source(tmp_path):
    secret = tmp_path / 'truth.json'
    secret.write_text('PRIVATE ANSWERS')
    code = '''import os,json, pathlib, socket
out={}
for label,path in [('truth',%r),('source',%r),('home','/home/pat'),('env','/proc/1/root/home/pat')]:
 try: out[label]=pathlib.Path(path).read_text()
 except (OSError, IsADirectoryError): out[label]='DENIED'
out['credential']=os.environ.get('EKAS_TRUTH_TOKEN')
try:
 s=socket.create_connection(('1.1.1.1',443),timeout=.2);out['network']='OPEN'
except OSError:out['network']='DENIED'
print(json.dumps(out))
''' % (str(secret), str(__file__))
    p = subprocess.run(sandbox_command(code), capture_output=True, text=True,
                       env={'EKAS_TRUTH_TOKEN': 'must-not-leak'}, timeout=10)
    assert p.returncode == 0, p.stderr
    result = json.loads(p.stdout)
    assert result == {'truth':'DENIED','source':'DENIED','home':'DENIED',
                      'env':'DENIED','credential':None,'network':'DENIED'}


def test_runtime_rejects_an_unpinned_installed_simulator(monkeypatch,tmp_path):
    import historiansim
    from ekas_press_intelligence.simulator.upstream import verify_runtime,UpstreamNotReady
    monkeypatch.setattr(historiansim,'__file__',str(tmp_path/'unverified'/'__init__.py'))
    with pytest.raises(UpstreamNotReady):
        verify_runtime(Path(__file__).parents[1])
