"""Actual browser acceptance. No mocked API, diagnostic answers or truth injection."""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import httpx
import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.fixture(scope='module')
def web(tmp_path_factory):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env=dict(os.environ,EKAS_STATE_DIR=str(tmp_path_factory.mktemp('browser-state')))
    process=subprocess.Popen([sys.executable,'-m','uvicorn','ekas_press_intelligence.api:create_app',
        '--factory','--host','127.0.0.1','--port',str(port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if process.poll() is not None:raise RuntimeError(process.stderr.read().decode())
            try:
                if httpx.get(url+'/v1/health').status_code==200:break
            except httpx.ConnectError:pass
            time.sleep(.1)
        else:raise RuntimeError('Local API did not start')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=os.environ.get('EKAS_BROWSER_HEADLESS','1')!='0')
            yield browser,url
            browser.close()
    finally:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()


def test_complete_engineering_user_flow(web):
    browser,url=web
    page=browser.new_page(viewport={'width':1440,'height':1100})
    errors=[];failed=[];calls=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
    page.on('response',lambda response:failed.append((response.url,response.status)) if response.status>=400 else calls.append(response.url))
    page.goto(url)
    page.get_by_label('Instrumentation',exact=True).select_option('enhanced')
    page.get_by_role('button',name='Generate campaign',exact=True).click()
    expect(page.get_by_role('status')).to_contain_text('Campaign ready',timeout=60000)
    page.get_by_role('button',name='Investigate evidence',exact=False).click()
    expect(page.get_by_role('status')).to_contain_text('Investigation saved',timeout=60000)
    expect(page.locator('#primary-finding')).not_to_be_empty()
    page.get_by_role('button',name='Open evidence',exact=False).click()
    expect(page.get_by_role('dialog')).to_be_visible()
    expect(page.get_by_text('Evidence provenance',exact=True)).to_be_visible()
    page.get_by_role('button',name='Close evidence',exact=True).click()
    page.locator('#alternatives summary').first.click()
    expect(page.locator('#alternatives details').first).to_have_attribute('open','')
    page.get_by_role('button',name='Observability',exact=False).click()
    page.locator('#ambiguities summary').first.click()
    expect(page.locator('#ambiguities details').first).to_have_attribute('open','')
    page.get_by_role('button',name='Sensor gaps',exact=False).click()
    # Enhanced may have no useful single candidate; request sparse via explicit assessment
    # after checking the enhanced model's honest remaining limitation.
    expect(page.locator('#gaps')).not_to_be_empty()
    page.get_by_role('button',name='Blind benchmark',exact=False).click()
    expect(page.get_by_role('button',name='Reveal truth after scoring')).to_be_disabled()
    page.get_by_role('button',name='Freeze submission & score',exact=True).click()
    expect(page.locator('#truth-status')).to_contain_text('SCORED',timeout=30000)
    expect(page.get_by_role('button',name='Freeze submission & score',exact=True)).to_be_disabled()
    page.get_by_role('button',name='Reveal truth after scoring').click()
    expect(page.locator('#truth')).to_contain_text('Post-score synthetic truth')
    page.get_by_role('button',name='Action verification',exact=False).click()
    page.get_by_role('button',name='Apply synthetic corrective action').click()
    expect(page.get_by_role('status')).to_contain_text('Synthetic action recorded',timeout=60000)
    page.get_by_role('button',name='Compare before and after').click()
    expect(page.get_by_role('status')).to_contain_text('Verification saved',timeout=30000)
    expect(page.locator('#verification')).to_contain_text('Sustained result')
    page.get_by_role('button',name='Investigation',exact=False).click()
    expect(page.locator('#kpis')).to_contain_text('VERIFICATION')
    artifacts=Path('validation');artifacts.mkdir(exist_ok=True)
    page.screenshot(path=str(artifacts/'browser-desktop.png'),full_page=False)
    assert not errors,errors
    assert not failed,failed
    assert any('/v1/rca/investigate' in call for call in calls)
    assert any('/submit' in call for call in calls)
    assert any('/verify' in call for call in calls)
    (artifacts/'browser-flow.json').write_text(json.dumps({'flows':12,'console_errors':errors,'failed_requests':failed,'api_calls':calls},indent=2))
    page.close()


def test_accessibility_labels_landmarks_keyboard_and_layout(web):
    browser,url=web;page=browser.new_page(viewport={'width':1440,'height':1000});page.goto(url)
    assert page.locator('html').get_attribute('lang')=='en'
    assert page.get_by_role('main').count()==1
    assert page.get_by_role('heading',level=1).count()==1
    # Real accessible names are required for every editable field and button.
    for control in page.locator('input,select,textarea,button').all():
        name=control.evaluate("el=>el.labels?.length ? Array.from(el.labels).map(l=>l.textContent).join(' ') : (el.getAttribute('aria-label')||el.textContent)")
        assert name and name.strip()
    page.keyboard.press('Tab');expect(page.get_by_role('link',name='Skip to investigation')).to_be_focused()
    page.keyboard.press('Enter');expect(page.get_by_role('main')).to_be_focused()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    Path('validation/accessibility.json').write_text(json.dumps({'checks':['language','one main','one h1','editable names','button names','keyboard skip','desktop overflow'],'violations':[],'scope':'Structural and keyboard audit; not complete WCAG certification.'},indent=2))
    page.close()


def test_mobile_has_no_horizontal_overflow(web):
    browser,url=web;page=browser.new_page(viewport={'width':390,'height':844});page.goto(url)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    expect(page.get_by_role('button',name='Generate campaign',exact=True)).to_be_visible()
    page.screenshot(path='validation/browser-mobile.png',full_page=True)
    page.close()
