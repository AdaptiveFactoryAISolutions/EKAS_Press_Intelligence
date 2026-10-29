"""Direct instruments and PLC counters; no engineering ledgers exported."""
from historiansim.tags import TagSpec

def plant_tags():
    rows=[('SIC-1500.PV','SPM',0,12,'pulse_speed','SI-1500'),('SIC-1500.SP','SPM',0,10,'status','SIC-1500.SP'),('SIC-1500.OP','%',0,100,'valve','SIC-1500.OP'),('SIC-1500.MODE','-',0,2,'status','SIC-1500.MODE')]
    analogue={'FI-LUBE-MAKEUP':('L/min',2,'flow'),'WI-STRAIGHTENER-LOAD':('kN',100,'pressure'),'ZI-STRAIGHTENER-GAP':('mm',5,'level'),'LI-LUBE':('L',100,'level'),'FI-MAKEUP':('L/min',30,'flow'),'TI-WASH':('degC',100,'temperature'),'PI-LUBE':('bar',10,'pressure'),'FI-LUBE':('L/min',10,'flow'),'FI-WASH':('L/min',200,'flow'),'PI-WASH':('bar',10,'pressure'),'LI-WASH':('L',3000,'level'),'DPI-WASH':('bar',5,'pressure'),'JI-WASH':('kW',10,'power'),'JI-HEATER':('kW',200,'power'),'JI-DRIVE':('kW',200,'power'),'II-DRIVE':('A',500,'power'),'LI-LOOP':('m',10,'level'),'WI-COIL':('kg',20000,'level'),'ZI-COIL':('m',5,'level'),'FI-REEL':('m/s',1,'flow'),'II-REEL':('A',30,'power'),'SI-STRAIGHTENER':('m/s',1,'flow'),'II-STRAIGHTENER':('A',50,'power'),'ZI-FEED-SHAFT':('mm',2000,'pulse_position'),'ZI-FEED-STRIP':('mm',2000,'pulse_position'),'ZI-RAM':('mm',1000,'pulse_position'),'WI-TOTAL':('kN',20000,'pressure'),'WI-SCRAP':('kg',100,'level'),'II-SCRAP':('A',100,'power'),'SI-WASH':('m/min',10,'flow')}
    for i in range(1,11):
        analogue[f'WI-STATION-{i:02}']=('kN',2000,'pressure');analogue[f'FI-LUBE-STATION-{i:02}']=('L/min',1,'flow')
    for i in range(1,5):analogue[f'WI-CORNER-{i}']=('kN',5000,'pressure')
    rows.extend((n,unit,-.1*hi,hi,inst,n) for n,(unit,hi,inst) in analogue.items())
    digital=['PHASE-1500','DI-FEED','DI-RUN','DI-BLOCKED','DI-PACKING','DI-REEL-READY','COUNT-COILS']+[f'DI-STATION-{i:02}' for i in range(1,11)]+['COUNT-'+x for x in ('STROKES','PRODUCED','PACKED','REJECTED','DISCHARGE','WASHER','PACK-QUEUE','CONTAINER','CONTAINERS')]
    rows.extend((n,'pieces' if n.startswith('COUNT') else '-',0,1e8 if n.startswith('COUNT') else 1,'status',n) for n in digital)
    rows.append(('CALC-FEED-ERROR','mm',-2000,2000,'calculated','CALC-FEED-ERROR'))
    return [TagSpec(n,n+' '+('DCS derived from acquired instruments' if inst=='calculated' else 'PLC derived' if inst=='status' else 'direct instrument'),unit,lo,hi,inst,role='CALC' if inst=='calculated' else n.rsplit('.',1)[1] if n.startswith('SIC') else 'IND',source=source,loop='SIC-1500' if n.startswith('SIC') else None) for n,unit,lo,hi,inst,source in rows]
def recompute_dcs_calculations(values,params=None):
    if 'ZI-FEED-SHAFT' in values and 'ZI-FEED-STRIP' in values:values['CALC-FEED-ERROR']=values['ZI-FEED-SHAFT']-values['ZI-FEED-STRIP']
