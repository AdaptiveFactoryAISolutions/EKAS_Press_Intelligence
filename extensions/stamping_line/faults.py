"""Native parameter degradation and acquisition fault specifications."""
from historiansim.faults.base import ProcessFault,InstrumentFault,Step
from historiansim.faults.catalog import Evidence,FaultCatalog,RootCause,SymptomClass
ROWS=[('LINE-FEED-SLIP','Feed roll slip','feed_traction',.2,'CALC-FEED-ERROR'),('LINE-SUPPLY-STARVATION','Reel supply starvation','supply_factor',1.,'FI-REEL'),('LINE-LUBE-RESTRICTION','Lubrication restriction','lube_factor',.8,'PI-LUBE'),('LINE-STATION-SENSOR','Station presence sensor failure','i:DI-STATION-05',1.,'DI-STATION-05'),('LINE-SCRAP-BLOCKAGE','Scrap conveyor blockage','scrap_factor',1.,'WI-SCRAP'),('LINE-WASHER-COLD','Washer heater unavailable','heater_factor',1.,'TI-WASH'),('LINE-WASHER-LOW-FLOW','Washer spray restriction','spray_factor',.8,'FI-WASH'),('LINE-PACKING-SLOW','Packing staffing slowdown','packing_factor',.8,'COUNT-PACK-QUEUE')]
def build(row):
    cid,label,param,mag,tag=row
    def make(onset,severity):
        amount=min(1.,mag*{'subtle':.5,'moderate':1.,'obvious':1.25}[severity])
        if param.startswith('i:'):return InstrumentFault(id=cid,tag=tag,magnitude=-amount,onset_s=onset,profile=Step(),mode='scale',label=label)
        return ProcessFault(id=cid,param=param,magnitude=amount,onset_s=onset,profile=Step(),mode='scale',label=label)
    return make
# Every candidate is evaluated on the same measured union. Cross-effects follow
# actual line interlocks/heat loading, rather than missing tags being treated flat.
# Washer WI-SCRAP 'erratic' is a secondary coarse-acquisition phase shift: changed
# pack/container event timing propagates through inventory/reel cycle timing.
# It does not establish a new upstream scrap-removal fault or a fixed direction.
EVIDENCE_TAGS=('CALC-FEED-ERROR','FI-REEL','PI-LUBE','DI-STATION-05','WI-SCRAP','TI-WASH','FI-WASH','COUNT-PACK-QUEUE')
EXPECTATIONS={
 'LINE-FEED-SLIP':('rises','falls','flat','flat','falls','rises','flat','falls'),
 'LINE-SUPPLY-STARVATION':('flat','falls','flat','flat','falls','rises','flat','falls'),
 'LINE-LUBE-RESTRICTION':('flat','falls','falls','flat','falls','rises','flat','falls'),
 'LINE-STATION-SENSOR':('flat','flat','flat','falls','flat','flat','flat','flat'),
 'LINE-SCRAP-BLOCKAGE':('flat','falls','flat','flat','rises','rises','flat','falls'),
 'LINE-WASHER-COLD':('flat','flat','flat','flat','erratic','falls','flat','falls'),
 'LINE-WASHER-LOW-FLOW':('flat','flat','flat','flat','erratic','flat','falls','falls'),
 'LINE-PACKING-SLOW':('flat','falls','flat','flat','falls','rises','flat','rises')}
CATALOG=FaultCatalog({'LINE':SymptomClass('LINE','Line interruption or quality loss','DI-RUN','Connected material handling or process service departs from normal.','cycling')},[RootCause(id=r[0],name=r[1],label=r[1],symptom='LINE',layer=7 if r[2].startswith('i:') else 6,mechanism=r[1],component=r[2],build=build(r),evidence=tuple(Evidence(tag,expectation,'Secondary phase/aliasing excursion in coarse scrap-inventory acquisition after changed packing/container event timing; not independent evidence of physical scrap-removal degradation. Use primary washer temperature/flow and the full causal timeline.' if tag=='WI-SCRAP' and r[0] in ('LINE-WASHER-COLD','LINE-WASHER-LOW-FLOW') else 'Compare acquired instruments across the complete shared evidence set; interlocks and finite queues determine causal order.',rules_in=tuple(cid for cid,signature in EXPECTATIONS.items() if signature[EVIDENCE_TAGS.index(tag)]==expectation) if expectation!='flat' else (),rules_out=()) for tag,expectation in zip(EVIDENCE_TAGS,EXPECTATIONS[r[0]])),grade='Medium',walkthrough='Follow material inventory and the earliest changed instrument; downstream faults propagate through finite queues.',competitors=tuple(x[0] for x in ROWS if x!=r)) for r in ROWS])
