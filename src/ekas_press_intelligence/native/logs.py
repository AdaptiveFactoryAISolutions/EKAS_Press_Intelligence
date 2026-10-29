"""Bounded private worker logs with complete-stream byte count and digest."""
import hashlib
import json

def capture_log(stream,path,limit=16*1024*1024,on_error=None):
    digest=hashlib.sha256();total=0;recorded=0;output=None;error=None
    def failed(exc):
        nonlocal error
        if error is not None:return
        error={'code':'LOG_CAPTURE_FAILED','message':'Private worker log storage failed: '+type(exc).__name__}
        if on_error:
            try:on_error(error)
            except Exception:pass  # Always drain the pipe, even if reporting fails.
    try:
        try:output=path.open('wb');path.chmod(0o600)
        except OSError as exc:failed(exc)
        while True:
            block=stream.read(65536)
            if not block:break
            digest.update(block);total+=len(block)
            if output is not None and error is None:
                keep=block[:max(0,limit-recorded)]
                try:output.write(keep);output.flush();recorded+=len(keep)
                except OSError as exc:failed(exc)
    finally:
        stream.close()
        if output is not None:
            try:output.close()
            except OSError as exc:failed(exc)
    result={'recorded_bytes':recorded,'total_bytes':total,'truncated':total>recorded,'sha256_complete_stream':digest.hexdigest()}
    if error is not None:result['error']=error
    metadata=path.with_name(path.name+'.json')
    try:
        metadata.write_text(json.dumps(result,indent=2)+'\n');metadata.chmod(0o600)
    except OSError as exc:failed(exc);result['error']=error
    return result
