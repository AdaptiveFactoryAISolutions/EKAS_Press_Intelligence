"""Compiled form of the same RK4/event equations; native stages stay in Python."""
from __future__ import annotations
import ctypes as C
from pathlib import Path
import math
import numpy as np
from historiansim.plants.stamping_press.cycles import PressCycleEvents

PARAMETERS=('cut_perimeter','shear_strength','forming_travel','inertia','torque','efficiency','bearing_drag','other_loss','viscosity','die_wear','guide_drag','traction','backlash','obstruction','brake_drag','pump_efficiency','filter_resistance','leakage','film_delivery','oil_capacity','die_capacity','brake_coefficient','strip_density','strip_width','trim_fraction','servo_tau','hydraulic_tau','coolant_ua','oil_ua','feed_gain','design_rate')
SCALARS=('gate','cycle_work','cycle_pitch','cycle_encoder','phase','completed','good','reject','pitch','encoder','feed_complete','running','token','token_pitch','token_mass','token_thickness','buffer_mass','supplied_mass','withdrawn_mass','trim_mass','product_mass','inspection','checked','motor_energy','loss_energy','forming_energy','actual_forming_energy','initial_energy','energy_residual','energy_relative_residual','pending_start','pending_count','stop','clutch','paused_work')
MAPPING={name:{'gate':'gate_enabled','cycle_pitch':'cycle_pitch_m','cycle_encoder':'cycle_encoder_pitch','encoder':'encoder_pitch','stop':'stop_requested','clutch':'clutch_closed'}.get(name,name) for name in SCALARS if name not in ('token','token_pitch','token_mass','token_thickness','pending_start','pending_count')}
class State(C.Structure):
    _fields_=[(name,C.c_double) for name in SCALARS]+[('pending_time',C.c_double*512),('pending_dimension',C.c_double*512)]
class Event(C.Structure):
    _fields_=[(name,C.c_double) for name in ('time','pitch','count','kind','rejected')]

_LIBRARY=None
def library():
    global _LIBRARY
    if _LIBRARY is None:
        path=Path(__file__).with_name('cycle_kernel.so')
        if not path.is_file():raise RuntimeError('COMPILED_PRESS_KERNEL_MISSING: rebuild the verified native runtime')
        lib=C.CDLL(str(path))
        lib.press_state_size.restype=C.c_uint64;lib.press_event_size.restype=C.c_uint64;lib.press_abi_version.restype=C.c_int
        if lib.press_abi_version()!=7 or lib.press_state_size()!=C.sizeof(State) or lib.press_event_size()!=C.sizeof(Event):
            raise RuntimeError('PRESS_KERNEL_ABI_MISMATCH')
        pointer=C.POINTER(C.c_double)
        lib.press_advance.argtypes=[C.c_double,pointer,pointer,pointer,pointer,C.POINTER(State),C.c_double,C.c_int,C.POINTER(Event),C.c_int,C.POINTER(C.c_int)]
        lib.press_advance.restype=C.c_int
        _LIBRARY=lib
    return _LIBRARY

class CompiledPressCycleEvents(PressCycleEvents):
    backend='compiled-cpp-rk4-events'
    def __init__(self,unit,x,u,d,p):
        super().__init__(unit,x,u,d,p)
        self._native=State()
        for field,attr in MAPPING.items():setattr(self._native,field,float(getattr(self,attr)))
        self._events_buffer=(Event*256)()
        self._library=library()

    def advance(self,t,x,u,d,p,dt_sim,n_sub):
        state=self._native
        state.stop=float(self.stop_requested)
        xx=np.asarray(x,dtype=np.float64).copy()
        uu=np.array([u[name] for name in self.unit.mv_names],dtype=np.float64)
        dd=np.array([d[name] for name in self.unit.disturbance_names],dtype=np.float64)
        pp=np.array([p[name] for name in PARAMETERS],dtype=np.float64)
        duration=dt_sim*n_sub
        max_speed=abs(float(x[0]))+max(p['efficiency']*p['torque']*u['DRIVE-271']*d['voltage']/p['inertia'],0)*duration+.1
        capacity=math.ceil(duration*max_speed/(2*math.pi)*4)+128
        if capacity>10_000_000:raise RuntimeError('PRESS_EVENT_ALLOCATION_EXCESS: integration scan exceeds supported event allocation')
        if capacity>len(self._events_buffer):self._events_buffer=(Event*capacity)()
        count=C.c_int(0);pointer=C.POINTER(C.c_double)
        status=self._library.press_advance(float(t),xx.ctypes.data_as(pointer),uu.ctypes.data_as(pointer),dd.ctypes.data_as(pointer),pp.ctypes.data_as(pointer),C.byref(state),float(dt_sim),int(n_sub),self._events_buffer,len(self._events_buffer),C.byref(count))
        if status:
            reason={-1:'NONFINITE_PHYSICS',-2:'EVENT_BUFFER_CAPACITY',-3:'TRANSPORT_BUFFER_CAPACITY',-4:'BOUNDARY_CONVERGENCE'}.get(status,'UNKNOWN')
            raise RuntimeError('PRESS_KERNEL_'+reason)
        for field,attr in MAPPING.items():
            value=getattr(state,field)
            setattr(self,attr,int(value) if field in ('completed','good','reject') else bool(value) if field in ('gate','stop','clutch') else float(value))
        self.feed_token=(float(state.token_pitch),float(state.token_mass),float(state.token_thickness)) if state.token else None
        self.pending=[(float(state.pending_time[(int(state.pending_start)+i)%512]),float(state.pending_dimension[(int(state.pending_start)+i)%512])) for i in range(int(state.pending_count))]
        if count.value:
            data=np.frombuffer(self._events_buffer,dtype=np.float64,count=count.value*5).reshape(count.value,5)
            for array,column,dtype in ((self.events.time,0,np.float64),(self.events.pitch,1,np.float64),(self.events.count,2,np.int64),(self.events.kind,3,np.int8),(self.events.rejected,4,np.int8)):
                array.frombytes(np.ascontiguousarray(data[:,column],dtype=dtype).tobytes())
        return xx
