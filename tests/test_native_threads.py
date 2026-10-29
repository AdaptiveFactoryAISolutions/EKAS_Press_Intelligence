"""Explicit native/evidence numerical thread capacity, without changing checks."""
import pytest


def test_worker_thread_defaults_override_ambient_library_pool_sizes():
    from ekas_press_intelligence.native.thread_limits import apply_thread_limit
    env={'OPENBLAS_NUM_THREADS':'64','OMP_NUM_THREADS':'32','MKL_NUM_THREADS':'16'}
    assert apply_thread_limit(env)==1
    assert all(env[name]=='1' for name in ('EKAS_NATIVE_BLAS_THREADS','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'))
    env['EKAS_NATIVE_BLAS_THREADS']='4'
    assert apply_thread_limit(env)==4
    assert all(env[name]=='4' for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'))


@pytest.mark.parametrize('value',['0','65','-1','1.5','true',True,''])
def test_invalid_thread_limits_fail_visibly(value):
    from ekas_press_intelligence.native.thread_limits import apply_thread_limit
    with pytest.raises(ValueError,match='THREAD_CONFIG_INVALID'):
        apply_thread_limit({'EKAS_NATIVE_BLAS_THREADS':value})


def test_evidence_namespace_sets_explicit_numerical_threads(tmp_path,monkeypatch):
    import pandas as pd
    from ekas_press_intelligence.native.analysis import evidence_command
    from pathlib import Path
    challenge=tmp_path/'challenge';challenge.mkdir()
    for name in ('CHALLENGE.md','PROCESS_DESCRIPTION.md'):(challenge/name).write_text('Public process task')
    pd.DataFrame({'tag':['A']}).to_csv(challenge/'tags.csv',index=False)
    monkeypatch.setenv('EKAS_NATIVE_BLAS_THREADS','3')
    command=evidence_command(challenge,tmp_path/'audit.jsonl',Path(__file__).resolve().parents[1])
    settings={command[i+1]:command[i+2] for i in range(len(command)-2) if command[i]=='--setenv'}
    assert all(settings[name]=='3' for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'))
