"""Actual HTTP/browser setup against a separately owned stock reference service.

No route mocks, paid providers, line-runtime launch or production activation.
A stock native runtime intentionally blocks stamping-line execution.
"""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import httpx
import pytest
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).parents[1]
ARTIFACTS=ROOT/'work/guided-line-browser'


def test_navigation_stays_visible_on_small_screen(line_reference_web):
    browser,url=line_reference_web
    page=browser.new_page(viewport={'width':1280,'height':800})
    page.goto(url+'/#setup')
    page.get_by_role('button',name='Access',exact=True).click()
    page.get_by_label('Bearer token',exact=True).fill('guided-browser-admin')
    page.get_by_role('button',name='Apply credential',exact=True).click()
    expect(page.locator('#connection-status')).to_contain_text('admin')
    page.get_by_role('button',name='Next',exact=True).click()
    expect(page.get_by_role('heading',name='Capacity and speed',exact=True)).to_be_visible()
    page.evaluate('window.scrollTo(0,0)')
    box=page.get_by_role('button',name='Next',exact=True).bounding_box()
    assert box and box['y']+box['height']<=800
    page.close()

@pytest.fixture(scope='module')
def line_reference_web(tmp_path_factory):
    ARTIFACTS.mkdir(parents=True,exist_ok=True)
    state=tmp_path_factory.mktemp('guided-line-browser-state')
    spec=importlib.util.spec_from_file_location('guided_reference',ROOT/'scripts/prepare_reference_runtime.py')
    preparer=importlib.util.module_from_spec(spec);spec.loader.exec_module(preparer)
    runtime=preparer.prepare_runtime(ROOT,ARTIFACTS/'reference-runtime')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env=dict(os.environ,EKAS_NATIVE_RUNTIME=str(runtime),EKAS_NATIVE_STATE_DIR=str(state),
             EKAS_NATIVE_TOKENS=json.dumps({'guided-browser-admin':'admin'}))
    log=(ARTIFACTS/'reference-service.log').open('w')
    process=subprocess.Popen([sys.executable,'-m','uvicorn','ekas_press_intelligence.native.api:create_native_app','--factory','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(200):
            if process.poll() is not None:raise RuntimeError((ARTIFACTS/'reference-service.log').read_text())
            try:
                if httpx.get(url+'/v2/health',headers={'Authorization':'Bearer guided-browser-admin'}).status_code==200:break
            except httpx.ConnectError:pass
            time.sleep(.1)
        else:raise RuntimeError('Guided reference service startup timed out')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            yield browser,url
            browser.close()
    finally:
        process.terminate()
        try:process.wait(timeout=8)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close()


def test_real_metadata_save_resume_validation_and_blocked_run(line_reference_web):
    browser,url=line_reference_web
    page=browser.new_page(viewport={'width':1440,'height':1100})
    unexpected=[]
    page.on('pageerror',lambda error:unexpected.append(str(error)))
    page.goto(url)
    page.get_by_role('button',name='Access',exact=True).click()
    page.get_by_label('Bearer token',exact=True).fill('guided-browser-admin')
    page.get_by_role('button',name='Apply credential',exact=True).click()
    expect(page.locator('#connection-status')).to_contain_text('admin')
    page.get_by_role('button',name='Guided press setup',exact=True).click()
    expect(page.get_by_role('heading',name='Choose your line',exact=True)).to_be_visible()
    page.screenshot(path=str(ARTIFACTS/'01-line-overview.png'),full_page=True)
    page.get_by_label('Setup name',exact=True).fill('Real server saved setup')
    page.get_by_role('button',name='Next',exact=True).click()
    speed=page.locator('#setup-speed_spm')
    expect(speed).to_have_value('8')
    speed.fill('600')
    page.get_by_role('button',name='Next',exact=True).click()
    expect(page.locator('#setup-errors')).to_contain_text('Operating speed')
    expect(speed).to_be_focused()
    page.screenshot(path=str(ARTIFACTS/'02-invalid-speed.png'),full_page=True)
    speed.fill('8')
    page.locator('#setup-force_unit').select_option('short_ton_force')
    assert float(page.locator('#setup-capacity_tons').input_value())==pytest.approx(1500*9806.65/8896.443230521)
    page.get_by_role('button',name='Save and exit',exact=True).click()
    expect(page.locator('#view-explore')).to_be_visible()
    expect(page.locator('[data-view="explore"]')).to_have_attribute('aria-current','page')
    page.reload()
    page.get_by_role('button',name='Access',exact=True).click()
    page.get_by_label('Bearer token',exact=True).fill('guided-browser-admin')
    page.get_by_role('button',name='Apply credential',exact=True).click()
    expect(page.locator('#connection-status')).to_contain_text('admin')
    page.get_by_role('button',name='Guided press setup',exact=True).click()
    page.get_by_role('button',name='Resume Real server saved setup · step 2',exact=True).click()
    expect(page.locator('#setup-force_unit')).to_have_value('short_ton_force')
    for _ in range(6):page.get_by_role('button',name='Next',exact=True).click()
    expect(page.get_by_role('heading',name='Review and run',exact=True)).to_be_visible()
    assert page.locator('#view-setup textarea').count()==0
    page.get_by_role('button',name='Check setup',exact=True).click()
    expect(page.locator('#setup-check-status')).to_contain_text('Setup checked')
    expect(page.locator('#view-setup')).to_contain_text('installer')
    expect(page.get_by_role('button',name='Run practice',exact=True)).to_be_disabled()
    page.screenshot(path=str(ARTIFACTS/'03-checked-runtime-unavailable.png'),full_page=True)
    assert not unexpected,unexpected
    page.close()

def test_setup_deeplink_opens_wizard_before_and_after_access(line_reference_web):
    browser,url=line_reference_web
    page=browser.new_page()
    page.goto(url+'/#setup')
    expect(page.locator('#view-setup')).to_be_visible()
    expect(page.locator('#view-setup')).to_contain_text('Admin access is required')
    page.get_by_role('button',name='Access',exact=True).click()
    page.get_by_label('Bearer token',exact=True).fill('guided-browser-admin')
    page.get_by_role('button',name='Apply credential',exact=True).click()
    expect(page.get_by_role('heading',name='Choose your line',exact=True)).to_be_visible()
    expect(page.locator('[data-view="setup"]')).to_have_attribute('aria-current','page')
    page.close()

def test_dataset_refresh_preserves_inflight_user_selection(line_reference_web):
    """UI ownership contract: controlled deferred transport, no physics claim."""
    browser,url=line_reference_web
    page=browser.new_page()
    page.goto(url)
    page.get_by_role('button',name='Access',exact=True).click()
    page.get_by_label('Bearer token',exact=True).fill('guided-browser-admin')
    page.get_by_role('button',name='Apply credential',exact=True).click()
    expect(page.locator('#connection-status')).to_contain_text('admin')
    page.evaluate('''async()=>{
      const original=api;const inventory=[{id:'reference-a',source:'original',status:'PUBLISHED_REFERENCE'},{id:'practice-b',source:'generated',status:'UNVALIDATED',line_setup:{practice:true}}];
      window.delayRegistry=false;window.delayPractice=false;window.selectionStarted=false;
      window.registryGate=new Promise(resolve=>window.releaseRegistry=resolve);
      window.practiceGate=new Promise(resolve=>window.releasePractice=resolve);
      api=async(path,options)=>{
        if(path==='/datasets'){if(window.delayRegistry)await registryGate;return {datasets:inventory};}
        const dataset=inventory.find(d=>path==='/datasets/'+d.id);
        if(dataset){if(dataset.id==='practice-b'&&window.delayPractice){window.selectionStarted=true;await practiceGate;}return dataset;}
        if(/^\\/datasets\\/(reference-a|practice-b)\\/tags$/.test(path))return {tags:[]};
        if(/^\\/datasets\\/(reference-a|practice-b)\\/files$/.test(path))return {files:[]};
        return original(path,options);
      };
      state.dataset=null;state.datasets=[];document.getElementById('dataset-select').replaceChildren();
      await loadDatasets();window.delayRegistry=true;window.delayPractice=true;window.registryRefresh=loadDatasets();
    }''')
    page.locator('#dataset-select').select_option('practice-b')
    page.wait_for_function('window.selectionStarted')
    page.evaluate('async()=>{releaseRegistry();await registryRefresh;}')
    expect(page.locator('#dataset-select')).to_have_value('practice-b')
    page.evaluate('releasePractice()')
    expect(page.locator('#dataset-summary')).to_contain_text('Synthetic press practice — not qualified for production')
    page.evaluate('''async()=>{
      const current=api;let requests=0;
      window.oldRegistryGate=new Promise(resolve=>window.releaseOldRegistry=resolve);
      api=async(path,options)=>{if(path==='/datasets'){requests++;if(requests===1){await oldRegistryGate;return {datasets:[{id:'reference-a'}]};}return {datasets:[{id:'practice-b',source:'generated',status:'UNVALIDATED',line_setup:{practice:true}}]};}return current(path,options);};
      window.oldRegistry=loadDatasets();await loadDatasets();releaseOldRegistry();await oldRegistry;
    }''')
    expect(page.locator('#dataset-select')).to_have_value('practice-b')
    assert page.locator('#dataset-select option[value="reference-a"]').count()==0
    page.close()

def test_refresh_recovers_rejected_selected_metadata(line_reference_web):
    """A controlled transient transport failure exercises the actual Refresh action."""
    browser,url=line_reference_web
    page=browser.new_page()
    page.goto(url)
    page.get_by_role('button',name='Access',exact=True).click()
    page.get_by_label('Bearer token',exact=True).fill('guided-browser-admin')
    page.get_by_role('button',name='Apply credential',exact=True).click()
    expect(page.locator('#connection-status')).to_contain_text('admin')
    expect(page.locator('#dataset-summary')).to_contain_text('PUBLISHED_REFERENCE')
    ident=page.locator('#dataset-select').input_value()
    page.evaluate('''id=>{const original=api;let reject=true;api=async(path,options)=>{if(path==='/datasets/'+encodeURIComponent(id)&&reject){reject=false;throw new Error('Temporary metadata failure');}return original(path,options);};}''',ident)
    page.locator('#dataset-select').select_option(ident)
    expect(page.locator('#error')).to_contain_text('Temporary metadata failure')
    expect(page.locator('#dataset-summary')).to_contain_text('Refresh datasets to retry')
    page.get_by_role('button',name='Refresh datasets',exact=True).click()
    expect(page.locator('#dataset-summary')).to_contain_text('PUBLISHED_REFERENCE')
    expect(page.locator('#notice')).to_contain_text('Dataset registry refreshed')
    assert page.evaluate('state.dataset?.id')==ident
    page.close()
