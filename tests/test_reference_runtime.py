import importlib.util
from pathlib import Path
import pytest
import os
import py_compile
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def module():
    spec=importlib.util.spec_from_file_location('reference_runtime',ROOT/'scripts/prepare_reference_runtime.py')
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

def test_reference_runtime_is_stock_and_tampering_fails():
    runtime=module();target=runtime.prepare_runtime(ROOT,ROOT/'work/reference-test-runtime')
    manifest=runtime.verify_runtime(ROOT,target)
    assert manifest['kind']=='native_reference'
    assert not (target/'src/historiansim/plants/stamping_press').exists()
    original=target/'src/historiansim/__init__.py'
    content=original.read_bytes()
    try:
        original.write_bytes(content+b'\n# altered\n')
        with pytest.raises(ValueError,match='hash'):runtime.verify_runtime(ROOT,target)
    finally:original.write_bytes(content)
    assert runtime.verify_runtime(ROOT,target)==manifest

def test_native_import_ignores_untrusted_cached_bytecode():
    runtime=module();target=runtime.prepare_runtime(ROOT,ROOT/'work/reference-cache-test-runtime')
    source=target/'src/historiansim/__init__.py'
    original=source.read_bytes();stat=source.stat()
    payload=b'raise RuntimeError("POISONED_CACHE")\n'
    source.write_bytes(payload+b' '*(len(original)-len(payload)))
    os.utime(source,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    py_compile.compile(str(source),doraise=True)
    source.write_bytes(original);os.utime(source,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    runtime.verify_runtime(ROOT,target)
    result=subprocess.run([sys.executable,'-c','from ekas_press_intelligence.native.bootstrap import activate; activate(); import historiansim; print(historiansim.__version__)'],cwd=ROOT,env=dict(os.environ,EKAS_NATIVE_RUNTIME=str(target)),capture_output=True,text=True)
    assert result.returncode==0,result.stderr[-2000:]
    assert result.stdout.strip()=='0.1.0'
