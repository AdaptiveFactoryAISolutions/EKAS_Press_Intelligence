"""Real HTTP/UI report acceptance on labeled public evidence fixtures; no route mocks."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import httpx
import pytest
import pandas as pd
from playwright.sync_api import sync_playwright,expect
from test_practice_report import evidence,api_run

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def report_page(api_run,tmp_path):
    _,store,ident=api_run
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    url=f'http://127.0.0.1:{port}'
    env=dict(os.environ,EKAS_NATIVE_STATE_DIR=str(store.directory),EKAS_NATIVE_TOKENS='{}')
    with (tmp_path/'service.log').open('w') as log:
        process=subprocess.Popen([sys.executable,'-m','uvicorn','ekas_press_intelligence.native.api:create_native_app','--factory','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(200):
                if process.poll() is not None:raise AssertionError((tmp_path/'service.log').read_text())
                try:
                    if httpx.get(url+'/v2/health').status_code==200:break
                except httpx.ConnectError:pass
                time.sleep(.1)
            else:raise AssertionError('Report service startup timed out')
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                page=browser.new_page(viewport={'width':1440,'height':1050});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(url);page.get_by_role('button',name='Durable jobs',exact=False).click()
                yield page,ident,store
                assert not errors,errors
                browser.close()
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()


def open_report(page,ident):
    page.locator('article.job').filter(has_text=ident).get_by_role('button',name='Read my results',exact=True).click()
    expect(page.get_by_role('heading',name='Your press simulation: results and next steps',exact=True)).to_be_visible()


def test_beginner_report_primary_action_charts_and_print(report_page):
    page,ident,_=report_page;open_report(page,ident)
    report=page.locator('#view-report')
    expect(report).to_contain_text('467 parts produced')
    expect(report).to_contain_text('459 parts packed')
    expect(report).to_contain_text('8 parts remained')
    expect(report).to_contain_text('Simulation practice only')
    expect(report).to_contain_text('Sensor-noise pattern')
    expect(report).to_contain_text('Full vocabulary and terminology review remains open')
    expect(report.get_by_role('img',name='Press speed',exact=False)).to_be_visible()
    ticks=report.get_by_role('img',name='Press speed',exact=False).locator('text').all_text_contents()
    assert all(str(v) in ticks for v in (15,30,45,60)),ticks
    expect(report.get_by_role('img',name='Washer temperature',exact=False)).to_be_visible()
    expect(report).to_contain_text('strokes per minute')
    expect(report.get_by_role('button',name='Print or save as PDF',exact=True)).to_be_visible()
    page.emulate_media(media='print')
    expect(page.locator('.topbar')).to_be_hidden()
    expect(report).to_be_visible();page.emulate_media(media='screen')
    target=ROOT/'work/practice-report-browser';target.mkdir(exist_ok=True)
    page.screenshot(path=str(target/'report.png'),full_page=True)
    report.get_by_role('button',name='Back to runs',exact=True).click()
    expect(page.get_by_role('heading',name='Durable jobs',exact=True)).to_be_visible()


def test_missing_final_reading_explains_uncertainty(report_page):
    page,ident,store=report_page
    data=Path(store.dataset(ident)['public_path'])/'historian_10s.parquet';frame=pd.read_parquet(data)
    frame.loc[frame.index[frame.tag=='COUNT-PACKED'][-1],'quality']=2;frame.to_parquet(data)
    open_report(page,ident)
    expect(page.locator('#view-report')).to_contain_text('The final part balance is not available')
    expect(page.locator('#view-report')).to_contain_text('Last reading is not available')
