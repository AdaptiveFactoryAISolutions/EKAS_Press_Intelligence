"""P-27 native stamping press plant registration."""
from historiansim.faults.base import ControlFault
from historiansim.plants.base import BenignEvent,Plant
from .description import describe
from .faults import CATALOG
from .loops import plant_channels,plant_loops
from .model import StampingPress
from .tags import plant_tags,recompute_dcs_calculations
BENIGN_EVENTS={
 'speed_reduction':BenignEvent(kind='speed_reduction',duration_days=(.75,1.5),build=lambda bid,onset,end:ControlFault(id=bid,loop='SIC-271',action='setpoint',onset_s=onset,value=54.,end_s=end,label='planned production speed reduction'),note='Operator reduced the production speed setpoint.',why='The speed setpoint record explains the lower throughput and forming duty.'),
 'tool_changeover':BenignEvent(kind='tool_changeover',duration_days=(.75,1.5),build=lambda bid,onset,end:ControlFault(id=bid,loop='SIC-271',action='setpoint',onset_s=onset,value=0.,end_s=end,label='planned tooling changeover stop'),note='Operator stopped production for an identical-tool changeover.',why='The speed setpoint was deliberately set to zero. The interlocked clutch held the crank and production stopped. The original production setpoint was restored after the planned identical-tool replacement.')}
SCENARIOS={'stamping-press-rca':dict(recipe='rca-benchmark',description='P-27 stamping cell, 90 day historian extract.',cause_ids=['RC-A1','RC-B1','RC-C2','RC-A3','RC-B2','RC-D1','RC-C3','RC-B6','RC-D4'],severities=['moderate','obvious','moderate','subtle','moderate','moderate','obvious','moderate','subtle'],benign_kinds=list(BENIGN_EVENTS))}
PLANT=Plant(name='stamping_press',equipment='P-27',summary='Stamping cell with controlled drive, feeder, inventory, lubrication and cooling',unit_cls=StampingPress,tags=plant_tags,loops=plant_loops,channels=plant_channels,catalog=CATALOG,describe=describe,scenarios=SCENARIOS,recompute_calcs=recompute_dcs_calculations,benign_events=BENIGN_EVENTS,default_benign_kinds=tuple(BENIGN_EVENTS),hard_mode_withheld=('ZI-276','CALC-TRAVEL-GAP','CALC-SUPPLY','CALC-CONSUMPTION','TI-272','WI-272','ZI-273','FI-274','JI-272','AI-271','AI-272','EI-271','FI-273','QI-272','FI-275','PI-273','LI-272','SI-272','ZI-272','FI-272','TI-273','DPI-271','PI-271'),mass_balance=None)
