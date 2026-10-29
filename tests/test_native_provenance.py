import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def test_unknown_runtime_is_rejected_before_app_import(tmp_path):
    env=dict(os.environ,EKAS_NATIVE_RUNTIME=str(tmp_path))
    result=subprocess.run([sys.executable,'-c','from ekas_press_intelligence.native.api import create_native_app'],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode!=0
    assert 'runtime' in result.stderr.lower()


def test_native_server_uses_protected_checkout_and_client_stays_independent():
    from ekas_press_intelligence.native.bootstrap import activate
    from ekas_press_intelligence.native.client import EKASNativeClient
    result=activate()
    assert result['kind']=='immutable_upstream'
    assert Path(result['source']).resolve()==ROOT/'vendor/HistorianSim/src'


def _default_guard_module():
    import importlib.util
    spec=importlib.util.spec_from_file_location('default_source_guard',ROOT/'scripts/prepare_reference_runtime.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_default_source_guard_denies_ignored_legacy_bytecode_before_lazy_import(tmp_path):
    import py_compile
    import shutil
    import pytest
    source=tmp_path/'src';source.mkdir()
    shutil.copytree(ROOT/'vendor/HistorianSim/src/historiansim',source/'historiansim',ignore=shutil.ignore_patterns('__pycache__'))
    payload=tmp_path/'payload.py';payload.write_text('raise RuntimeError("UNVERIFIED_DEFAULT_BYTECODE_EXECUTED")\n')
    for destination in (source/'matplotlib.pyc',source/'historiansim/plants/review_unknown/__init__.pyc'):
        destination.parent.mkdir(parents=True,exist_ok=True)
        py_compile.compile(str(payload),cfile=str(destination),doraise=True)
        with pytest.raises(ValueError,match='unsupported sibling|source file hashes mismatch'):
            _default_guard_module().verify_default_source(ROOT,source)
        code="import importlib.util,sys;from pathlib import Path;spec=importlib.util.spec_from_file_location('guard',sys.argv[1]);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.verify_default_source(Path(sys.argv[2]),Path(sys.argv[3]));sys.pycache_prefix=sys.argv[4];sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv[3]);"
        code+=('from historiansim.plotting import plot_dataset;plot_dataset(\"/nonexistent-review-data\")' if destination.name=='matplotlib.pyc' else 'from historiansim.plants import available_plants;available_plants()')
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'scripts/prepare_reference_runtime.py'),str(ROOT),str(source),str(tmp_path/'fresh-cache')],cwd=ROOT,capture_output=True,text=True,timeout=30)
        assert result.returncode!=0 and ('unsupported sibling' in result.stderr or 'source file hashes mismatch' in result.stderr)
        assert 'UNVERIFIED_DEFAULT_BYTECODE_EXECUTED' not in result.stderr
        destination.unlink()


def test_default_source_guard_preserves_editable_metadata_and_private_cache_policy(tmp_path):
    import shutil
    import pytest
    source=tmp_path/'src';source.mkdir()
    shutil.copytree(ROOT/'vendor/HistorianSim/src/historiansim',source/'historiansim',ignore=shutil.ignore_patterns('__pycache__'))
    metadata=source/'historiansim.egg-info';metadata.mkdir()
    for name in ('PKG-INFO','SOURCES.txt','dependency_links.txt','entry_points.txt','requires.txt','top_level.txt'):
        (metadata/name).write_text('Legitimate editable metadata fixture.')
    licenses=metadata/'licenses';licenses.mkdir();(licenses/'LICENSE').write_text('Legitimate license metadata.')
    cache=source/'historiansim/__pycache__';cache.mkdir()
    (cache/'ignored.cpython-312.pyc').write_bytes(b'ignored by private cache prefix')
    guard=_default_guard_module()
    guard.verify_default_source(ROOT,source)
    unexpected=metadata/'unexpected.pyc';unexpected.write_bytes(b'not editable metadata')
    with pytest.raises(ValueError,match='editable metadata'):guard.verify_default_source(ROOT,source)
    unexpected.unlink()
    link=cache/'linked.pyc';link.symlink_to(metadata/'PKG-INFO')
    with pytest.raises(ValueError,match='symlink'):guard.verify_default_source(ROOT,source)
    link.unlink()
    changed=source/'historiansim/__init__.py';changed.write_bytes(changed.read_bytes()+b'\n# unexpected change\n')
    with pytest.raises(ValueError,match='source file hashes mismatch'):guard.verify_default_source(ROOT,source)
