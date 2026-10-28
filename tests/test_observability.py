from ekas_press_intelligence.contracts.models import FailureSignature
from ekas_press_intelligence.observability.coverage import assess_observability

def test_missing_discriminator_is_reported_not_invented():
    f=FailureSignature("feed","Feed fault",frozenset({"press_run"}),frozenset({"feeder_position"}))
    a=assess_observability({"press_run"},[f])
    assert "feed" in a.ambiguous_failures
    assert "feed" not in a.observable_failures
    assert a.recommendations[0].signal_id == "feeder_position"

def test_signal_can_resolve_ambiguity():
    f=FailureSignature("feed","Feed fault",frozenset({"press_run"}),frozenset({"feeder_position"}))
    a=assess_observability({"press_run","feeder_position"},[f])
    assert "feed" in a.observable_failures
