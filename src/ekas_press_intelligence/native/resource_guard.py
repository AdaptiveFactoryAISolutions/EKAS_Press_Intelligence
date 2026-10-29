"""Opt-in Linux worker RSS ceiling and host available-memory reserve."""
import os
from pathlib import Path

def memory_pressure(environ=None,proc_root=Path('/proc')):
    env=os.environ if environ is None else environ
    limits={}
    for name in ('EKAS_NATIVE_MAX_RSS_BYTES','EKAS_NATIVE_MIN_AVAILABLE_BYTES'):
        if name not in env:continue
        try:value=int(env[name])
        except (ValueError,TypeError):raise ValueError('RESOURCE_CONFIG_INVALID: memory limits must be positive byte counts') from None
        if value<=0:raise ValueError('RESOURCE_CONFIG_INVALID: memory limits must be positive byte counts')
        limits[name]=value
    if not limits:return None
    def kb(path,name):
        for line in path.read_text().splitlines():
            fields=line.split()
            if fields and fields[0]==name+':' and len(fields)==3 and fields[2]=='kB':return int(fields[1])*1024
        raise ValueError('memory telemetry missing')
    try:
        rss=kb(Path(proc_root)/'self/status','VmRSS')
        available=kb(Path(proc_root)/'meminfo','MemAvailable')
    except (OSError,ValueError):
        return {'code':'RESOURCE_MONITOR_UNAVAILABLE','message':'Configured memory protection cannot read Linux telemetry; native execution stopped'}
    measurements={'rss_bytes':rss,'available_bytes':available,**limits}
    if rss>limits.get('EKAS_NATIVE_MAX_RSS_BYTES',float('inf')) or available<limits.get('EKAS_NATIVE_MIN_AVAILABLE_BYTES',0):
        return {'code':'RESOURCE_LIMIT_EXCEEDED','message':'Configured worker memory ceiling or host memory reserve reached; partial output is unqualified','measurements':measurements}
    return None
