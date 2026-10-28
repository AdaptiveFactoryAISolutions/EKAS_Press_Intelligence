import pytest
from ekas_press_intelligence.storage import Store, Conflict


def test_case_survives_restart_with_audit(tmp_path):
    path = tmp_path / 'state.sqlite'
    Store(path).create('case', 'c1', {'state': 'OBSERVED_ANOMALY'})
    store = Store(path)
    store.update('case', 'c1', {'state': 'CORRECTIVE_ACTION'}, reason='record action')
    assert Store(path).get('case', 'c1')['state'] == 'CORRECTIVE_ACTION'
    assert [x['operation'] for x in store.audit('case', 'c1')] == ['CREATE', 'UPDATE']


def test_duplicate_submission_cannot_replace_frozen_claim(tmp_path):
    store = Store(tmp_path / 'state.sqlite')
    store.create('submission', 'run1', {'claims': [{'failed_item': 'feeder'}]})
    with pytest.raises(Conflict):
        store.create('submission', 'run1', {'claims': []})
    with pytest.raises(Conflict):
        store.update('submission', 'run1', {'claims': []}, reason='overwrite')
    assert len(store.get('submission', 'run1')['claims']) == 1


def test_freeze_submission_and_score_is_atomic(tmp_path):
    store=Store(tmp_path/'state.sqlite')
    store.create('score','run1',{'points':3})
    with pytest.raises(Conflict):
        store.freeze_benchmark('run1',{'claims':[]},{'points':0})
    with pytest.raises(KeyError):
        store.get('submission','run1')
