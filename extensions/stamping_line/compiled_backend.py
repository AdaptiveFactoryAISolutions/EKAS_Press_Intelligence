"""Exact C++ RK4/event execution; Python retains native hooks and observations.

The reference implementation remains selectable with compiled_cycles=0. No
integration interval, event boundary, instrument, controller or gate is changed.
"""
from __future__ import annotations
import ctypes as C
from pathlib import Path
import math
import weakref
import numpy as np
from .cycles import LineCycleEvents
from .model import StampingLine
PARAMETERS=tuple(StampingLine.default_params())
SCALARS=('integration_steps','water_initial','water_makeup','water_evap','water_energy_initial','water_energy_in','water_energy_out','phase','completed','produced','packed','rejected','pack_queue','container_fill','containers','change_until','pack_credit','next_wash','blocked','stop_requested','loop_m','linear_mass','coils_loaded','coil_change_until','remaining_kg','initial_kg','consumed_kg','scrap_kg','scrap_removed_kg','die_mass_kg','output_mass_kg','energy_in','energy_forming','energy_loss','last_pitch','feed_shaft_m','feed_strip_m','feed_mass_kg','feed_failed','feed_complete','running','wash_qualified','payout','straightener_speed','lube_initial_l','lube_makeup_l','lube_loss_l')
BOOLEANS={'blocked','stop_requested','feed_failed','feed_complete','running','wash_qualified'}
INTEGERS={'integration_steps','completed','produced','packed','rejected','pack_queue','container_fill','containers','coils_loaded'}
class Event(C.Structure):_fields_=[(name,C.c_double) for name in ('time','kind','count')]
_LIBRARY=None
POINTER=C.POINTER(C.c_double)
def library():
    global _LIBRARY
    if _LIBRARY is None:
        path=Path(__file__).with_name('cycle_kernel.so')
        if not path.is_file():raise RuntimeError('COMPILED_LINE_KERNEL_MISSING: rebuild the verified native runtime')
        lib=C.CDLL(str(path))
        lib.line_abi_version.restype=C.c_int
        lib.line_scalar_count.restype=C.c_int
        if lib.line_abi_version()!=2 or lib.line_scalar_count()!=len(SCALARS):raise RuntimeError('LINE_KERNEL_ABI_MISMATCH')
        lib.line_create.argtypes=[POINTER,POINTER];lib.line_create.restype=C.c_void_p
        lib.line_destroy.argtypes=[C.c_void_p]
        lib.line_advance.argtypes=[C.c_void_p,C.c_double,POINTER,C.c_double,C.c_double,POINTER,C.c_double,C.c_double,C.POINTER(Event),C.c_int,C.POINTER(C.c_int),POINTER,POINTER,POINTER]
        lib.line_advance.restype=C.c_int
        lib.line_queue.argtypes=[C.c_void_p,C.c_int,POINTER,C.c_int];lib.line_queue.restype=C.c_int
        _LIBRARY=lib
    return _LIBRARY
class QueueView:
    def __init__(self,owner,index):self.owner=owner;self.index=index;self.size=0
    def __len__(self):return self.size
    def __iter__(self):
        owner=self.owner;data=np.empty((self.size,4),dtype=np.float64)
        count=owner._library.line_queue(owner._native,self.index,data.ctypes.data_as(POINTER),self.size)
        if count!=self.size:raise RuntimeError('LINE_QUEUE_SNAPSHOT_MISMATCH')
        width=2 if self.index==0 else 4
        return iter(tuple(row[:width]) for row in data)
    def __getitem__(self,index):return list(self)[index]
class CompiledLineCycleEvents(LineCycleEvents):
    backend='compiled-cpp-rk4-events'
    def __init__(self,unit,x,u,d,p):
        super().__init__(unit,x,u,d,p)
        self._library=library()
        self._scalars=np.array([getattr(self,n) for n in SCALARS],dtype=np.float64)
        self._die=np.array([float('nan') if value is None else value for value in self.die],dtype=np.float64)
        self._counts=np.zeros(2,dtype=np.float64)
        self._native=self._library.line_create(self._scalars.ctypes.data_as(POINTER),self._die.ctypes.data_as(POINTER))
        if not self._native:raise RuntimeError('LINE_KERNEL_ALLOCATION_FAILED')
        self._release=weakref.finalize(self,self._library.line_destroy,self._native)
        self.discharge=QueueView(self,0);self.washer=QueueView(self,1)
        self._events_buffer=(Event*256)()
    def advance(self,t,x,u,d,p,dt_sim,n_sub):
        xx=np.asarray(x,dtype=np.float64).copy()
        pp=np.fromiter((p[n] for n in PARAMETERS),dtype=np.float64,count=len(PARAMETERS))
        duration=dt_sim*n_sub
        capacity=int(2*p['buffer_parts']+math.ceil(duration*(10/60*(p['parts_per_stroke']+4)+p['packers']*p['packing_rate_per_min']/60))+128)
        if capacity>10_000_000:raise RuntimeError('LINE_EVENT_ALLOCATION_EXCESS')
        if capacity>len(self._events_buffer):self._events_buffer=(Event*capacity)()
        count=C.c_int()
        status=self._library.line_advance(self._native,float(t),xx.ctypes.data_as(POINTER),float(u['DRIVE-1500']),float(d.get('T_amb',20.)),pp.ctypes.data_as(POINTER),float(duration),float(self.stop_requested),self._events_buffer,len(self._events_buffer),C.byref(count),self._scalars.ctypes.data_as(POINTER),self._die.ctypes.data_as(POINTER),self._counts.ctypes.data_as(POINTER))
        if status:raise RuntimeError('LINE_KERNEL_'+{-1:'NONFINITE_PHYSICS',-2:'EVENT_BUFFER_CAPACITY',-3:'BOUNDARY_CONVERGENCE',-4:'QUEUE_CAPACITY'}.get(status,'UNKNOWN'))
        for name,value in zip(SCALARS,self._scalars):setattr(self,name,bool(value) if name in BOOLEANS else int(value) if name in INTEGERS else float(value))
        self.die=[None if math.isnan(value) else float(value) for value in self._die]
        self.discharge.size=int(self._counts[0]);self.washer.size=int(self._counts[1])
        if count.value:
            data=np.frombuffer(self._events_buffer,dtype=np.float64,count=count.value*3).reshape(count.value,3)
            for array,column,dtype in ((self.events.time,0,np.float64),(self.events.kind,1,np.int8),(self.events.count,2,np.int64)):
                array.frombytes(np.ascontiguousarray(data[:,column],dtype=dtype).tobytes())
        return xx
