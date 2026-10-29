import sqlite3
import threading
import pytest


def test_atomic_claim_and_idempotency(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore, JobConflict
    store=JobStore(tmp_path)
    first=store.create('generate',{'scenario':'tank-clean'},'same')
    assert store.create('generate',{'scenario':'tank-clean'},'same')['id']==first['id']
    with pytest.raises(JobConflict):store.create('generate',{'scenario':'cstr-clean'},'same')
    results=[]
    threads=[threading.Thread(target=lambda:results.append(store.claim('worker'))) for _ in range(4)]
    for t in threads:t.start()
    for t in threads:t.join()
    assert sum(r is not None for r in results)==1


def test_cancel_and_terminal_results_are_durable(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore,JobConflict
    s=JobStore(tmp_path);job=s.create('generate',{})
    assert s.request_cancel(job['id'])['state']=='cancelled'
    assert JobStore(tmp_path).get(job['id'])['state']=='cancelled'
    with pytest.raises(JobConflict):s.finish(job['id'],{'dataset':True})
    running=s.create('validate',{});s.claim('worker')
    assert s.request_cancel(running['id'])['state']=='cancel_requested'
    s.cancelled(running['id'])
    assert s.get(running['id'])['result'] is None


def test_interrupted_job_never_registers_partial_dataset(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore
    s=JobStore(tmp_path);j=s.create('generate',{});s.claim('dead-worker')
    with sqlite3.connect(s.path) as db:db.execute("UPDATE jobs SET lease_until=0 WHERE id=?",(j['id'],))
    s.recover()
    assert s.get(j['id'])['state']=='interrupted'
    assert s.datasets()==[]
    assert s.get(j['id'])['error']['code']=='WORKER_INTERRUPTED'


def test_unknown_operation_and_nonfinite_parameters_fail_before_queue(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore
    s=JobStore(tmp_path)
    with pytest.raises(ValueError):s.create('shell',{'command':'anything'})
    with pytest.raises(ValueError):s.create('generate',{'days':float('nan')})
    assert s.list()==[]


def test_global_single_worker_budget_is_transactional(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore
    s=JobStore(tmp_path);s.create('generate',{});s.create('validate',{})
    assert s.claim('first') is not None
    assert JobStore(tmp_path).claim('second') is None


def test_submission_is_frozen_and_adjudication_is_separate(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore,JobConflict
    s=JobStore(tmp_path)
    frozen=s.freeze_submission('original','start_utc,end_utc,kind,root_cause,evidence_tags\n')
    assert frozen['sha256'] and frozen['frozen']
    with pytest.raises(JobConflict):s.freeze_submission('original','different')
    s.adjudicate('original',[{'row':2,'correct':True,'reason':'Independent evidence'}])
    with pytest.raises(JobConflict):s.adjudicate('original',[{'row':2,'correct':False,'reason':'Overwrite'}])
    assert JobStore(tmp_path).submission('original')['judgments'][0]['correct'] is True


def test_analysis_completion_and_freeze_are_atomic_with_cancellation(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore,JobConflict
    s=JobStore(tmp_path);job=s.create('blind_analysis',{});s.claim('worker');s.request_cancel(job['id'])
    with pytest.raises(JobConflict):s.finish(job['id'],{},submission=('dataset','header\n'))
    with pytest.raises(KeyError):s.submission('dataset')


def test_existing_frozen_claims_cannot_be_replaced_by_analysis_completion(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore,JobConflict
    s=JobStore(tmp_path);s.freeze_submission('dataset','old\n')
    job=s.create('blind_analysis',{});s.claim('worker')
    with pytest.raises(JobConflict):s.finish(job['id'],{},submission=('dataset','new\n'))
    assert s.get(job['id'])['state']=='running'
    assert s.submission('dataset')['csv']=='old\n'


def test_expired_live_worker_keeps_single_worker_capacity(tmp_path):
    import subprocess,sys
    from ekas_press_intelligence.native.jobs import JobStore
    process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
    try:
        store=JobStore(tmp_path);first=store.create('generate',{});store.claim('lost-manager')
        store.heartbeat(first['id'],pid=process.pid)
        store.create('generate',{'seed':2})
        with sqlite3.connect(store.path) as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(first['id'],))
        assert store.recover()==0
        assert store.get(first['id'])['state']=='running'
        assert store.claim('restarted-manager') is None
    finally:process.terminate();process.wait(timeout=5)


def test_failed_worker_reserves_capacity_until_owned_process_exits(tmp_path):
    import subprocess,sys
    from ekas_press_intelligence.native.jobs import JobStore,process_identity
    process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
    try:
        store=JobStore(tmp_path);first=store.create('generate',{});store.claim('manager')
        store.heartbeat(first['id'],pid=process.pid,process_start=process_identity(process.pid))
        store.fail(first['id'],'RESOURCE_LIMIT_EXCEEDED','Worker is still unwinding owned processes')
        store.create('generate',{'seed':2})
        assert store.claim('replacement-manager') is None
        process.terminate();process.wait(timeout=5)
        assert store.claim('replacement-manager') is not None
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=5)


def test_late_log_failure_preserves_terminal_result_and_is_visible(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore
    store=JobStore(tmp_path);job=store.create('describe_process',{});store.claim('worker')
    original={'text':'completed native artifact'};store.finish(job['id'],original)
    store.record_log_failure(job['id'],'Log metadata could not be persisted')
    current=store.get(job['id'])
    assert current['state']=='succeeded' and current['result']==original
    assert current['audit_failures'][0]['code']=='LOG_CAPTURE_FAILED'
    assert store.list()[0]['audit_failures']==current['audit_failures']
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE job_id=? AND operation='log_capture_failed'",(job['id'],)).fetchone()[0]==1
