"""Prepared compatibility tests and patches must execute inside their own tree."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import pytest
ROOT=Path(__file__).resolve().parents[1]


def preparer():
    spec=importlib.util.spec_from_file_location('native_preparer',ROOT/'scripts/prepare_native_runtime.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_extended_header_patch_applies_in_nested_workspace():
    module=preparer()
    with tempfile.TemporaryDirectory(dir=ROOT/'work',prefix='test-native-patch-') as temporary:
        target=Path(temporary)
        for name in ('src/historiansim/plants/base.py','src/historiansim/faults/scheduler.py'):
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((ROOT/'vendor/HistorianSim'/name).read_bytes())
        result=module.apply_runtime_patch(target,ROOT/'patches/0009-native-config-aware-benign-events.patch')
        assert len(result)==2
        assert 'build_for_config' in (target/'src/historiansim/plants/base.py').read_text()
        assert 'event.build_for_config(bid, onset, onset + duration, cfg)' in (target/'src/historiansim/faults/scheduler.py').read_text()
        with pytest.raises((ValueError,subprocess.CalledProcessError)):
            module.apply_runtime_patch(target,ROOT/'patches/0009-native-config-aware-benign-events.patch')


def test_pfd_layout_compatibility_patch_changes_only_two_tests(tmp_path):
    module=preparer();original=ROOT/'vendor/HistorianSim/tests/test_pipeline.py'
    target=tmp_path/'tests/test_pipeline.py';target.parent.mkdir();target.write_bytes(original.read_bytes())
    result=module.apply_runtime_patch(tmp_path,ROOT/'patches/0010-native-optional-pfd-layout-tests.patch')
    assert set(result)=={'tests/test_pipeline.py'}
    import ast
    def functions(text):
        return {node.name:ast.dump(node) for node in ast.parse(text).body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
    before=functions(original.read_text());after=functions(target.read_text())
    changed={name for name in before if before[name]!=after[name]}
    assert changed=={'test_write_dataset_emits_the_documented_layout','test_make_challenge_leaves_the_answers_behind'}
    text=target.read_text()
    assert 'assert all(c.passed for c in audit_dataset_dir(out))' in text
    assert 'assert "FAULT_ANSWER_KEY" not in' in text
    assert '(challenge / name).read_bytes() == (source_pfd / name).read_bytes()' in text


def test_prepared_runtime_binds_patched_test_sources():
    module=preparer()
    with tempfile.TemporaryDirectory(dir=ROOT/'work',prefix='test-native-test-provenance-') as temporary:
        runtime=module.prepare_runtime(ROOT,Path(temporary))
        import json
        manifest=json.loads((runtime/'NATIVE_RUNTIME_PROVENANCE.json').read_text())
        assert manifest['test_suite_kind']=='native_patched_upstream_compatibility'
        assert manifest['source_tests_sha256']['test_pipeline.py']!=manifest['runtime_tests_sha256']['test_pipeline.py']
        assert set(manifest['source_tests_sha256'])==set(manifest['runtime_tests_sha256'])
        assert {name for name in manifest['source_tests_sha256'] if manifest['source_tests_sha256'][name]!=manifest['runtime_tests_sha256'][name]}=={'test_pipeline.py'}
        assert 'build_for_config' in (runtime/'src/historiansim/plants/base.py').read_text()
        test=runtime/'tests/test_pipeline.py';original=test.read_bytes();test.write_bytes(original+b'\n# unexpected mutation\n')
        with pytest.raises(ValueError,match='runtime test source file hashes mismatch'):module.verify_runtime(ROOT,runtime)
        test.write_bytes(original)
        assert module.verify_runtime(ROOT,runtime)==manifest
        configuration=runtime/'pyproject.toml';configuration.write_text(configuration.read_text()+'\n# unexpected config mutation\n')
        with pytest.raises(ValueError,match='runtime test configuration hashes mismatch'):module.verify_runtime(ROOT,runtime)


def test_patch_target_cannot_contain_git_metadata(tmp_path):
    (tmp_path/'.git').mkdir()
    with pytest.raises(ValueError,match='Git metadata'):
        preparer().apply_runtime_patch(tmp_path,ROOT/'patches/0009-native-config-aware-benign-events.patch')
