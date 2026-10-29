import hashlib
import io
import json

def test_worker_log_is_bounded_but_drains_and_hashes_complete_stream(tmp_path):
    from ekas_press_intelligence.native.logs import capture_log
    content=b'x'*200_000
    target=tmp_path/'worker.log'
    capture_log(io.BytesIO(content),target,limit=1024)
    assert target.read_bytes()==content[:1024]
    metadata=json.loads((tmp_path/'worker.log.json').read_text())
    assert metadata=={'recorded_bytes':1024,'total_bytes':len(content),'truncated':True,'sha256_complete_stream':hashlib.sha256(content).hexdigest()}

def test_log_storage_failure_reports_once_and_drains_worker_pipe(tmp_path):
    from ekas_press_intelligence.native.logs import capture_log
    target=tmp_path/'unwritable';target.mkdir()
    stream=io.BytesIO(b'x'*200_000);errors=[]
    result=capture_log(stream,target,limit=1024,on_error=errors.append)
    assert stream.closed
    assert result['total_bytes']==200_000
    assert len(errors)==1 and errors[0]['code']=='LOG_CAPTURE_FAILED'
