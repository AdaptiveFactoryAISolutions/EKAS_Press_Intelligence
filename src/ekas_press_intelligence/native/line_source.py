"""Bind a queued line run to the exact verified runtime source epoch."""
import hashlib
from pathlib import Path


def model_digest():
    import historiansim
    package=Path(historiansim.__file__).resolve().parent
    manifest=package.parent.parent/'NATIVE_RUNTIME_PROVENANCE.json'
    if manifest.is_file():return hashlib.sha256(manifest.read_bytes()).hexdigest()
    # Used only for stock-source API tests; stamping_line requires a prepared
    # runtime and therefore takes the manifest branch in real execution.
    digest=hashlib.sha256()
    for file in sorted(package.rglob('*.py')):
        digest.update(str(file.relative_to(package)).encode());digest.update(file.read_bytes())
    return digest.hexdigest()


def check_binding(binding):
    if binding and binding.get('model_sha256')!=model_digest():
        raise ValueError('LINE_SOURCE_CHANGED: the queued run belongs to another model version; review the setup and submit a new run')
