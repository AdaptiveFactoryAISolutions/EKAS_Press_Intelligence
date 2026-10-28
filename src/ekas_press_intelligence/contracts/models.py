from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

class DiagnosisState(str, Enum):
    OBSERVATION = "OBSERVATION"
    CORRELATION = "CORRELATION"
    CONTRIBUTOR = "CONTRIBUTOR"
    SUSPECTED_CAUSE = "SUSPECTED_CAUSE"
    EVIDENCE_SUPPORTED_CAUSE = "EVIDENCE_SUPPORTED_CAUSE"
    VERIFIED_ROOT_CAUSE = "VERIFIED_ROOT_CAUSE"
    CORRECTIVE_ACTION = "CORRECTIVE_ACTION"
    VERIFIED_RESULT = "VERIFIED_RESULT"
    SUSTAINED_RESULT = "SUSTAINED_RESULT"

@dataclass(frozen=True)
class SignalDefinition:
    signal_id: str
    asset: str
    description: str
    unit: str | None = None
    source: str = "unknown"
    existing: bool = True
    cost_class: str = "existing"

@dataclass(frozen=True)
class FailureSignature:
    failure_id: str
    name: str
    required_signals: frozenset[str]
    discriminating_signals: frozenset[str] = frozenset()

@dataclass
class ObservabilityAssessment:
    available_signals: set[str]
    observable_failures: set[str] = field(default_factory=set)
    ambiguous_failures: dict[str, set[str]] = field(default_factory=dict)
    unobservable_failures: set[str] = field(default_factory=set)
    recommendations: list["SensorRecommendation"] = field(default_factory=list)

@dataclass(frozen=True)
class SensorRecommendation:
    signal_id: str
    ambiguity_reduction: int
    reason: str
    cost_class: str = "unknown"

@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source: str
    signal_or_event: str
    observation: str
    supports: tuple[str, ...] = ()
    rules_out: tuple[str, ...] = ()

@dataclass
class RcaCase:
    case_id: str
    asset: str
    problem: str
    state: DiagnosisState
    hypotheses: list[str]
    evidence: list[Evidence]
    alternatives_ruled_out: list[str]
    qualification: str
