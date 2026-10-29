from types import SimpleNamespace
import pytest


def test_practice_never_promotes_native_failure_to_qualified_success():
    from ekas_press_intelligence.native.engine import validation_outcome
    checks=[SimpleNamespace(passed=False,severity='error')]
    result=validation_outcome(checks,True,True,{'passed':True})
    assert result['passed'] is None
    assert result['native_validation_passed'] is False
    assert result['qualification_status']=='UNQUALIFIED_PRACTICE'
    assert result['validation_performed'] is True


def test_engineering_failure_blocks_practice_and_regular_checks_still_block():
    from ekas_press_intelligence.native.engine import validation_outcome
    assert validation_outcome([],True,True,{'passed':False})['passed'] is False
    assert validation_outcome([SimpleNamespace(passed=False,severity='error')],True,False,None)['passed'] is False


def test_even_all_checks_passing_does_not_qualify_practice():
    from ekas_press_intelligence.native.engine import validation_outcome
    result=validation_outcome([],True,True,{'passed':True})
    assert result['passed'] is None and result['native_validation_passed'] is True
