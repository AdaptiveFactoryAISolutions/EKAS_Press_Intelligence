from dataclasses import dataclass
@dataclass(frozen=True)
class GroundTruthEvent:
    event_id: str
    cause: str
@dataclass(frozen=True)
class Claim:
    event_id: str | None
    cause: str
    evidence_ids: tuple[str, ...]
@dataclass(frozen=True)
class Score:
    points: int
    correct_causes: int
    detected: int
    false_positives: int
    evidence_complete: int

def score_claims(truth: list[GroundTruthEvent], claims: list[Claim]) -> Score:
    """Prototype scoring preserves the HistorianRCA false-positive penalty.
    Temporal interval matching replaces event_id matching in the full integration.
    """
    truth_by_id = {e.event_id: e for e in truth}
    seen=set(); points=detected=correct=false_pos=evidence_complete=0
    for c in claims:
        if c.event_id not in truth_by_id or c.event_id in seen:
            false_pos += 1; points -= 1; continue
        seen.add(c.event_id); detected += 1; points += 1
        if c.evidence_ids: evidence_complete += 1
        if c.cause.strip().casefold() == truth_by_id[c.event_id].cause.strip().casefold():
            correct += 1; points += 2
    return Score(points, correct, detected, false_pos, evidence_complete)
