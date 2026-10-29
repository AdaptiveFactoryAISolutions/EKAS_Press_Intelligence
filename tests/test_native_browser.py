"""Real same-origin native workspace acceptance; no browser route mocks.

Original benchmark/native job flows use actual source artifacts. The event UI
contract uses explicitly labeled Parquet fixtures and does not qualify physics.

Run with PLAYWRIGHT_BROWSERS_PATH=work/browsers work/venv/bin/python -m pytest
 tests/test_native_browser.py. Tests start an isolated real broker and use the
 complete original HistorianRCA registration. Browser diagnostics preserve both
 intentional HTTP failures and unexpected errors for inspection.
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

ARTIFACTS = Path('validation/native/browser')


EVENT_FIXTURE_ID = '36a3e170-589b-4f1c-84ed-61b64f1deff0'


@pytest.fixture(scope='module')
def native_state(tmp_path_factory):
    """Shape-valid acquisition fixture only: no simulation or qualification claim."""
    import pandas as pd
    from ekas_press_intelligence.native.data import dataset_info
    from ekas_press_intelligence.native.jobs import JobStore
    directory=tmp_path_factory.mktemp('native-browser')
    public=directory/'browser-contract-fixture'/'public'
    public.mkdir(parents=True)
    times=pd.to_datetime(['2024-01-01T00:00:00Z','2024-01-01T00:00:10Z'])
    pd.DataFrame({'timestamp':times,'tag':['COUNT-271','COUNT-271'],
                  'value':[1.,float('nan')],'quality':[0,2]}).to_parquet(public/'historian.parquet')
    pd.DataFrame({'timestamp':times,'COUNT-271':[1.,float('nan')],
                  'DI-271':[1.,float('nan')]}).to_parquet(public/'historian_60s.parquet')
    pd.DataFrame({'tag':['COUNT-271','DI-271'],'units':['pieces','-'],
                  'description':['Contract fixture counter; not native-qualified','Contract fixture status; not native-qualified']}).to_csv(public/'tags.csv',index=False)
    edges=pd.to_datetime(['2024-01-01T00:00:00.001Z','2024-01-01T00:00:00.002Z',
                          '2024-01-01T00:00:00.003Z','2024-01-01T00:00:00.004Z'])
    pd.DataFrame({'timestamp':edges,'event_code':[2,-1,1,-1],
                  'count':pd.array([1,None,1,None],dtype='Int64'),
                  'quality':[0,2,0,1]}).to_parquet(public/'cycle_event_journal.parquet')
    pd.DataFrame({'timestamp':times,'COUNT-271':[1.,float('nan')],
                  'DI-271':[1.,float('nan')]}).to_parquet(public/'cycle_events.parquet')
    record={'id':EVENT_FIXTURE_ID,'label':'Browser event contract fixture (not native-qualified)',
            'source':'browser_contract_fixture','status':'CONTRACT_FIXTURE_NOT_NATIVE_QUALIFIED',
            'scoring_status':'EXTERNAL_SCORING_REQUIRED','public_path':str(public),
            'private_path':None,'metadata':dataset_info(public)}
    # Test setup registration, never a fake successful generation/qualification job.
    store=JobStore(directory)
    with store.connect() as db:
        db.execute('INSERT INTO datasets VALUES(?,?)',(EVENT_FIXTURE_ID,json.dumps(record)))
    return directory


@pytest.fixture(scope='module')
def native_web(tmp_path_factory, native_state):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, EKAS_NATIVE_STATE_DIR=str(native_state),
               EKAS_NATIVE_TOKENS=json.dumps({'browser-admin': 'admin', 'browser-analyst': 'analyst'}))
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn',
        'ekas_press_intelligence.native.api:create_native_app', '--factory',
        '--host', '127.0.0.1', '--port', str(port)], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(150):
            if process.poll() is not None:
                raise RuntimeError(process.stderr.read().decode())
            try:
                if httpx.get(url+'/v2/health', headers={'Authorization':'Bearer browser-admin'}).status_code == 200:
                    break
            except httpx.ConnectError:
                pass
            time.sleep(.1)
        else:
            raise RuntimeError('Native API startup timeout')
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            yield browser, url
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def sign_in(page, url, token='browser-admin'):
    page.goto(url)
    page.get_by_role('button', name='Access', exact=True).click()
    page.get_by_label('Bearer token', exact=True).fill(token)
    page.get_by_role('button', name='Apply credential').click()
    expect(page.locator('#connection-status')).to_contain_text('admin' if token == 'browser-admin' else 'analyst')
    expect(page.locator('#dataset-select')).to_have_value('historianrca', timeout=30000)
    expect(page.locator('#tag-select option')).not_to_have_count(0, timeout=30000)


def observe(page):
    log = {'console_errors': [], 'page_errors': [], 'requests': [], 'responses': [], 'request_failures': []}
    page.on('console', lambda message: log['console_errors'].append(message.text) if message.type == 'error' else None)
    page.on('pageerror', lambda error: log['page_errors'].append(str(error)))
    page.on('request', lambda req: log['requests'].append({'method': req.method, 'url': req.url}))
    page.on('response', lambda response: log['responses'].append({'url': response.url, 'status': response.status}))
    page.on('requestfailed', lambda request: log['request_failures'].append({'url': request.url, 'failure': request.failure}))
    return log


def test_original_dataset_raw_grid_metadata_download_and_external_score(native_web):
    browser, url = native_web
    page = browser.new_page(viewport={'width': 1512, 'height': 1100})
    log = observe(page)
    sign_in(page, url)
    expect(page.locator('#dataset-summary')).to_contain_text('EXTERNAL_SCORING_REQUIRED')
    expect(page.locator('#tag-metadata .tag-item').first).to_be_visible()
    page.get_by_role('button', name='Query measurements', exact=True).click()
    expect(page.locator('#sample-count')).not_to_have_text('No query', timeout=30000)
    expect(page.locator('#query-disclosure')).to_contain_text('raw')
    expect(page.locator('#query-disclosure')).to_contain_text('quality')
    page.get_by_text('Returned measurements', exact=True).click()
    expect(page.locator('#sample-table table')).to_be_visible()
    expect(page.locator('#trend svg')).to_be_visible()
    page.screenshot(path=str(ARTIFACTS/'explorer-desktop.png'), full_page=True)
    page.get_by_label('Sample source', exact=True).select_option('grid')
    page.get_by_role('button', name='Query measurements', exact=True).click()
    expect(page.locator('#query-disclosure')).to_contain_text('Grid values may be interpolated')
    expect(page.locator('#query-disclosure')).to_contain_text('aggregation')
    with page.expect_download() as download:
        page.locator('#files a').filter(has_text='tags.csv').first.click()
    result = download.value
    result.save_as(str(ARTIFACTS/'download-tags.csv'))
    assert (ARTIFACTS/'download-tags.csv').stat().st_size > 0
    page.locator('#files .file-card').filter(has=page.get_by_role('link', name='PROCESS_DESCRIPTION.md', exact=True)).get_by_role('button', name='View artifact').click()
    expect(page.locator('#process-preview pre')).not_to_be_empty()
    page.locator('#files .file-card').filter(has=page.get_by_role('link', name='tk-101-hold-tank.png', exact=True)).get_by_role('button', name='View artifact').click()
    expect(page.locator('#process-preview img')).to_be_visible()
    page.wait_for_function("() => document.querySelector('#process-preview img')?.naturalWidth > 0")
    page.screenshot(path=str(ARTIFACTS/'process-pfd-desktop.png'), full_page=True)
    page.get_by_role('button', name='Evaluation', exact=True).click()
    expect(page.locator('#score-status')).to_contain_text('External scoring required')
    # Initial authentication and externally unavailable official score are intentional failures.
    assert not [e for e in log['console_errors'] if 'status of 401' not in e and 'status of 409' not in e and 'status of 404' not in e], log['console_errors']
    assert not log['page_errors'], log
    assert not log['request_failures'], log
    unexpected = [r for r in log['responses'] if r['status'] >= 400 and r['status'] not in (401, 409) and not (r['status']==404 and r['url'].endswith('/submission'))]
    assert not unexpected, unexpected
    (ARTIFACTS/'explorer-network.json').write_text(json.dumps(log, indent=2))
    page.close()


def test_native_jobs_failure_and_durable_reload(native_web):
    browser, url = native_web
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    sign_in(page, url)
    page.get_by_role('button', name='Native workflows', exact=True).click()
    page.get_by_label('Native parameters / overrides (JSON object)', exact=True).fill('{"config":{}}')
    preview = json.loads(page.locator('#request-preview').inner_text())
    assert 'scenario' not in preview['parameters'], preview
    assert 'profile' not in preview['parameters'], preview
    assert 'seed' not in preview['parameters'], preview
    page.get_by_label('Native parameters / overrides (JSON object)', exact=True).fill('{}')
    # Use actual native description rather than a shortened substitute for generation.
    page.get_by_label('Operation', exact=True).select_option('describe_process')
    page.get_by_role('button', name='Queue native job', exact=True).click()
    expect(page.locator('#jobs .job').first).to_be_visible(timeout=30000)
    expect(page.locator('#jobs .job').first.locator('.job-status')).to_have_text('succeeded', timeout=60000)
    job_id = page.locator('#jobs .job').first.locator('.job-id').inner_text()
    artifact = page.locator('#jobs .job').first
    expect(artifact.get_by_role('link', name='PROCESS_DESCRIPTION.md', exact=True)).to_be_visible(timeout=10000)
    artifact.get_by_role('button', name='View native artifact', exact=True).click()
    expect(artifact.locator('.job-artifact-preview pre')).not_to_be_empty()
    page.reload()
    page.get_by_role('button', name='Access', exact=True).click()
    page.get_by_label('Bearer token', exact=True).fill('browser-admin')
    page.get_by_role('button', name='Apply credential').click()
    page.get_by_role('button', name='Durable jobs', exact=False).click()
    expect(page.locator('#jobs')).to_contain_text(job_id)
    page.get_by_role('button', name='Native workflows', exact=True).click()
    page.get_by_label('Native parameters / overrides (JSON object)', exact=True).fill('{"unknown_native_option":true}')
    page.get_by_role('button', name='Queue native job', exact=True).click()
    # Validation may reject before enqueueing or record a typed worker failure.
    page.wait_for_function("() => !document.querySelector('#error').hidden || [...document.querySelectorAll('.job-status')].some(e=>e.textContent==='failed')", timeout=30000)
    assert ('unknown' in page.locator('#error').inner_text().lower() or page.locator('.job.failed').count())
    page.screenshot(path=str(ARTIFACTS/'jobs-desktop.png'), full_page=True)
    page.close()


def test_cancel_native_generation(native_web):
    browser, url = native_web
    page = browser.new_page()
    sign_in(page, url)
    page.get_by_role('button', name='Native workflows', exact=True).click()
    page.get_by_label('Operation', exact=True).select_option('generate')
    page.get_by_label('Profile', exact=True).select_option('quick')
    page.get_by_role('button', name='Queue native job', exact=True).click()
    active = page.locator('#jobs .job').first
    expect(active.get_by_role('button', name='Request cancellation', exact=True)).to_be_visible(timeout=10000)
    active.get_by_role('button', name='Request cancellation', exact=True).click()
    expect(active.locator('.job-status')).to_have_text('cancelled', timeout=30000)
    page.screenshot(path=str(ARTIFACTS/'cancelled-native-job.png'), full_page=True)
    page.close()


def test_analyst_evaluator_boundary_and_submission_validation(native_web):
    browser, url = native_web
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    sign_in(page, url, 'browser-analyst')
    page.get_by_role('button', name='Evaluation', exact=True).click()
    page.get_by_label('Judgments (JSON array)', exact=True).fill('[{"row":2,"correct":true,"reason":"Browser authorization negative test"}]')
    page.get_by_role('button', name='Record independent judgments', exact=True).click()
    expect(page.locator('#error')).to_be_visible()
    expect(page.locator('#error')).to_contain_text('FORBIDDEN')
    page.get_by_role('button', name='Investigation & submission', exact=True).click()
    page.get_by_label('Original submission CSV', exact=True).fill('cause_correct\ntrue\n')
    page.get_by_label('I have reviewed these claims', exact=False).check()
    page.get_by_role('button', name='Freeze submission', exact=True).click()
    expect(page.locator('#error')).to_be_visible()
    assert page.locator('#submission-result').inner_text() != 'true'
    csv = 'start_utc,end_utc,kind,root_cause,evidence_tags,notes\n2024-01-01T00:00:00Z,2024-01-01T01:00:00Z,fault,Unresolved item and mechanism,,Browser integration test; no diagnostic claim\n'
    page.get_by_label('Original submission CSV', exact=True).fill(csv)
    page.get_by_role('button', name='Freeze submission', exact=True).click()
    expect(page.locator('#notice')).to_contain_text('froze this submission', timeout=10000)
    frozen = page.locator('#submission-result').inner_text()
    page.get_by_role('button', name='Freeze submission', exact=True).click()
    expect(page.locator('#error')).to_be_visible()
    assert page.locator('#submission-result').inner_text() == frozen
    page.close()


def test_mobile_keyboard_dialog_and_accessible_controls(native_web):
    browser, url = native_web
    page = browser.new_page(viewport={'width': 390, 'height': 844})
    sign_in(page, url)
    assert page.locator('html').get_attribute('lang') == 'en'
    assert page.get_by_role('main').count() == 1
    assert page.get_by_role('heading', level=1).count() == 1
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_role('button', name='Access', exact=False).click()
    expect(page.get_by_role('dialog')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.get_by_role('dialog')).not_to_be_visible()
    for control in page.locator('input,select,textarea,button').all():
        name = control.evaluate("el => el.labels?.length ? [...el.labels].map(l=>l.textContent).join(' ') : (el.getAttribute('aria-label') || el.textContent)")
        assert name and name.strip()
    page.screenshot(path=str(ARTIFACTS/'explorer-mobile.png'), full_page=True)
    page.reload()
    page.keyboard.press('Tab')
    expect(page.get_by_role('link', name='Skip to workspace', exact=True)).to_be_focused()
    page.keyboard.press('Enter')
    expect(page.get_by_role('main')).to_be_focused()
    (ARTIFACTS/'accessibility.json').write_text(json.dumps({'checks':['language','one main','visible h1','control names','mobile overflow','dialog Escape','keyboard skip'],'scope':'Structural and keyboard checks, not complete WCAG certification.'},indent=2))
    page.close()


def test_native_full_range_plot_job_and_original_png(native_web):
    browser, url = native_web
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    log = observe(page)
    sign_in(page, url)
    page.get_by_role('button', name='Queue native full-range plot', exact=True).click()
    job = page.locator('#jobs .job').first
    expect(job.locator('.job-status')).to_have_text('succeeded', timeout=90000)
    expect(job.get_by_role('link', name='plot.png', exact=True)).to_be_visible(timeout=10000)
    job.get_by_role('button', name='View native artifact', exact=True).click()
    expect(job.locator('.job-artifact-preview img')).to_be_visible()
    page.wait_for_function("() => document.querySelector('.job-artifact-preview img')?.naturalWidth > 0")
    with page.expect_download() as download:
        job.get_by_role('link', name='plot.png', exact=True).click()
    download.value.save_as(str(ARTIFACTS/'download-native-plot.png'))
    assert (ARTIFACTS/'download-native-plot.png').stat().st_size > 1000
    page.screenshot(path=str(ARTIFACTS/'native-full-range-plot.png'), full_page=True)
    assert not log['page_errors'], log
    assert not log['request_failures'], log
    assert not [e for e in log['console_errors'] if 'status of 401' not in e], log['console_errors']
    assert not [r for r in log['responses'] if r['status'] >= 400 and r['status'] != 401], log
    (ARTIFACTS/'native-plot-network.json').write_text(json.dumps(log, indent=2))
    page.close()


def test_provider_workflow_forms_real_preflight_failure_and_evaluator_boundary(native_web):
    """Actual worker rejects invalid model before provider access; no provider success asserted."""
    browser, url = native_web
    page = browser.new_page(viewport={'width':1440,'height':1000})
    sign_in(page, url, 'browser-analyst')
    page.get_by_role('button', name='Investigation & submission', exact=True).click()
    expect(page.get_by_role('heading', name='Blind evidence analysis', exact=True)).to_be_visible()
    page.get_by_label('Analysis model', exact=True).fill('invalid model identifier!')
    page.get_by_label('Analysis timeout (seconds)', exact=True).fill('20')
    page.get_by_label('Analysis budget (USD)', exact=True).fill('0.1')
    page.get_by_role('button', name='Queue blind analysis', exact=True).click()
    expect(page.locator('#analysis-jobs')).to_contain_text('INVALID_PARAMETERS', timeout=30000)
    expect(page.locator('#analysis-jobs')).to_contain_text('invalid model identifier')
    expect(page.locator('#analysis-jobs')).not_to_contain_text('CLAIMS_FROZEN_REQUIRES_INDEPENDENT_EVALUATION')
    page.screenshot(path=str(ARTIFACTS/'analysis-preflight-failure.png'), full_page=True)
    page.get_by_role('button', name='Evaluation', exact=True).click()
    expect(page.get_by_role('button', name='Queue independent evaluation', exact=True)).to_be_disabled()
    page.get_by_role('button', name='Access', exact=False).click()
    page.get_by_label('Bearer token', exact=True).fill('browser-admin')
    page.get_by_role('button', name='Apply credential', exact=True).click()
    expect(page.get_by_role('button', name='Queue independent evaluation', exact=True)).to_be_enabled()
    page.get_by_role('button', name='Queue independent evaluation', exact=True).click()
    expect(page.locator('#error')).to_contain_text('EXTERNAL_SCORING_REQUIRED')
    page.screenshot(path=str(ARTIFACTS/'provider-unavailable-boundary.png'), full_page=True)
    page.close()



def test_event_acquisition_contract_and_actual_observability_export(native_web):
    """Parquet event contract fixture plus actual export of the original public dataset."""
    browser,url=native_web
    page=browser.new_page(viewport={'width':1512,'height':1100})
    log=observe(page)
    sign_in(page,url)
    expect(page.get_by_role('heading',name='Event journal & scan status',exact=True)).to_be_visible()
    page.get_by_label('Active dataset',exact=True).select_option(EVENT_FIXTURE_ID)
    expect(page.locator('#dataset-summary')).to_contain_text('CONTRACT_FIXTURE_NOT_NATIVE_QUALIFIED')
    page.get_by_label('Event source',exact=True).select_option('journal')
    page.get_by_label('Maximum event rows',exact=True).fill('2')
    page.get_by_role('button',name='Query event records',exact=True).click()
    expect(page.locator('#event-disclosure')).to_contain_text('1 ms')
    expect(page.locator('#event-disclosure')).to_contain_text('truncated: true')
    expect(page.locator('#event-table')).to_contain_text('null')
    expect(page.locator('#event-table')).to_contain_text('-1')
    expect(page.locator('#event-table tbody tr')).to_have_count(2)
    assert page.locator('#event-table tbody tr').nth(1).locator('td').nth(1).inner_text()=='-1'
    assert 'null' in page.locator('#event-table tbody tr').nth(1).locator('td').nth(2).inner_text()
    assert page.locator('#event-table tbody tr').nth(1).locator('td').nth(3).inner_text()=='2'
    page.get_by_label('Maximum event rows',exact=True).fill('10')
    page.get_by_role('button',name='Query event records',exact=True).click()
    expect(page.locator('#event-table tbody tr')).to_have_count(4)
    assert page.locator('#event-table tbody tr').nth(3).locator('td').nth(3).inner_text()=='1'
    page.screenshot(path=str(ARTIFACTS/'event-journal-contract-fixture.png'),full_page=True)
    page.get_by_label('Event start (UTC)',exact=True).fill('2024-01-01T00:00:00.002000001Z')
    page.get_by_label('Event end (UTC)',exact=True).fill('2024-01-01T00:00:00.004Z')
    page.get_by_role('button',name='Query event records',exact=True).click()
    expect(page.locator('#event-table tbody tr')).to_have_count(2)
    assert '00:00:00.003' in page.locator('#event-table tbody tr').first.locator('td').first.inner_text()
    page.get_by_label('Event start (UTC)',exact=True).fill('')
    page.get_by_label('Event end (UTC)',exact=True).fill('')
    page.get_by_label('Event source',exact=True).select_option('status')
    page.get_by_role('button',name='Query event records',exact=True).click()
    expect(page.locator('#event-disclosure')).to_contain_text('historian scan')
    expect(page.locator('#event-table')).to_contain_text('COUNT-271')
    expect(page.locator('#event-table')).to_contain_text('null')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_label('Active dataset',exact=True).select_option('historianrca')
    expect(page.locator('#dataset-summary')).to_contain_text('PUBLISHED_REFERENCE')
    page.get_by_label('Observability profile',exact=True).select_option('sparse')
    page.get_by_role('button',name='Queue observability export',exact=True).click()
    job=page.locator('#jobs .job').first
    expect(job.locator('.job-status')).to_have_text('succeeded',timeout=120000)
    expect(job.get_by_role('button',name='Open registered dataset',exact=True)).to_be_visible()
    job.get_by_role('button',name='Open registered dataset',exact=True).click()
    expect(page.locator('#availability-summary')).to_contain_text('sparse',timeout=30000)
    expect(page.locator('#availability-details')).to_contain_text('same_physical_run')
    expect(page.locator('#availability-details')).to_contain_text('resimulated')
    expect(page.locator('#dataset-summary')).to_contain_text('UNVALIDATED')
    expect(page.locator('#files')).to_contain_text('SOURCE_AVAILABILITY.json')
    page.screenshot(path=str(ARTIFACTS/'actual-sparse-observability-export.png'),full_page=True)
    page.get_by_label('Observability profile',exact=True).select_option('enhanced')
    page.get_by_role('button',name='Queue observability export',exact=True).click()
    failed=page.locator('#jobs .job').first
    expect(failed.locator('.job-status')).to_have_text('failed',timeout=30000)
    expect(failed).to_contain_text('OBSERVABILITY_CANNOT_RESTORE')
    assert not log['page_errors'],log
    assert not log['request_failures'],log
    assert not [e for e in log['console_errors'] if 'status of 401' not in e],log['console_errors']
    assert not [r for r in log['responses'] if r['status']>=400 and r['status']!=401],log
    (ARTIFACTS/'observability-events-network.json').write_text(json.dumps(log,indent=2))
    page.close()
