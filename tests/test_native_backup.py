import importlib
import shutil
import pytest
from ekas_press_intelligence.native.jobs import JobStore

def test_backup_restores_frozen_evidence_and_rejects_tampering(tmp_path):
    backup=importlib.import_module('ekas_press_intelligence.native.backup')
    source=tmp_path/'state';store=JobStore(source)
    job=store.create('describe_process',{'plant':'heated_stirred_tank'})
    store.freeze_submission('test','start_utc,end_utc,kind,root_cause,evidence_tags\n')
    artifact=source/'artifacts'/'test';artifact.mkdir(parents=True)
    (artifact/'evidence.txt').write_text('original evidence')
    snapshot=tmp_path/'snapshot';backup.create_backup(source,snapshot)
    with pytest.raises(ValueError,match='empty'):backup.restore_backup(snapshot,source)
    shutil.rmtree(source);backup.restore_backup(snapshot,source)
    restored=JobStore(source)
    assert restored.get(job['id'])['state']=='queued'
    assert restored.submission('test')['sha256']==store.submission('test')['sha256']
    assert (artifact/'evidence.txt').read_text()=='original evidence'
    (snapshot/'artifacts/test/evidence.txt').write_text('tampered')
    shutil.rmtree(source)
    with pytest.raises(ValueError,match='integrity'):backup.restore_backup(snapshot,source)
    assert not source.exists()

def test_nested_manifest_is_not_exempt_from_integrity(tmp_path):
    backup=importlib.import_module('ekas_press_intelligence.native.backup')
    source=tmp_path/'state';JobStore(source)
    snapshot=tmp_path/'snapshot';backup.create_backup(source,snapshot)
    nested=snapshot/'artifacts/injected/BACKUP_MANIFEST.json'
    nested.parent.mkdir(parents=True);nested.write_text('injected evidence')
    shutil.rmtree(source)
    with pytest.raises(ValueError,match='integrity'):backup.restore_backup(snapshot,source)

def test_backup_refuses_active_jobs_and_symlinks(tmp_path):
    backup=importlib.import_module('ekas_press_intelligence.native.backup')
    source=tmp_path/'state';store=JobStore(source)
    job=store.create('generate',{});store.claim('worker')
    with pytest.raises(ValueError,match='active'):backup.create_backup(source,tmp_path/'snapshot')
    store.fail(job['id'],'TEST','test')
    (source/'outside').symlink_to(tmp_path)
    with pytest.raises(ValueError,match='symlink'):backup.create_backup(source,tmp_path/'snapshot')
