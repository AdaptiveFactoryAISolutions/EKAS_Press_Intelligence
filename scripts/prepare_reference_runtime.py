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

def prepare_runtime(repo_root,target=None):
    root=Path(repo_root).resolve();target=Path(target or root/'work/reference-runtime')
    if target.is_symlink():raise ValueError('symlink runtime forbidden')
    target=target.resolve()
    if not target.is_relative_to(root/'work') or target==root/'work':raise ValueError('runtime must be isolated under work/')
    if target.exists():
        hashes(target)
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
    if runtime.is_symlink():raise ValueError('symlink runtime forbidden')
    runtime=runtime.resolve()
    if not runtime.is_relative_to(root/'work'):raise ValueError('runtime must be isolated under work/')
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
