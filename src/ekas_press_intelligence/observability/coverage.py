from collections import defaultdict
from ekas_press_intelligence.contracts.models import FailureSignature, ObservabilityAssessment, SensorRecommendation

def assess_observability(available: set[str], failures: list[FailureSignature], candidate_costs: dict[str, str] | None = None) -> ObservabilityAssessment:
    candidate_costs = candidate_costs or {}
    out = ObservabilityAssessment(available_signals=set(available))
    missing_to_failures: dict[str, set[str]] = defaultdict(set)
    for f in failures:
        if f.required_signals.issubset(available):
            if not f.discriminating_signals or f.discriminating_signals & available:
                out.observable_failures.add(f.failure_id)
            else:
                out.ambiguous_failures[f.failure_id] = set(f.discriminating_signals)
                for signal in f.discriminating_signals:
                    if signal not in available:
                        missing_to_failures[signal].add(f.failure_id)
        else:
            out.unobservable_failures.add(f.failure_id)
            for signal in f.required_signals - available:
                missing_to_failures[signal].add(f.failure_id)
    out.recommendations = sorted(
        (SensorRecommendation(
            signal_id=s,
            ambiguity_reduction=len(ids),
            reason=f"Adds evidence for {len(ids)} currently ambiguous or unobservable failure class(es).",
            cost_class=candidate_costs.get(s, "unknown"),
        ) for s, ids in missing_to_failures.items()),
        key=lambda x: (-x.ambiguity_reduction, x.signal_id),
    )
    return out
