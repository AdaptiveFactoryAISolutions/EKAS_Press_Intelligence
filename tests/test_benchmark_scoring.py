from ekas_press_intelligence.benchmark.scoring import GroundTruthEvent, Claim, score_claims

def test_false_positive_costs_points():
    truth=[GroundTruthEvent("E1","feeder sensor intermittency")]
    claims=[Claim("E1","feeder sensor intermittency",("EV1",)),Claim("X","die wear",("EV2",))]
    s=score_claims(truth,claims)
    assert s.points == 2
    assert s.false_positives == 1
