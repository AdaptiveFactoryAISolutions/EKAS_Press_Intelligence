"""Wizard contract tests use a fake transport; real native E2E is separate."""
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect

UI = Path(__file__).parents[1] / 'src/ekas_press_intelligence/native_ui'

@pytest.fixture
def wizard():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.set_content('<section id="view-setup"></section>')
        page.evaluate('''() => {window.calls=[];crypto.randomUUID??=()=> 'test-run-key';window.EKASSetup={role:()=> 'admin',view:()=>{},notice:()=>{},loadJobs:async()=>{},api:async(path,options={})=>{calls.push([path,options]);if(path.endsWith('preset'))return {preset_id:'test',preset_version:1,runtime_ready:true,config:{speed:8},fields:[{name:'speed',label:'Press speed',unit:'SPM',help:'Maximum ten strokes per minute.',tooltip:'600 is strokes per hour.',step:2,type:'number',minimum:1,maximum:10}],steps:Array.from({length:8},(_,i)=>({number:i+1,title:'Step '+(i+1),description:'Configure line'}))};if(path.endsWith('/drafts')&&!options.method)return {drafts:[]};if(path.endsWith('check-step')){if(JSON.parse(options.body).config.speed>10)throw Object.assign(new Error('Correct press speed'),{errors:[{location:['config','speed'],message:'Value error, speed: Must be at most 10'}]});return {passed:true};}if(path.endsWith('preflight'))return {passed:true,runtime_ready:true,config:{speed:8},config_sha256:'abc',summary:{practice:true}};return {id:'draft1',revision:1,state:'queued'};}}}''')
        page.add_script_tag(path=str(UI/'setup.js'))
        page.evaluate('window.LineWizard.open()')
        yield page
        browser.close()

