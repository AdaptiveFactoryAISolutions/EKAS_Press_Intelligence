"""Declared press acquisition hardware; no fitted covariance or gate thresholds.

Pulse counters use a16bit scaled digital word over the configured axis range.
One code is span/65536: 3.815um over250mm. Encoder positions are latched each
feed; trajectories/frequency are read on the acquisition clock. Quantization
is deterministic; liquid-level lag/wander and flow turbulence do not apply.

The independent optical gauges measure every transported part. A5000pixel
100mm field with half-pixel interpolation gives10um output increments. A50um
thermal/illumination offset (independent600s OU streams) and0.2um/day ordinary
calibration drift are explicit synthetic instrument assumptions, not machine
calibration claims. Physical transport is resolved by delivery events.
"""
from historiansim.measurement.instrument import InstrumentClass,INSTRUMENT_CLASSES
CLASSES={
 'pulse_position':InstrumentClass(name='pulse_position',tau_s=0.,noise_sigma=0.,noise_tau_s=0.,lsb=1/65536,deadband=1/65536),
 'pulse_speed':InstrumentClass(name='pulse_speed',tau_s=0.,noise_sigma=0.,noise_tau_s=0.,lsb=1/65536,deadband=1/65536),
 'optical_gauge':InstrumentClass(name='optical_gauge',tau_s=0.,noise_sigma=.005,noise_tau_s=600.,lsb=.001,drift_per_day=.00002,deadband=.001),
}
for name,cls in CLASSES.items():
 if name in INSTRUMENT_CLASSES and INSTRUMENT_CLASSES[name]!=cls:raise RuntimeError('PRESS_INSTRUMENT_CLASS_CONFLICT: '+name)
 INSTRUMENT_CLASSES[name]=cls
