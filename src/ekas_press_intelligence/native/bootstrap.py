"""Fail closed on foreign native imports or an unverified patched build."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

_IMPORT_CACHE=None


def activate():
    global _IMPORT_CACHE
    # A source hash cannot authenticate timestamp-valid cached executable code.
    # Use a new private cache namespace and disable writes, so no runtime-local
    # or inherited bytecode cache can be read during verified native imports.
    if _IMPORT_CACHE is None:_IMPORT_CACHE=tempfile.TemporaryDirectory(prefix='ekas-verified-import-')
    sys.pycache_prefix=_IMPORT_CACHE.name
    sys.dont_write_bytecode=True
    root=Path(os.environ.get('EKAS_NATIVE_REPO_ROOT',Path(__file__).resolve().parents[3])).resolve()
    result=subprocess.run(['bash',str(root/'scripts/verify_upstreams.sh')],capture_output=True,text=True,
                          env=dict(os.environ,GIT_NO_REPLACE_OBJECTS='1'),timeout=30)
    if result.returncode:raise RuntimeError('Native upstream verification failed: '+(result.stderr or result.stdout).strip())
    runtime=os.environ.get('EKAS_NATIVE_RUNTIME')
    kind='immutable_upstream'
    if runtime:
        manifest=json.loads((Path(runtime)/'NATIVE_RUNTIME_PROVENANCE.json').read_text())
        reference=manifest.get('kind')=='native_reference'
        script=root/('scripts/prepare_reference_runtime.py' if reference else 'scripts/prepare_native_runtime.py')
        spec=importlib.util.spec_from_file_location('_ekas_native_runtime_verifier',script)
        verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
        try:verifier.verify_runtime(root,Path(runtime))
        except Exception as exc:raise RuntimeError('Prepared native runtime verification failed: '+str(exc)) from exc
        source=Path(runtime).resolve()/'src';kind='verified_native_reference' if reference else 'verified_hybrid_extension'
    else:source=root/'vendor/HistorianSim/src'
    loaded=sys.modules.get('historiansim')
    expected=(source/'historiansim').resolve()
    if loaded is not None:
        location=getattr(loaded,'__file__',None)
        if not location or Path(location).resolve().parent!=expected:
            raise RuntimeError('Native runtime is already imported from a different source; restart instead of hot-swapping')
    if str(source) not in sys.path:sys.path.insert(0,str(source))
    spec=importlib.util.find_spec('historiansim')
    if spec is None or not spec.origin or Path(spec.origin).resolve().parent!=expected:
        raise RuntimeError('Native runtime import origin is not the verified source')
    return {'kind':kind,'source':str(source),'repository':str(root)}
