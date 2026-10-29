"""Real wizard→SQLite→owned native worker→public evidence, without route mocks."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4
import httpx
import pytest
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def native_line_web():
    base=Path(os.environ.get('EKAS_NATIVE_BROWSER_ARTIFACTS',ROOT/'work/guided-line-browser'))
    report=base/('full-flow-'+str(uuid4()));report.mkdir(parents=True)
    existing=os.environ.get('EKAS_NATIVE_LINE_ACCEPTANCE_URL')
    process=None;log=None;token='line-acceptance-admin' if not existing else ''
    if existing:url=existing
    else:
        spec=importlib.util.spec_from_file_location('full_line_runtime',ROOT/'scripts/prepare_native_runtime.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        runtime=module.prepare_runtime(ROOT,report/'runtime')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        url=f'http://127.0.0.1:{port}'
        env=dict(os.environ,EKAS_NATIVE_RUNTIME=str(runtime),EKAS_NATIVE_STATE_DIR=str(report/'state'),
                 EKAS_NATIVE_TOKENS=json.dumps({token:'admin','line-acceptance-reader':'analyst'}),
                 OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',EKAS_NATIVE_BLAS_THREADS='1')
        log=(report/'service.log').open('w')
        process=subprocess.Popen([sys.executable,'-m','uvicorn','ekas_press_intelligence.native.api:create_native_app',
            '--factory','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    headers={'Authorization':'Bearer '+token} if token else {}
    try:
        with httpx.Client(base_url=url,headers=headers,timeout=30) as client:
            for _ in range(200):
                if process and process.poll() is not None:raise AssertionError((report/'service.log').read_text()[-2000:])
                try:
                    if client.get('/v2/health').status_code==200:break
                except httpx.ConnectError:pass
                time.sleep(.1)
            else:raise AssertionError('Actual line service did not start')
            assert client.get('/v2/line/preset').json()['runtime_ready']
            yield client,url,token,report
    finally:
        if process:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        if log:log.close()


def test_actual_wizard_runs_connected_line_and_explores_real_evidence(native_line_web):
    client,url,token,report=native_line_web
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1500,'height':1100});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url)
        if token:
            page.get_by_role('button',name='Access',exact=True).click()
            page.get_by_label('Bearer token',exact=True).fill(token)
            page.get_by_role('button',name='Apply credential',exact=True).click()
        expect(page.locator('#connection-status')).to_contain_text('admin')
        page.get_by_role('button',name='Guided press setup',exact=True).click()
        page.get_by_label('Setup name',exact=True).fill('Verified ten-station practice line')
        for _ in range(5):page.get_by_role('button',name='Next',exact=True).click()
        page.locator('#setup-duration_minutes').fill('10')
        for _ in range(2):page.get_by_role('button',name='Next',exact=True).click()
        page.get_by_role('button',name='Check setup',exact=True).click()
        run=page.get_by_role('button',name='Run practice',exact=True)
        expect(run).to_be_enabled()
        page.screenshot(path=str(report/'01-ready-to-run.png'),full_page=True)
        with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/run')) as response:
            run.click()
        job=response.value.json();assert response.value.status==201
        ident=job['id'];deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            job=client.get('/v2/jobs/'+ident).json()
            if job['state'] in ('succeeded','failed','interrupted','cancelled'):break
            time.sleep(.25)
        (report/'actual-job.json').write_text(json.dumps(job,indent=2))
        assert job['state']=='succeeded',job.get('error')
        result=job['result'];assert result['passed'] is None
        assert result['engineering_acceptance']['passed']
        assert result['qualification_status']=='UNQUALIFIED_PRACTICE'
        assert len(result['line_setup']['model_sha256'])==64
        dataset_id=result['dataset_id']
        dataset=client.get('/v2/datasets/'+dataset_id).json()
        assert dataset['status']=='UNVALIDATED'
        assert dataset['line_setup']['config_sha256']==result['line_setup']['config_sha256']
        samples=client.get('/v2/datasets/'+dataset_id+'/samples',params={
            'tags':'SIC-1500.PV,COUNT-PRODUCED,COUNT-PACKED','source':'raw','max_points':10000})
        assert samples.status_code==200 and samples.json()['rows']
        files=client.get('/v2/datasets/'+dataset_id+'/files').json()['files']
        assert not any('AUDIT-' in f['name'] or 'ground_truth' in f['name'] for f in files)
        page.get_by_role('button',name='Durable jobs',exact=False).click()
        page.get_by_role('button',name='Refresh jobs',exact=True).click()
        expect(page.locator('#jobs')).to_contain_text('Practice run complete — not qualified')
        expect(page.locator('#jobs').get_by_role('button',name='View practice results').first).to_be_visible()
        page.get_by_role('button',name='Dataset explorer',exact=True).click()
        page.get_by_role('button',name='Refresh datasets',exact=True).click()
        page.get_by_label('Active dataset',exact=True).select_option(dataset_id)
        expect(page.locator('#dataset-summary')).to_contain_text('Synthetic press practice')
        page.get_by_label('Signals',exact=True).select_option('SIC-1500.PV')
        page.get_by_role('button',name='Query measurements',exact=True).click()
        expect(page.locator('#sample-count')).not_to_contain_text('No query')
        page.screenshot(path=str(report/'02-actual-line-evidence.png'),full_page=True)
        assert not errors,errors
        browser.close()
