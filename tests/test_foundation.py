from ekas_press_intelligence.contracts.models import DiagnosisState


def test_charter_state_vocabulary_is_exact():
    assert {s.value for s in DiagnosisState} == {
        'OBSERVED_ANOMALY', 'CONTRIBUTOR', 'SUSPECTED_CAUSE',
        'EVIDENCE_SUPPORTED_CAUSE', 'VERIFIED_ROOT_CAUSE',
        'CORRECTIVE_ACTION', 'VERIFICATION', 'SUSTAINED',
    }


def test_context_provenance_serializes_through_the_executable_contract():
    from ekas_press_intelligence.rca.engine import investigate
    from ekas_press_intelligence.contracts.api import CaseResponse
    evidence={'context':{},'samples':[{'t':t,'spm':60,'press_run':1} for t in range(8)],
              'pfmea':[{'signal_ids':['feed_complete','strip_progression']}],
              'control_plan':[{'asset':'Feeder 27','signal_ids':['feed_complete']}]}
    result=investigate(evidence)
    response=CaseResponse(**dict(result,case_id='c1',run_id='r1',asset_id='Press 27'))
    assert all(e.signal is None or isinstance(e.signal,str) for e in response.evidence)
