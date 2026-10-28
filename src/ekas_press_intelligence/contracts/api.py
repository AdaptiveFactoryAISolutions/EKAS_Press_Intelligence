"""EKAS ORIGINAL executable v1 request and response contracts."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .models import DiagnosisState


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class RunRequest(Request):
    seed: int = Field(default=7, ge=0, le=2**32-1)
    duration_s: int = Field(default=86400, ge=10800, le=604800)
    profile: Literal['sparse','enhanced'] = 'sparse'


class AssessmentRequest(Request):
    profile: Literal['sparse','enhanced'] = 'sparse'
    signals: list[str] | None = None


class InvestigationRequest(Request):
    run_id: str
    asset_id: Literal['Press 27','Feeder 27','Decoiler 27','Line 03'] = 'Press 27'
    question: str = Field(min_length=3, max_length=2000)
    start_s: int = Field(ge=0)
    end_s: int = Field(gt=0)

    @model_validator(mode='after')
    def ordered(self):
        if self.end_s <= self.start_s:
            raise ValueError('end_s must be after start_s')
        return self


class Claim(Request):
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    event_kind: Literal['fault','benign','artifact'] = 'fault'
    failed_item: str | None = None
    failure_mechanism: str | None = None
    evidence: list[str] = Field(default_factory=list)
    alternatives: list[dict[str,Any]] = Field(default_factory=list)
    diagnosis_state: DiagnosisState = DiagnosisState.SUSPECTED_CAUSE

    @model_validator(mode='after')
    def ordered(self):
        if self.end_s <= self.start_s:
            raise ValueError('Claim end must be after start')
        return self


class SubmissionRequest(Request):
    claims: list[Claim] = Field(max_length=100)


class ActionRequest(Request):
    target_event_class: str
    repair_at_s: int = Field(ge=1)
    description: str = Field(min_length=5, max_length=1000)


class FinancialRequest(Request):
    contribution_per_unit: float = Field(ge=0)
    currency: str = Field(pattern='^[A-Z]{3}$')
    assumption_source: str = Field(min_length=5,max_length=1000)


class VerifyRequest(Request):
    action_id: str
    before_start_s: int = Field(ge=0)
    before_end_s: int = Field(gt=0)
    after_start_s: int = Field(ge=0)
    after_end_s: int = Field(gt=0)
    sustained_duration_s: int = Field(default=86400, ge=3600)

    @model_validator(mode='after')
    def ordered(self):
        if not self.before_start_s < self.before_end_s < self.after_start_s < self.after_end_s:
            raise ValueError('Before and after windows must be ordered and disjoint')
        return self


class Extensible(BaseModel):
    model_config = ConfigDict(extra='allow', allow_inf_nan=False)


class EvidenceRecord(Extensible):
    id: str
    source: str
    signal: str | None = None
    asset: str
    timestamp: Any
    calculation: Any
    rule: str
    confidence: str
    qualification: str


class HypothesisResponse(Extensible):
    event_class: str
    event_kind: Literal['fault','benign','artifact']
    asset: str
    failed_item: str
    failure_mechanism: str
    score: float
    disposition: Literal['SUPPORTED','CONTRADICTED','UNRESOLVED','NOT_OBSERVABLE']
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    missing_evidence: list[str]
    reason: str


class CaseResponse(Extensible):
    case_id: str
    run_id: str
    asset_id: str
    diagnosis_state: DiagnosisState
    observed_problem: str
    direct_answer: str
    evidence: list[EvidenceRecord]
    hypotheses: list[HypothesisResponse]
    alternatives: list[HypothesisResponse]
    qualification: str
    recommended_action: str
    period: dict[str,int]


class RunResponse(Extensible):
    run_id: str
    profile: Literal['sparse','enhanced']
    duration_s: int
    hidden_truth_status: Literal['HIDDEN']
    windows: list[dict[str,Any]]


class ScoreResponse(Extensible):
    points: int
    detected: int
    correct_cause: int
    false_positives: int
    missed: int


class VerificationResponse(Extensible):
    status: Literal['VERIFIED','NOT_VERIFIED','INCONCLUSIVE']
    sustained: bool
    reasons: list[str]
    comparisons: dict[str,Any]


class Coverage(Extensible):
    numerator: int
    denominator: int
    definition: str


class Visibility(Extensible):
    event_class: str
    status: Literal['NOT_OBSERVABLE','FULLY_DISTINGUISHABLE','PARTIALLY_DISTINGUISHABLE','INDISTINGUISHABLE']
    required_observations: list[str]
    available_observations: list[str]
    competing_fault_classes: list[str]


class DiscriminationPair(Extensible):
    classes: list[str]
    required_observations: list[str]
    available_observations: list[str]
    missing_discriminators: list[str]
    distinguishable: bool


class AssessmentResponse(Extensible):
    assessment_id: str
    profile: Literal['sparse','enhanced']
    available_signals: list[str]
    classes: list[Visibility]
    pairs: list[DiscriminationPair]
    coverage: Coverage
    pair_coverage: Coverage
    unresolved_equivalence_groups: list[list[str]]


class SensorRecommendationResponse(Extensible):
    signal: str
    fault_classes_separated: list[list[str]]
    current_source_available: bool
    plc_input_possible: bool
    kind: str
    hardware_required: bool
    priority: int
    expected_diagnostic_gain: dict[str,int]
    calculation: str


class GapsResponse(Extensible):
    profile: Literal['sparse','enhanced']
    recommendations: list[SensorRecommendationResponse]


class AssetResponse(Extensible):
    asset_id: str
    name: str
    parent: str | None
    relationship: str


class AssetsResponse(Extensible):
    assets: list[AssetResponse]


class SignalResponse(Extensible):
    signal_id: str
    asset: str
    description: str
    unit: str | None
    existing: bool
    kind: str
    priority: int
    hardware_required: bool


class SignalsResponse(Extensible):
    signals: list[SignalResponse]


class CaseEvidenceResponse(Extensible):
    evidence: list[EvidenceRecord]
    samples: list[dict[str,Any]]
    events: list[dict[str,Any]]
    maintenance: list[dict[str,Any]]
    quality: list[dict[str,Any]]
    pfmea: list[dict[str,Any]]
    control_plan: list[dict[str,Any]]


class SubmissionResponse(Extensible):
    run_id: str
    submission: list[Claim]
    score: ScoreResponse
    hidden_truth_status: Literal['SCORED']


class FinancialResponse(Extensible):
    financial_id: str
    lost_capacity: float | None
    production_opportunity: float | None
    potential_contribution_at_risk: float | None
    estimated_financial_impact: float | None
    avoided_cost: float | None
    verified_savings: float | None
    currency: str | None
    assumptions: dict[str,Any]
    provenance: dict[str,Any]
    unknowns: list[str]
