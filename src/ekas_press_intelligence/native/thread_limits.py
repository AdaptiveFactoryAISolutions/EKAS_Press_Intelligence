"""Explicit per-worker numerical thread capacity; no numerical substitutions."""
import os
import re

THREAD_VARIABLES=('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')


def blas_thread_count(environ=None):
    env=os.environ if environ is None else environ
    value=env.get('EKAS_NATIVE_BLAS_THREADS','1')
    if not isinstance(value,str) or not re.fullmatch(r'[1-9][0-9]*',value) or len(value)>2 or int(value)>64:
        raise ValueError('THREAD_CONFIG_INVALID: EKAS_NATIVE_BLAS_THREADS must be an integer1..64')
    return int(value)


def apply_thread_limit(env):
    count=blas_thread_count(env)
    env.update({name:str(count) for name in (*THREAD_VARIABLES,'EKAS_NATIVE_BLAS_THREADS')})
    return count
