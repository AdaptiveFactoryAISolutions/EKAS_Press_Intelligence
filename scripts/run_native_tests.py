"""Reproducible native test layers; no empty or skipped layer can pass."""
import argparse
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

def assess_report(path,code,layer):
    try:cases=ET.parse(path).getroot().findall('.//testcase')
    except (OSError,ET.ParseError):return 1,'MISSING_OR_INVALID_TEST_REPORT',[]
    if code:return code,None,cases
    if not cases or any(any(c.find(tag) is not None for tag in ('skipped','failure','error')) for c in cases):
        return 1,'EMPTY_OR_UNSUCCESSFUL_REQUIRED_LAYER',cases
    if layer=='upstream' and len(cases)<181:return 1,'UPSTREAM_TESTS_MISSING',cases
    return 0,None,cases


def main():
    parser=argparse.ArgumentParser();parser.add_argument('layer',choices=('core','browser','physics','upstream'));parser.add_argument('--timeout',type=int,default=14400)
    args=parser.parse_args()
    def interrupted(*_):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    if not 1<=args.timeout<=21600:parser.error('timeout must be1..21600 seconds')
    report=ROOT/'work/native-test-reports'/args.layer/str(uuid4());report.mkdir(parents=True)
    env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for name in ('EKAS_NATIVE_RUNTIME','EKAS_NATIVE_REPO_ROOT','EKAS_NATIVE_STATE_DIR','EKAS_NATIVE_TOKENS',
                 'EKAS_NATIVE_LOCAL_ONLY','EKAS_NATIVE_TEST_REFERENCE_RUNTIME','EKAS_NATIVE_MAX_ESTIMATED_BYTES',
                 'EKAS_NATIVE_MAX_RSS_BYTES','EKAS_NATIVE_MIN_AVAILABLE_BYTES'):
        env.pop(name,None)
    for name in ('PYTEST_ADDOPTS','PYTEST_PLUGINS'):env.pop(name,None)
    env['PYTHONPYCACHEPREFIX']=str(report/'import-cache')
    cwd=ROOT;runtime_manifest=None;test_identity=None
    if args.layer=='core':
        targets=[str(p.relative_to(ROOT)) for p in sorted((ROOT/'tests').glob('test_native_*.py')) if p.name!='test_native_browser.py']
        targets+=['tests/test_reference_runtime.py']
    elif args.layer=='browser':
        targets=['tests/test_native_browser.py']
        env['EKAS_NATIVE_BROWSER_ARTIFACTS']=str(report/'browser-artifacts')
    elif args.layer=='physics':
        runtime=report/'native-runtime';reference=report/'reference-runtime'
        for script,target in [('prepare_native_runtime.py',runtime),('prepare_reference_runtime.py',reference)]:
            subprocess.run([sys.executable,str(ROOT/'scripts'/script),'--target',str(target)],check=True,cwd=ROOT,env=env)
        runtime_manifest=hashlib.sha256((runtime/'NATIVE_RUNTIME_PROVENANCE.json').read_bytes()).hexdigest()
        env['PYTHONPATH']=str(runtime/'src')+os.pathsep+str(ROOT/'src')
        env['EKAS_NATIVE_RUNTIME']=str(runtime)
        env['EKAS_NATIVE_TEST_REFERENCE_RUNTIME']=str(reference)
        targets=['tests/test_press_native.py','extensions/stamping_press/pfd/test_press_pfd.py']
    else:
        runtime=report/'native-runtime'
        subprocess.run([sys.executable,str(ROOT/'scripts/prepare_native_runtime.py'),'--target',str(runtime)],check=True,cwd=ROOT,env=env)
        runtime_manifest=hashlib.sha256((runtime/'NATIVE_RUNTIME_PROVENANCE.json').read_bytes()).hexdigest()
        manifest=json.loads((runtime/'NATIVE_RUNTIME_PROVENANCE.json').read_text())
        test_identity={'kind':manifest['test_suite_kind'],'upstream_commit':manifest['upstream_commit'],
                       'source_tests_sha256':hashlib.sha256(json.dumps(manifest['source_tests_sha256'],sort_keys=True).encode()).hexdigest(),
                       'runtime_tests_sha256':hashlib.sha256(json.dumps(manifest['runtime_tests_sha256'],sort_keys=True).encode()).hexdigest(),
                       'configuration_sha256':manifest['test_configuration_sha256'],'patches':manifest['patches'],'compatibility_changes':manifest['test_compatibility_changes']}
        cwd=runtime;targets=['tests']
        env['PYTHONPATH']=str(runtime/'src')+os.pathsep+str(cwd)
    if not targets:raise SystemExit('No native test targets')
    command=[sys.executable,'-B','-m','pytest','-q',*targets,'--junitxml='+str(report/'tests.xml')]
    started=time.time();code=1;reason=None
    with (report/'stdout.log').open('w') as log:
        process=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=process.wait(timeout=args.timeout)
        except (subprocess.TimeoutExpired,KeyboardInterrupt) as exc:
            reason='TEST_TIMEOUT' if isinstance(exc,subprocess.TimeoutExpired) else 'TEST_INTERRUPTED'
            from ekas_press_intelligence.native.qualification import terminate_owned
            terminate_owned(process)
    code,report_reason,cases=assess_report(report/'tests.xml',code,args.layer)
    reason=reason or report_reason
    result={'layer':args.layer,'returncode':code,'reason':reason,'cases':len(cases),'skipped':sum(c.find('skipped') is not None for c in cases),'elapsed_seconds':time.time()-started,'test_suite_identity':test_identity,'runtime_manifest_sha256':runtime_manifest,'command':command,'report_directory':str(report)}
    (report/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return code

if __name__=='__main__':raise SystemExit(main())
