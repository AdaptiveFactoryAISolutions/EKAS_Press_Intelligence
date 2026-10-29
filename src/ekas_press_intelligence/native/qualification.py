"""Independent quantitative reports over actual native measured sweep pairs.

This module does not simulate, infer physical causes or change native limits.
"""
import numpy as np


def envelope_metrics(values,twin,nominal,dt):
    values=np.asarray(values,dtype=float);twin=np.asarray(twin,dtype=float)
    if values.shape!=twin.shape or values.ndim!=1 or not len(values) or nominal==0 or dt<=0:
        raise ValueError('INVALID_MASKING_INPUT: matched nonempty series and nonzero nominal required')
    finite=bool(np.all(np.isfinite(values)) and np.all(np.isfinite(twin)))
    error=np.abs(values-nominal)/abs(nominal)
    window=max(1,int(3600./dt))
    hourly=np.convolve(values,np.ones(window)/window,mode='valid') if len(values)>=window else values
    return {'nominal_setpoint':float(nominal),'observations':len(values),'within_fraction':float(np.mean(error<=.01)),
            'within_one_percent':finite and bool(np.all(error<=.01)),
            'peak_relative_setpoint_error':float(np.max(error)) if finite else None,
            'fault_minus_twin_peak':float(np.max(np.abs(values-twin))) if finite else None,
            'hourly_envelope_peak_relative_error':float(np.max(np.abs(hourly-nominal))/abs(nominal)) if finite else None,
            'definition':'Absolute deviation from nominal setpoint; no tag-span normalization and no twin-difference substitution.'}


def measured_effects(measured,twin,tags,onset_i,end_i,dt,floors):
    """Native Effect formula on a fully populated symptom evidence union."""
    result={}
    for tag in sorted(set(tags)):
        if tag not in measured.values or tag not in twin.values:
            raise ValueError('MISSING_MEASURED_EVIDENCE: '+tag)
        a=np.asarray(measured.values[tag]);b=np.asarray(twin.values[tag])
        if a.ndim!=1 or a.shape!=b.shape or not 0<onset_i<end_i<=len(a) or not np.isfinite(dt) or dt<=0:
            raise ValueError('INVALID_MEASURED_EVIDENCE: mismatched shape or interval '+tag)
        if tag not in floors or not np.isfinite(floors[tag]) or floors[tag]<0:
            raise ValueError('INVALID_NOISE_FLOOR: '+tag)
        after=a[onset_i:end_i]-b[onset_i:end_i];before=a[:onset_i]-b[:onset_i]
        if not len(after) or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or not np.all(np.isfinite(after)) or not np.all(np.isfinite(before)):
            raise ValueError('INVALID_MEASURED_EVIDENCE: nonfinite or empty interval '+tag)
        scale=float(np.std(before)) or float(np.std(b))*1e-3 or 1e-9
        peak=float(after[np.argmax(np.abs(after))]);window=max(1,int(3600./dt))
        smooth=np.convolve(after,np.ones(window)/window,mode='valid') if len(after)>=window else after
        sustained=float(smooth[np.argmax(np.abs(smooth))]);natural=float(np.std(b[onset_i:end_i])) or 1e-9
        result[tag]={'expectation':'measured_union','peak':peak,'snr':abs(peak)/scale,
                     'relative':abs(sustained)/natural,'noise_floor':float(floors[tag]),
                     'sustained':sustained}
    return result


def masking_gate(physical,load,demand,modes,min_snr,out_min,out_max):
    demand=np.asarray(demand,dtype=float);modes=np.asarray(modes)
    if demand.ndim!=1 or demand.shape!=modes.shape or not len(demand) or not np.all(np.isfinite(demand)):
        raise ValueError('INVALID_MASKING_INPUT: actuator/mode series required')
    headroom=float(min(np.min(demand)-100*out_min,100*out_max-np.max(demand)))
    closed=bool(np.all(np.isin(modes,[1,2])))
    moved=load['snr']>min_snr and abs(load['sustained'])>load['noise_floor']
    return {'actuator_min_percent':float(np.min(demand)), 'actuator_max_percent':float(np.max(demand)),
            'headroom_percent':headroom,'closed_loop_entire_interval':closed,
            'qualifies':bool(physical['within_one_percent'] and moved and closed and headroom>0)}


def validate_matrix_config(cfg,seed,rate,measured_n,twin_n):
    loops=[loop for loop in cfg.loops if loop.name=='SIC-271']
    valid=(cfg.unit=='stamping_press' and cfg.seed==seed and cfg.ballast_tags==0
           and cfg.time.days==14. and cfg.time.dt_scan==20. and cfg.time.n_steps==60480
           and measured_n==60480 and twin_n==60480 and cfg.episodes.n_faults==0
           and cfg.episodes.n_benign==0 and not cfg.episodes.background_fouling
           and len(loops)==1 and loops[0].sp==rate)
    if not valid:raise ValueError('MATRIX_CONFIG_MISMATCH: actual native exposure differs from declared matrix')


def terminate_owned(process):
    """Terminate a runner session and await pinned descendants, including escapees."""
    import os
    import signal
    import subprocess
    from .analysis import _owned_process_handles,_wait_process_handles
    handles=_owned_process_handles(process.pid)
    try:
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait(timeout=5)
        for fd in handles:
            try:signal.pidfd_send_signal(fd,signal.SIGKILL)
            except ProcessLookupError:pass
        _wait_process_handles(handles)
    finally:
        for fd in handles:os.close(fd)
