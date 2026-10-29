"""Integrity-checked local snapshots. Restore preserves the original absolute paths."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

def _files(root):
    if root.is_symlink():raise ValueError('symlink snapshot forbidden')
    values={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('symlink snapshot forbidden')
        if path.is_file():
            if path==root/'BACKUP_MANIFEST.json':continue
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
            values[str(path.relative_to(root))]=digest.hexdigest()
        elif not path.is_dir():raise ValueError('special snapshot file forbidden')
    return values

def create_backup(state_dir,destination):
    source=Path(state_dir);destination=Path(destination)
    _files(source)
    source=source.resolve()
    if destination.exists():raise ValueError('backup destination must not exist')
    if destination.resolve().is_relative_to(source):raise ValueError('backup must be outside state directory')
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.native-backup-',dir=destination.parent));stage.chmod(0o700)
    lock=sqlite3.connect(source/'native.sqlite',timeout=30)
    try:
        lock.execute('BEGIN IMMEDIATE')
        if lock.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('running','cancel_requested')").fetchone()[0]:
            raise ValueError('backup refuses active jobs; wait for completion or cancel first')
        for path in source.iterdir():
            if path.name.startswith('native.sqlite'):continue
            if path.is_symlink():raise ValueError('symlink snapshot forbidden')
            if path.is_dir():shutil.copytree(path,stage/path.name)
            else:shutil.copy2(path,stage/path.name)
        with sqlite3.connect(source/'native.sqlite') as reader,sqlite3.connect(stage/'native.sqlite') as writer:
            reader.backup(writer)
        manifest={'schema':1,'original_state_path':str(source),'files':_files(stage)}
        (stage/'BACKUP_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (stage/'native.sqlite').chmod(0o600)
        stage.rename(destination)
    finally:
        lock.rollback();lock.close()
        if stage.exists():shutil.rmtree(stage)
    return destination

def restore_backup(snapshot,state_dir):
    snapshot=Path(snapshot);target=Path(state_dir)
    actual=_files(snapshot)
    manifest=json.loads((snapshot/'BACKUP_MANIFEST.json').read_text())
    if manifest.get('schema')!=1 or manifest.get('files')!=actual:raise ValueError('backup integrity verification failed')
    if target.is_symlink():raise ValueError('symlink restore forbidden')
    if str(target.resolve())!=manifest['original_state_path']:raise ValueError('restore requires original absolute state path')
    if target.exists() and any(target.iterdir()):raise ValueError('restore target must be empty; stop service and preserve existing state first')
    with sqlite3.connect(f'file:{snapshot / "native.sqlite"}?mode=ro',uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('database integrity verification failed')
    target.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.native-restore-',dir=target.parent));stage.chmod(0o700)
    try:
        for path in snapshot.iterdir():
            if path.name=='BACKUP_MANIFEST.json':continue
            if path.is_dir():shutil.copytree(path,stage/path.name)
            else:shutil.copy2(path,stage/path.name)
        (stage/'native.sqlite').chmod(0o600)
        if target.exists():target.rmdir()
        stage.rename(target)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('create','restore'));parser.add_argument('state',type=Path);parser.add_argument('snapshot',type=Path)
    args=parser.parse_args()
    print(create_backup(args.state,args.snapshot) if args.operation=='create' else restore_backup(args.snapshot,args.state))
