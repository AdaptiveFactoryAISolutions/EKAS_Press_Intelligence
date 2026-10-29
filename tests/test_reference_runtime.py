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


def test_reference_runtime_rejects_lazy_import_sibling_before_execution():
    import tempfile
    with tempfile.TemporaryDirectory(prefix='reference-sibling-boundary-',dir=ROOT/'work') as temporary:
        runtime=module();target=runtime.prepare_runtime(ROOT,Path(temporary)/'runtime')
        sibling=target/'src/matplotlib.py'
        sibling.write_text('raise RuntimeError("UNVERIFIED_REFERENCE_SIBLING_EXECUTED")\n')
        # A real lazy native import previously executed this file after verification.
        result=subprocess.run([sys.executable,'-B','-c',
            'from ekas_press_intelligence.native.bootstrap import activate;activate();from historiansim.plotting import plot_dataset;plot_dataset("/nonexistent-review-data")'],
            cwd=ROOT,env=dict(os.environ,EKAS_NATIVE_RUNTIME=str(target),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=30)
        assert result.returncode!=0
        assert 'unsupported sibling' in result.stderr
        assert 'UNVERIFIED_REFERENCE_SIBLING_EXECUTED' not in result.stderr
        with pytest.raises(ValueError,match='unsupported sibling'):runtime.verify_runtime(ROOT,target)


def test_reference_source_boundary_preserves_nonimport_data_and_ignored_package_cache():
    import tempfile
    with tempfile.TemporaryDirectory(prefix='reference-data-cache-boundary-',dir=ROOT/'work') as temporary:
        runtime=module();target=runtime.prepare_runtime(ROOT,Path(temporary)/'runtime')
        (target/'review-notes.txt').write_text('Nonimport runtime-root data is outside executable src.')
        cache=target/'src/historiansim/__pycache__';cache.mkdir(exist_ok=True)
        (cache/'unused.cpython-312.pyc').write_bytes(b'not executable through the private import cache prefix')
        assert runtime.verify_runtime(ROOT,target)['kind']=='native_reference'
        alias=Path(temporary)/'alias';alias.symlink_to(Path(temporary),target_is_directory=True)
        with pytest.raises(ValueError,match='symbolic link ancestors'):runtime.verify_runtime(ROOT,alias/'runtime')
        with pytest.raises(ValueError,match='symbolic link ancestors'):runtime.prepare_runtime(ROOT,alias/'new-runtime')
        sibling=target/'src/notes.txt';sibling.write_text('Even harmless src siblings are rejected consistently with hybrid runtime.')
        with pytest.raises(ValueError,match='unsupported sibling'):runtime.verify_runtime(ROOT,target)
