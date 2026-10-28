"""Evidence-only acquisition checks; no scenario or event-class inputs.

STUCK means a suspected acquired-value plateau, not a verified sensor mechanism.
An exactly repeated positive acquired SPM for 30 elapsed seconds requires an
independently advancing stroke counter, with progress in the last five seconds.
Normal zero-speed stops cannot trigger it. Missing values are recognized by None.
"""
import math

RULES={
    'MISSING':'Acquired value is None; no equipment inference is made.',
    'STUCK':'Positive acquired SPM repeats exactly for >=30 elapsed seconds while the independently acquired stroke counter advances (last progress <=5 seconds). Suspected acquisition plateau; not a verified failure mechanism.'}


class AcquisitionMonitor:
    def __init__(self, plateau_s=30, progress_recency_s=5):
        self.plateau_s=plateau_s; self.progress_recency_s=progress_recency_s
        self.previous_spm=None; self.previous_count=None
        self.since=None; self.start_count=None; self.last_progress=None

    def observe(self,t,values):
        flags={key:'MISSING' for key,value in values.items() if value is None}
        spm=values.get('spm'); count=values.get('stroke_count')
        numeric=lambda value:isinstance(value,(int,float)) and math.isfinite(value)
        if not numeric(spm) or not numeric(count):
            self.previous_spm=None;self.previous_count=None;self.since=None
            return flags
        changed=(spm!=self.previous_spm or self.previous_count is None or count<self.previous_count or spm<=0)
        if changed:
            self.since=t;self.start_count=count;self.last_progress=t
        elif count>self.previous_count:
            self.last_progress=t
        if (spm>0 and t-self.since>=self.plateau_s and count>self.start_count
                and t-self.last_progress<=self.progress_recency_s):
            flags['spm']='STUCK'
        self.previous_spm=spm;self.previous_count=count
        return flags
