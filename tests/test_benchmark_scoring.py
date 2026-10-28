from ekas_press_intelligence.benchmark.scoring import score


def test_false_positive_costs_points():
    truth=[dict(start_s=10,end_s=20,event_class='unknown',event_kind='fault',failed_item='belt',failure_mechanism='slip')]
    one=[dict(start_s=10,end_s=20,event_kind='fault')]
    extra=one+[dict(start_s=100,end_s=110,event_kind='fault')]
    assert score(truth,extra)['points']==score(truth,one)['points']-1
    assert score(truth,extra)['false_positives']==1
