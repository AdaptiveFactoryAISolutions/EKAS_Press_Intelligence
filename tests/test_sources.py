import pytest
from pydantic import ValidationError
from ekas_press_intelligence.contracts.sources import SourceObservation


def test_optional_edge_observation_requires_provenance_and_explicit_quality():
    good=dict(source='synthetic-waveform-test',signal='press.current.envelope',asset='Press 27',
              timestamp='2026-10-28T00:00:00Z',value=23.2,unit='A',quality='GOOD',
              modality='motor_current',calculation='RMS of sampled current',synthetic=True)
    assert SourceObservation(**good).modality=='motor_current'
    for field in ('source','asset','timestamp','quality','calculation','synthetic'):
        missing=dict(good);missing.pop(field)
        with pytest.raises(ValidationError):SourceObservation(**missing)


def test_unqualified_sensor_output_cannot_silently_become_good_data():
    with pytest.raises(ValidationError):
        SourceObservation(source='camera',signal='strip.present',asset='Press 27',
            timestamp='2026-10-28T00:00:00Z',value=True,unit='state',quality='probably',
            modality='vision',calculation='frame inference',synthetic=False)
