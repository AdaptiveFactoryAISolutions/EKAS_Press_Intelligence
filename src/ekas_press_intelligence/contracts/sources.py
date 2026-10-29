"""Vendor-neutral extension boundary; no physical sensor provider is connected."""
from datetime import datetime
from typing import Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime


class SourceObservation(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    source: str = Field(min_length=1)
    signal: str = Field(min_length=1)
    asset: str = Field(min_length=1)
    timestamp: AwareDatetime
    value: float | bool | str | None
    unit: str = Field(min_length=1)
    quality: Literal['GOOD','UNCERTAIN','BAD','MISSING','STUCK']
    modality: Literal['plc','historian','vision','vibration','acoustic','motor_current','tonnage_waveform','thermal']
    calculation: str = Field(min_length=1)
    synthetic: bool


class ObservationProvider(Protocol):
    """Future adapters supply observations, never RCA conclusions or truth."""
    def read(self, asset: str, start: datetime, end: datetime) -> list[SourceObservation]: ...
