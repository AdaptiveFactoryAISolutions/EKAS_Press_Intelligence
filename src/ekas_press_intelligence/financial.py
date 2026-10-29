"""Financial categories retain assumptions; opportunity never implies savings."""

def estimate(metrics: dict, assumptions: dict) -> dict:
    lost=metrics.get('lost_units')
    margin=assumptions.get('contribution_per_unit')
    risk=lost*margin if lost is not None and margin is not None else None
    provenance=assumptions.get('provenance')
    measured=metrics.get('verification_status')=='VERIFIED' and metrics.get('measured_cost_before') is not None and metrics.get('measured_cost_after') is not None and metrics.get('measurement_provenance')
    savings=max(0,metrics['measured_cost_before']-metrics['measured_cost_after']) if measured else None
    return dict(lost_capacity=lost,production_opportunity=lost,potential_contribution_at_risk=risk,estimated_financial_impact=risk,avoided_cost=metrics.get('measured_avoided_cost') if measured else None,verified_savings=savings,currency=assumptions.get('currency'),assumptions=dict(assumptions),provenance={'estimate':provenance,'measurement':metrics.get('measurement_provenance')},unknowns=[k for k,v in {'lost_units':lost,'contribution_per_unit':margin,'estimate_provenance':provenance,'verified_cost_measurements':savings}.items() if v is None])
