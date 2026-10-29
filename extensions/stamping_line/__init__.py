"""Native auto-discovered connected stamping line plant."""
from historiansim.plants.base import Plant
from .model import StampingLine
from .tags import plant_tags,recompute_dcs_calculations
from .loops import plant_loops,plant_channels
from .faults import CATALOG,ROWS
from .description import describe
# Register the same declared digital encoder acquisition classes as the press.
from . import instruments
PLANT=Plant(name='stamping_line',equipment='LINE-1500',summary='Connected continuous-strip ten-station stamping, wash and manual packing line',unit_cls=StampingLine,tags=plant_tags,loops=plant_loops,channels=plant_channels,catalog=CATALOG,describe=describe,scenarios={'stamping-line-practice':dict(description='Generic continuous-strip line; eight-cause practice scenario using native duration profiles, not an RCA benchmark. Guided setup separately defaults to a 60-minute practice run with one selected case.',n_faults=8,n_benign=0,n_concurrent=0,background_fouling=False,cause_ids=[row[0] for row in ROWS],severities=['obvious']*8,benign_kinds=[])},recompute_calcs=recompute_dcs_calculations,benign_events={},default_benign_kinds=(),hard_mode_withheld=(),mass_balance=None)
