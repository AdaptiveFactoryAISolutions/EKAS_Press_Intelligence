from ekas_press_intelligence.contracts.models import FailureSignature
from ekas_press_intelligence.observability.coverage import assess_observability
FAILURES = [
    FailureSignature("feeder_sensor", "Feeder sensor intermittency", frozenset({"press_run", "fault_bit"}), frozenset({"feeder_position"})),
    FailureSignature("material_starvation", "Material starvation", frozenset({"press_run", "fault_bit"}), frozenset({"material_present", "loop_level"})),
    FailureSignature("lube_loss", "Lubrication pressure loss", frozenset({"press_run"}), frozenset({"lube_pressure"})),
    FailureSignature("die_wear", "Die wear progression", frozenset({"press_run", "scrap_count"}), frozenset({"tonnage", "quality_measurement"})),
]
def main():
    sparse={"press_run","fault_bit","spm","stroke_count","scrap_count"}
    result=assess_observability(sparse,FAILURES,{"feeder_position":"medium","material_present":"low","loop_level":"low","lube_pressure":"low","tonnage":"medium","quality_measurement":"existing"})
    print("EKAS PRESS OBSERVABILITY — PROTOTYPE")
    print("Observable:", sorted(result.observable_failures) or "none")
    print("Ambiguous:", result.ambiguous_failures)
    print("Unobservable:", sorted(result.unobservable_failures))
    print("Recommended signals:")
    for r in result.recommendations:
        print(f"- {r.signal_id}: resolves/supports {r.ambiguity_reduction} class(es); cost={r.cost_class}")
if __name__ == "__main__": main()
