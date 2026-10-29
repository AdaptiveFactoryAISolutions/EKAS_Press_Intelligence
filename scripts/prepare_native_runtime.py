"""Build an isolated, reproducible native source runtime without editing vendor.

Call prepare_runtime(repo_root), then prepend returned_path / 'src' to
PYTHONPATH before importing historiansim. Existing imported modules must not be
hot-swapped. Source blobs are read directly from the protected pinned vendor.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

UPSTREAM_COMMIT='14e616c382a9db8026cbb4ab86bdd803d56ca72e'

def _git_env():
    result={key:value for key,value in os.environ.items() if key not in ('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR')}
    result['GIT_NO_REPLACE_OBJECTS']='1'
    return result


def prepare_runtime(repo_root:Path,target:Path|None=None)->Path:
    repo_root=Path(repo_root).resolve()
    vendor=repo_root/'vendor/HistorianSim'
    source=vendor
    def git(path,*args):return subprocess.check_output(['/usr/bin/git','-C',str(path),*args],text=True,env=_git_env()).strip()
    expected=git(vendor,'rev-parse','HEAD')
    if expected != UPSTREAM_COMMIT: raise RuntimeError('protected vendor pin changed')
    target=Path(target or repo_root/'work/native-runtime')
    _reject_symlink_ancestors(target)
    target=target.resolve()
    if target==vendor.resolve() or target==source.resolve() or not target.is_relative_to(repo_root/'work'):
        raise ValueError('runtime target must be a separate directory beneath work/')
    tracked=git(source,'ls-tree','-r','--name-only',expected).splitlines()
    # Copy only the immutable committed blobs, excluding scaffold modifications.
    target.mkdir(parents=True,exist_ok=True)
    _file_hashes(target)  # reject symlinks and special files before mutation
    if (target/'src').exists(): _validate_source_root(target/'src')
    package=target/'src/historiansim'
    if package.exists(): shutil.rmtree(package)
    for name in tracked:
        obj=subprocess.check_output(['/usr/bin/git','-C',str(source),'show',f'{expected}:{name}'],env=_git_env())
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(obj)
    for patch in sorted((repo_root/'patches').glob('*.patch')):
        subprocess.run(['/usr/bin/git','apply','--check',str(patch)],cwd=target,check=True,env=_git_env())
        subprocess.run(['/usr/bin/git','apply',str(patch)],cwd=target,check=True,env=_git_env())
    extension_target=target/'src/historiansim/plants/stamping_press'
    if extension_target.exists(): shutil.rmtree(extension_target)
    shutil.copytree(repo_root/'extensions/stamping_press',extension_target,ignore=shutil.ignore_patterns('__pycache__'))
    reference_overlay=repo_root/'extensions/reference_pfd'
    reference_hashes=_file_hashes(reference_overlay) if reference_overlay.exists() else {}
    for name in reference_hashes:
        parts=Path(name).parts
        if len(parts)!=2 or parts[0] not in ('heated_stirred_tank','exothermic_cstr') or parts[1] not in ('PFD.svg','PFD.png','build_pfd.py','pfd_contract.json'):
            raise ValueError('unsupported reference PFD overlay file')
        dest=target/'src/historiansim/plants'/parts[0]/'pfd'/parts[1]
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(reference_overlay/name,dest)
    kernel_source=extension_target/'cycle_kernel.cpp'
    kernel_build={}
    if kernel_source.exists():
        compiler=Path('/usr/bin/g++')
        if not compiler.is_file(): raise RuntimeError('COMPILED_PRESS_COMPILER_MISSING: project runtime requires g++')
        flags=['-O3','-std=c++17','-fPIC','-shared','-ffp-contract=off','-fno-fast-math','-Wl,--build-id=none']
        artifact=extension_target/'cycle_kernel.so'
        subprocess.run([str(compiler),*flags,str(kernel_source),'-o',str(artifact)],check=True)
        kernel_build={'compiler':str(compiler.resolve()),'compiler_sha256':hashlib.sha256(compiler.read_bytes()).hexdigest(),'flags':flags,'source_sha256':hashlib.sha256(kernel_source.read_bytes()).hexdigest(),'artifact_sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()}
    provenance={'upstream_commit':expected,'source':'committed full source blobs','patches':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((repo_root/'patches').glob('*.patch'))},
                'extension':{str(p.relative_to(repo_root/'extensions')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((repo_root/'extensions/stamping_press').rglob('*')) if p.is_file() and '__pycache__' not in str(p)}}
    provenance['compiled_kernel_build']=kernel_build
    provenance['reference_pfd_overlay_sha256']=reference_hashes
    provenance['reference_pfd_origin']='authored engineering overlay; no upstream PFD assets exist at pinned commit'
    _validate_source_root(target/'src')
    provenance['runtime_sha256']=_file_hashes(target/'src/historiansim')
    provenance['reference_pfd_sha256']={name:digest for name,digest in provenance['runtime_sha256'].items() if '/pfd/' in name and '/stamping_press/' not in name}
    (target/'NATIVE_RUNTIME_PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
    return target

def _reject_symlink_ancestors(path:Path)->None:
    for item in (path,*path.parents):
        if item.is_symlink(): raise ValueError('runtime path may not contain symbolic link ancestors')

def _validate_source_root(source:Path)->None:
    _reject_symlink_ancestors(source)
    if not source.is_dir(): raise ValueError('runtime src must be a directory')
    if any(path.name!='historiansim' for path in source.iterdir()):
        raise ValueError('runtime src contains an unsupported sibling')
    package=source/'historiansim'
    if package.exists() and not package.is_dir(): raise ValueError('runtime package must be a directory')


def _file_hashes(root:Path)->dict:
    _reject_symlink_ancestors(root)
    if root.is_symlink(): raise ValueError('runtime root must not be a symbolic link')
    out={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink(): raise ValueError('runtime may not contain symbolic links')
        if '__pycache__' in path.parts: continue
        if path.is_file(): out[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
        elif not path.is_dir(): raise ValueError('runtime contains unsupported file type')
    return out

def verify_runtime(repo_root:Path,runtime:Path)->dict:
    repo_root=Path(repo_root).resolve();runtime=Path(runtime)
    if runtime.is_symlink(): raise ValueError('runtime must not be a symbolic link')
    _reject_symlink_ancestors(runtime)
    runtime=runtime.resolve()
    if not runtime.is_relative_to(repo_root/'work') or runtime==repo_root/'work/HistorianSim-authoring':
        raise ValueError('runtime must be isolated under work/')
    manifest=json.loads((runtime/'NATIVE_RUNTIME_PROVENANCE.json').read_text())
    vendor_commit=subprocess.check_output(['/usr/bin/git','-C',str(repo_root/'vendor/HistorianSim'),'rev-parse','HEAD'],text=True,env=_git_env()).strip()
    if vendor_commit!=UPSTREAM_COMMIT: raise ValueError('protected vendor pin changed')
    if manifest['upstream_commit']!=vendor_commit: raise ValueError('runtime upstream commit mismatch')
    patches={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((repo_root/'patches').glob('*.patch'))}
    extensions=_file_hashes(repo_root/'extensions/stamping_press')
    extensions={'stamping_press/'+name:digest for name,digest in extensions.items()}
    if manifest['patches']!=patches: raise ValueError('runtime patch hashes mismatch')
    if manifest['extension']!=extensions: raise ValueError('runtime extension hashes mismatch')
    overlay=repo_root/'extensions/reference_pfd'
    overlay_hashes=_file_hashes(overlay) if overlay.exists() else {}
    if manifest['reference_pfd_overlay_sha256']!=overlay_hashes: raise ValueError('reference PFD overlay hashes mismatch')
    _validate_source_root(runtime/'src')
    actual=_file_hashes(runtime/'src/historiansim')
    if manifest['runtime_sha256']!=actual: raise ValueError('runtime source file hashes mismatch')
    pfds={name:digest for name,digest in actual.items() if '/pfd/' in name and '/stamping_press/' not in name}
    if manifest['reference_pfd_sha256']!=pfds: raise ValueError('reference PFD hash mismatch')
    with tempfile.TemporaryDirectory(prefix='verify-native-source-',dir=repo_root/'work') as scratch:
        expected=prepare_runtime(repo_root,Path(scratch))
        derived=json.loads((expected/'NATIVE_RUNTIME_PROVENANCE.json').read_text())
        if actual!=derived['runtime_sha256']: raise ValueError('runtime differs from derived pinned source')
        if manifest!=derived: raise ValueError('runtime provenance differs from derived pinned source')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--target',type=Path)
    args=parser.parse_args();print(prepare_runtime(args.repo_root,args.target))
