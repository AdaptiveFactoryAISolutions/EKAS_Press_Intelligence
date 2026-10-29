import pytest

def test_memory_guard_is_explicit_and_protects_host_reserve(tmp_path):
    from ekas_press_intelligence.native.resource_guard import memory_pressure
    (tmp_path/'self').mkdir()
    (tmp_path/'self/status').write_text('VmRSS:\t4096 kB\n')
    (tmp_path/'meminfo').write_text('MemAvailable: 8192 kB\n')
    assert memory_pressure({},tmp_path) is None
    assert memory_pressure({'EKAS_NATIVE_MAX_RSS_BYTES':str(5*1024*1024)},tmp_path) is None
    high=memory_pressure({'EKAS_NATIVE_MAX_RSS_BYTES':str(3*1024*1024)},tmp_path)
    assert high['code']=='RESOURCE_LIMIT_EXCEEDED'
    assert high['measurements']['rss_bytes']==4*1024*1024
    low=memory_pressure({'EKAS_NATIVE_MIN_AVAILABLE_BYTES':str(9*1024*1024)},tmp_path)
    assert low['code']=='RESOURCE_LIMIT_EXCEEDED'
    assert low['measurements']['available_bytes']==8*1024*1024

def test_configured_guard_fails_closed_if_telemetry_unavailable(tmp_path):
    from ekas_press_intelligence.native.resource_guard import memory_pressure
    assert memory_pressure({'EKAS_NATIVE_MAX_RSS_BYTES':'100'},tmp_path)['code']=='RESOURCE_MONITOR_UNAVAILABLE'
    with pytest.raises(ValueError,match='RESOURCE_CONFIG_INVALID'):
        memory_pressure({'EKAS_NATIVE_MAX_RSS_BYTES':'-1'},tmp_path)
