"""Declared digital encoders, identical hardware assumptions to the press overlay."""
from historiansim.measurement.instrument import InstrumentClass,INSTRUMENT_CLASSES
for name in ('pulse_position','pulse_speed'):
    cls=InstrumentClass(name=name,tau_s=0.,noise_sigma=0.,noise_tau_s=0.,lsb=1/65536,deadband=1/65536)
    if name in INSTRUMENT_CLASSES and INSTRUMENT_CLASSES[name]!=cls:raise RuntimeError('LINE_INSTRUMENT_CLASS_CONFLICT: '+name)
    INSTRUMENT_CLASSES[name]=cls
