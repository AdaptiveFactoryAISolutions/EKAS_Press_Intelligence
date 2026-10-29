"""Isolated stock upstream runtime with explicitly identified reference PFD assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

PIN='14e616c382a9db8026cbb4ab86bdd803d56ca72e'

def digest(data):return hashlib.sha256(data).hexdigest()

def hashes(root):
    if root.is_symlink():raise ValueError('symlink runtime forbidden')
    result={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('symlink runtime forbidden')
        if '__pycache__' in path.parts:continue
        if path.is_file():result[str(path.relative_to(root))]=digest(path.read_bytes())
        elif not path.is_dir():raise ValueError('special runtime file forbidden')
    return result

def committed(root):
    vendor=root/'vendor/HistorianSim'
    environment={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    def git(*args):return subprocess.check_output(['/usr/bin/git','--no-replace-objects','-C',str(vendor),*args],env=environment)
    if git('rev-parse','HEAD').decode().strip()!=PIN:raise ValueError('upstream pin mismatch')
    names=git('ls-tree','-r','--name-only',PIN).decode().splitlines()
    return {name:git('show',f'{PIN}:{name}') for name in names}

def overlay(root):
    source=root/'extensions/reference_pfd';result={}
    for name in hashes(source):
        parts=Path(name).parts
        if len(parts)!=2 or parts[0] not in ('heated_stirred_tank','exothermic_cstr') or parts[1] not in ('PFD.svg','PFD.png','build_pfd.py','pfd_contract.json'):
            raise ValueError('unexpected reference PFD asset')
        result[f'src/historiansim/plants/{parts[0]}/pfd/{parts[1]}']=(source/name).read_bytes()
    return result

def expected(root):
    files=committed(root);files.update(overlay(root));return files

def _reject_symlink_ancestors(path):
    if any(item.is_symlink() for item in (path,*path.parents)):
        raise ValueError('runtime path may not contain symbolic link ancestors')


def _validate_source_root(source,allow_editable_metadata=False):
    # Bootstrap prepends this whole directory to sys.path. Hashing only the
    # native package cannot authenticate siblings that shadow lazy dependencies.
    _reject_symlink_ancestors(source)
    if not source.is_dir():raise ValueError('runtime src must be a directory')
    for path in source.iterdir():
        if path.name=='historiansim':continue
        if allow_editable_metadata and path.name=='historiansim.egg-info':
            allowed={'PKG-INFO','SOURCES.txt','dependency_links.txt','entry_points.txt','requires.txt','top_level.txt','namespace_packages.txt','not-zip-safe','zip-safe','licenses/LICENSE'}
            if path.is_symlink() or not path.is_dir():raise ValueError('editable metadata must be a real directory')
            for entry in path.rglob('*'):
                name=str(entry.relative_to(path))
                if entry.is_symlink() or (not entry.is_file() and not entry.is_dir()):raise ValueError('unsafe editable metadata entry')
                if (entry.is_dir() and name!='licenses') or (entry.is_file() and name not in allowed):raise ValueError('unsupported editable metadata file')
        else:raise ValueError('runtime src contains an unsupported sibling')
    package=source/'historiansim'
    if package.is_symlink() or not package.is_dir():raise ValueError('runtime package must be a real directory')


def verify_default_source(repo_root,source=None):
    """Authenticate ignored executable files as well as tracked working files."""
    root=Path(repo_root).resolve()
    source=Path(source) if source is not None else root/'vendor/HistorianSim/src'
    _validate_source_root(source,allow_editable_metadata=True)
    prefix='src/historiansim/'
    wanted={name.removeprefix(prefix):digest(data) for name,data in committed(root).items() if name.startswith(prefix)}
    if hashes(source/'historiansim')!=wanted:raise ValueError('default native source file hashes mismatch')
    return {'source':str(source),'package_sha256':wanted}


def prepare_runtime(repo_root,target=None):
    root=Path(repo_root).resolve();target=Path(target or root/'work/reference-runtime')
    _reject_symlink_ancestors(target)
    target=target.resolve()
    if not target.is_relative_to(root/'work') or target==root/'work':raise ValueError('runtime must be isolated under work/')
    if target.exists():
        hashes(target)
        _validate_source_root(target/'src')
        if not (target/'NATIVE_RUNTIME_PROVENANCE.json').exists():raise ValueError('refusing to replace unowned runtime directory')
        shutil.rmtree(target)
    files=expected(root)
    for name,data in files.items():
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    manifest={'kind':'native_reference','upstream_commit':PIN,'source':'committed upstream blobs; authored reference PFD overlay only',
              'runtime_sha256':{name:digest(data) for name,data in files.items() if name.startswith('src/historiansim/')},
              'reference_pfd_overlay_sha256':hashes(root/'extensions/reference_pfd')}
    (target/'NATIVE_RUNTIME_PROVENANCE.json').write_text(json.dumps(manifest,indent=2)+'\n')
    verify_runtime(root,target)
    return target

def verify_runtime(repo_root,runtime):
    root=Path(repo_root).resolve();runtime=Path(runtime)
    _reject_symlink_ancestors(runtime)
    runtime=runtime.resolve()
    if not runtime.is_relative_to(root/'work'):raise ValueError('runtime must be isolated under work/')
    _validate_source_root(runtime/'src')
    manifest=json.loads((runtime/'NATIVE_RUNTIME_PROVENANCE.json').read_text())
    wanted={name.removeprefix('src/historiansim/'):digest(data) for name,data in expected(root).items() if name.startswith('src/historiansim/')}
    if manifest.get('kind')!='native_reference' or manifest.get('upstream_commit')!=PIN:raise ValueError('reference runtime identity mismatch')
    if hashes(runtime/'src/historiansim')!=wanted:raise ValueError('reference source hash mismatch')
    if manifest['runtime_sha256']!={'src/historiansim/'+name:value for name,value in wanted.items()}:raise ValueError('manifest hash mismatch')
    if manifest['reference_pfd_overlay_sha256']!=hashes(root/'extensions/reference_pfd'):raise ValueError('PFD hash mismatch')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--target',type=Path)
    args=parser.parse_args();print(prepare_runtime(args.repo_root,args.target))