def test_eight_steps_no_json_and_invalid_speed(wizard):
    page=wizard
    expect(page.get_by_role('heading',name='Step 1',exact=True)).to_be_visible()
    page.get_by_role('button',name='Next',exact=True).click()
    page.get_by_label('Press speed (SPM)',exact=True).fill('600')
    page.get_by_role('button',name='Next',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('Press speed (SPM): Must be at most 10')
    expect(page.get_by_role('alert')).not_to_contain_text('config /')
    expect(page.get_by_role('alert')).not_to_contain_text('Value error,')
    expect(page.get_by_label('Press speed (SPM)',exact=True)).to_be_focused()
    assert page.locator('textarea').count()==0

def test_help_escape_and_full_default_run(wizard):
    page=wizard
    page.get_by_role('button',name='Next',exact=True).click()
    help=page.get_by_role('button',name='Help for Press speed')
    help.click()
    expect(page.get_by_role('tooltip')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.get_by_role('tooltip')).to_be_hidden()
    for _ in range(6):page.get_by_role('button',name='Next',exact=True).click()
    expect(page.get_by_role('button',name='Run practice')).to_be_disabled()
    page.get_by_role('button',name='Check setup').click()
    expect(page.get_by_role('button',name='Run practice')).to_be_enabled()
    page.get_by_role('button',name='Run practice').evaluate('(button)=>{button.click();button.click();}')
    page.wait_for_function("calls.some(c=>c[0].endsWith('/run'))")
    assert len(page.evaluate("calls.filter(c=>c[0].endsWith('/run'))"))==1

def test_back_save_and_resume_after_reset(wizard):
    page=wizard
    page.evaluate('''() => {const original=EKASSetup.api;EKASSetup.api=async(path,options={})=>{if(path==='/line/drafts'&&options.method==='POST'){window.saved={...JSON.parse(options.body),id:'one',revision:1};return saved;}if(path==='/line/drafts'&&!options.method)return {drafts:window.saved?[saved]:[]};if(path==='/line/drafts/one')return saved;return original(path,options);}}''')
    page.get_by_role('button',name='Next',exact=True).click()
    page.get_by_label('Press speed (SPM)',exact=True).fill('9')
    page.get_by_role('button',name='Back',exact=True).click()
    page.get_by_role('button',name='Save setup',exact=True).click()
    expect(page.locator('#setup-save-state')).to_contain_text('Saved on server')
    page.evaluate('LineWizard.reset();LineWizard.open()')
    page.get_by_role('button',name='Resume 1,500-ton practice line · step 1').click()
    page.get_by_role('button',name='Next',exact=True).click()
    expect(page.get_by_label('Press speed (SPM)',exact=True)).to_have_value('9')

def test_preflight_is_invalidated_by_edit_and_analyst_has_no_controls(wizard):
    page=wizard
    for _ in range(7):page.get_by_role('button',name='Next',exact=True).click()
    page.get_by_role('button',name='Check setup').click()
    expect(page.get_by_role('button',name='Run practice')).to_be_enabled()
    page.get_by_role('button',name='Go to step 2',exact=True).click()
    page.get_by_label('Press speed (SPM)',exact=True).fill('9')
    page.get_by_role('button',name='Go to step 8',exact=True).click()
    expect(page.get_by_role('button',name='Run practice')).to_be_disabled()
    page.evaluate("EKASSetup.role=()=> 'analyst';LineWizard.reset();LineWizard.open()")
    expect(page.locator('#view-setup')).to_contain_text('Admin access is required')
    assert page.locator('#view-setup input').count()==0

def test_stale_save_error_is_actionable(wizard):
    page=wizard
    page.evaluate('''() => {const original=EKASSetup.api;EKASSetup.api=async(path,options={})=>{if(options.method==='PUT')throw Object.assign(new Error('stale'),{status:409});return original(path,options);}}''')
    page.get_by_role('button',name='Save setup',exact=True).click()
    page.get_by_role('button',name='Save setup',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('changed in another tab')

def test_force_unit_switch_converts_values(wizard):
    page=wizard
    page.evaluate('''async()=>{const original=EKASSetup.api;EKASSetup.api=async(path,options)=>{const r=await original(path,options);if(path.endsWith('preset')){r.config={speed:8,capacity_tons:1500,forming_force_tons:1000,force_unit:'metric_tonne_force'};r.fields.push({name:'capacity_tons',label:'Rated capacity',unit:'tons-force',step:2,type:'number',readOnly:true},{name:'forming_force_tons',label:'Forming load',unit:'tons-force',step:2,type:'number'},{name:'force_unit',label:'Force unit',step:2,type:'select',choices:[{value:'metric_tonne_force',label:'Metric'},{value:'short_ton_force',label:'US short tons'}]});}return r;};LineWizard.reset();await LineWizard.open();}''')
    page.get_by_role('button',name='Next',exact=True).click()
    page.get_by_label('Force unit',exact=True).select_option('short_ton_force')
    capacity=float(page.get_by_label('Rated capacity (tons-force)',exact=True).input_value())
    load=float(page.get_by_label('Forming load (tons-force)',exact=True).input_value())
    assert capacity==pytest.approx(1500*9806.65/8896.443230521)
    assert load==pytest.approx(1000*9806.65/8896.443230521)
    expect(page.get_by_label('Rated capacity (tons-force)',exact=True)).not_to_be_editable()
    assert len(page.get_by_label('Rated capacity (tons-force)',exact=True).input_value().split('.')[-1])<=3
    assert 'Allowed:' not in page.get_by_label('Rated capacity (tons-force)',exact=True).locator('..').inner_text()
    page.get_by_role('button',name='Save setup',exact=True).click()
    exact=page.evaluate("JSON.parse(calls.filter(c=>c[0]==='/line/drafts'&&c[1].method==='POST').at(-1)[1].body).config.capacity_tons")
    assert exact==pytest.approx(1500*9806.65/8896.443230521,rel=1e-12)

def test_save_and_exit_persists_before_navigation(wizard):
    page=wizard
    page.evaluate("window.destinations=[];EKASSetup.view=name=>destinations.push(name)")
    page.get_by_role('button',name='Save and exit',exact=True).click()
    page.wait_for_function("destinations.includes('explore')")
    assert page.evaluate("calls.some(c=>c[0]==='/line/drafts'&&c[1].method==='POST')")

def test_unsaved_navigation_is_not_silent(wizard):
    page=wizard
    page.get_by_role('button',name='Next',exact=True).click()
    page.get_by_label('Press speed (SPM)',exact=True).fill('9')
    assert page.evaluate("LineWizard.beforeLeave('explore')") is False
    expect(page.get_by_role('alert')).to_contain_text('Save and exit')
    assert page.evaluate("(()=>{const event=new Event('beforeunload',{cancelable:true});window.dispatchEvent(event);return event.defaultPrevented;})()")

def test_summary_uses_friendly_choices_and_optional_digests(wizard):
    page=wizard
    page.evaluate('''async()=>{const original=EKASSetup.api;EKASSetup.api=async(path,options)=>{const r=await original(path,options);if(path.endsWith('preset')){r.config.force_unit='metric_tonne_force';r.fields.push({name:'force_unit',label:'Force unit',step:2,type:'select',choices:[{value:'metric_tonne_force',label:'Metric tonnes-force'}]});}return r;};LineWizard.reset();await LineWizard.open();}''')
    for _ in range(7):page.get_by_role('button',name='Next',exact=True).click()
    expect(page.locator('.setup-summary')).to_contain_text('Metric tonnes-force')
    expect(page.locator('.setup-summary')).not_to_contain_text('metric_tonne_force')
    page.get_by_role('button',name='Check setup').click()
    expect(page.locator('#setup-check-status')).to_have_text('Setup checked. Review the settings and runtime status before running.')
    expect(page.locator('#setup-binding-metadata')).not_to_be_visible()
    page.get_by_text('Exact configuration and source binding',exact=True).click()
    expect(page.locator('#setup-binding-metadata')).to_contain_text('abc')

def test_lost_run_response_retries_exact_binding_without_resave(wizard):
    page=wizard
    page.evaluate('''()=>{const original=EKASSetup.api;window.runAttempts=[];window.createdJobs=new Map();EKASSetup.api=async(path,options={})=>{if(path.endsWith('/run')){calls.push([path,options]);const binding=JSON.parse(options.body);runAttempts.push(binding);const key=path+JSON.stringify(binding);createdJobs.set(key,{id:'committed-job',state:'queued'});if(runAttempts.length===1)throw Object.assign(new Error('Response lost after commit'),{code:'CONNECTION_FAILED'});return createdJobs.get(key);}return original(path,options);}}''')
    for _ in range(7):page.get_by_role('button',name='Next',exact=True).click()
    page.get_by_role('button',name='Check setup',exact=True).click()
    page.get_by_role('button',name='Run practice',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('Response lost')
    expect(page.get_by_role('button',name='Check setup',exact=True)).to_be_disabled()
    expect(page.get_by_role('button',name='Back',exact=True)).to_be_disabled()
    page.get_by_role('button',name='Save and exit',exact=True).click()
    page.get_by_role('button',name='Retry same run',exact=True).click()
    assert page.evaluate('runAttempts[0].revision===runAttempts[1].revision&&runAttempts[0].idempotency_key===runAttempts[1].idempotency_key')
    assert page.evaluate('createdJobs.size')==1
    assert page.evaluate('runAttempts[0].idempotency_key')=='line-draft1-1'
    assert page.evaluate("calls.filter(c=>c[0].includes('/drafts')&&['POST','PUT'].includes(c[1].method)&&!c[0].endsWith('/run')).length")==1

def test_resume_recovers_server_last_run_without_new_save(wizard):
    page=wizard
    page.evaluate('''()=>{const original=EKASSetup.api;const draft={id:'saved',name:'Already submitted',revision:4,step:8,config:{speed:8},last_run:{job_id:'existing',revision:4,idempotency_key:'line-saved-4',state:'queued'}};EKASSetup.api=async(path,options={})=>{if(path==='/line/drafts'&&!options.method)return {drafts:[draft]};if(path==='/line/drafts/saved'&&!options.method)return draft;return original(path,options);}}''')
    page.get_by_role('button',name='Refresh saved setups',exact=True).click()
    page.get_by_role('button',name='Resume Already submitted · step 8',exact=True).click()
    expect(page.get_by_role('button',name='View existing practice run',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Check setup',exact=True)).to_be_disabled()
    page.get_by_role('button',name='Retry same run',exact=True).click()
    attempts=page.evaluate("calls.filter(c=>c[0].endsWith('/run')).map(c=>JSON.parse(c[1].body))")
    assert attempts==[{'revision':4,'idempotency_key':'line-saved-4'}]
    assert page.evaluate("calls.filter(c=>['POST','PUT'].includes(c[1].method)&&!c[0].endsWith('/run')).length")==0

def test_setup_name_validation_and_wiki_link(wizard):
    page=wizard
    name=page.get_by_label('Setup name',exact=True)
    expect(name).to_have_attribute('maxlength','80')
    name.fill('   ')
    page.get_by_role('button',name='Next',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('Enter a setup name')
    expect(name).to_be_focused()
    expect(name).to_have_attribute('aria-invalid','true')
    link=page.get_by_role('link',name='Step-by-step wiki',exact=True)
    expect(link).to_have_attribute('href','https://github.com/AdaptiveFactoryAISolutions/EKAS_Press_Intelligence/blob/full-stack-foundation/docs/wiki/Home.md')
    expect(link).to_have_attribute('target','_blank')
    expect(link).to_have_attribute('rel','noopener noreferrer')

def test_server_name_error_returns_to_step_one(wizard):
    page=wizard
    page.get_by_role('button',name='Next',exact=True).click()
    page.evaluate('''()=>{const original=EKASSetup.api;EKASSetup.api=async(path,options={})=>{if(options.method==='POST'&&path==='/line/drafts')throw Object.assign(new Error('Invalid setup name'),{errors:[{location:['body','name'],message:'String should have at most 80 characters'}]});return original(path,options);}}''')
    page.get_by_role('button',name='Save setup',exact=True).click()
    expect(page.get_by_role('heading',name='Step 1',exact=True)).to_be_visible()
    expect(page.get_by_label('Setup name',exact=True)).to_be_focused()
    expect(page.get_by_role('alert')).to_contain_text('Setup name: String should have at most 80 characters')
