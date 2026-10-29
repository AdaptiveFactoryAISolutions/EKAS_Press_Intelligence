"""Private symptom-first physical root-cause catalog."""
from historiansim.faults.base import ProcessFault,DisturbanceFault,InstrumentFault,ControlFault,Step,Linear
from historiansim.faults.catalog import Evidence,FaultCatalog,RootCause,SymptomClass
DAY=86400.
SYMPTOMS={
 'S1':SymptomClass('S1','Drive demand increase','SIC-271.OP','Load rises while mean speed is held.','slow'),
 'S2':SymptomClass('S2','Abnormal strip transport','FDC-271.OP','Feeder or decoiler demand, progression or ready status departs from normal.','cycling'),
 'S3':SymptomClass('S3','Pump demand increase','PIC-272.OP','Lubrication demand rises while pressure is held.','slow'),
 'S4':SymptomClass('S4','Dimensional drift','QI-271','Product dimensions move from the design target.','slow')}
# id, symptom, name, component, physical handle, magnitude at moderate, diagnostic tag, direction
ROWS=[
 ('RC-A1','S1','Main-bearing drag','main bearing','bearing_drag',-.20,'TI-272','rises'),
 ('RC-A2','S1','Oil viscosity increase','oil charge','viscosity',-.30,'PIC-272.OP','falls'),
 ('RC-A3','S1','Strip-strength rise','stock strength','d:strength',.08,'AI-271','rises'),
 ('RC-A4','S1','Die-insert wear','die insert','die_wear',-.20,'WI-271','rises'),
 ('RC-A5','S1','Die-guide misalignment','die guide','guide_drag',-.20,'WI-272','rises'),
 ('RC-B1','S2','Encoder gain failure','feeder encoder','i:FDC-271.PV',.03,'ZI-272','falls'),
 ('RC-B2','S2','Feed-roll traction loss','feed roll','traction',.20,'FDC-271.OP','rises'),
 ('RC-B3','S2','Coupling backlash','feed coupling','o:backlash',4.,'ZI-273','rises'),
 ('RC-B4','S2','Strip-guide obstruction','strip guide','o:obstruction',5.,'PI-271','rises'),
 ('RC-B5','S2','Decoiler brake drag','decoiler brake','brake_drag',-.30,'LIC-271.OP','rises'),
 ('RC-B6','S2','Feeder controller manual','feeder control station','c:manual',.45,'FDC-271.MODE','falls'),
 ('RC-C1','S3','Hose leakage','lubrication hose','o:leakage',.5,'FI-274','rises'),
 ('RC-C2','S3','Pump volumetric wear','pump element','pump_efficiency',.15,'JI-272','rises'),
 ('RC-C3','S3','Filter blockage','lubrication filter','filter_resistance',-.8,'DPI-271','rises'),
 ('RC-C4','S3','Supply-voltage loss','power supply','d:voltage',-.10,'EI-271','falls'),
 ('RC-D1','S4','Die-cooling loss','cooling supply','d:cooling',-.25,'TIC-271.OP','rises'),
 ('RC-D2','S4','Stock-thickness variation','stock thickness','d:thickness',.025,'AI-272','rises'),
 ('RC-D3','S4','Film-delivery failure','film delivery','film_delivery',.30,'FI-273','falls'),
 ('RC-D4','S4','Inspection-gauge gain failure','inspection gauge','i:QI-271',.002,'QI-271','rises')]

def builder(row):
    cid,symptom,name,component,handle,mag,tag,direction=row
    def build(onset,severity):
        factor={'subtle':.5,'moderate':1.,'obvious':1.5}[severity]
        profile=Step() if symptom=='S2' or handle.startswith('i:') else Linear(ramp_s=DAY)
        if handle.startswith('i:'):
            return InstrumentFault(id=cid,tag=handle[2:],magnitude=mag*factor,onset_s=onset,profile=profile,mode='scale',label=name)
        if handle.startswith('c:'):
            return ControlFault(id=cid,loop='FDC-271',action='manual',onset_s=onset,value=.5-(.5-mag)*factor,label=name)
        if handle.startswith('d:'):
            return DisturbanceFault(id=cid,channel=handle[2:],magnitude=mag*factor,onset_s=onset,profile=profile,mode='scale',label=name)
        return ProcessFault(id=cid,param=handle.removeprefix('o:'),magnitude=mag*factor,onset_s=onset,profile=profile,mode='offset' if handle.startswith('o:') else 'scale',label=name)
    return build

# Predicted physical signatures. Native measured sweeps remain the authority.
EVIDENCE={
 'RC-A1':[('SIC-271.OP','rises'),('TI-272','rises'),('PIC-272.OP','rises'),('AI-271','flat'),('WI-271','flat'),('WI-272','flat')],
 'RC-A2':[('SIC-271.OP','rises'),('TI-272','rises'),('PIC-272.OP','falls'),('AI-271','flat'),('WI-271','flat'),('WI-272','flat')],
 'RC-A3':[('SIC-271.OP','rises'),('AI-271','rises'),('WI-271','rises'),('WI-272','flat'),('TI-272','flat')],
 'RC-A4':[('SIC-271.OP','rises'),('AI-271','flat'),('WI-271','rises'),('WI-272','flat'),('TI-272','flat')],
 'RC-A5':[('SIC-271.OP','rises'),('AI-271','flat'),('WI-271','rises'),('WI-272','rises'),('TI-272','flat')],
 'RC-B1':[('CALC-TRAVEL-GAP','flat'),('ZI-272','falls'),('FDC-271.OP','falls'),('ZI-273','flat'),('PI-271','flat'),('FDC-271.MODE','flat')],
 'RC-B2':[('CALC-TRAVEL-GAP','rises'),('ZI-272','falls'),('ZI-273','flat'),('PI-271','flat'),('FDC-271.MODE','flat'),('LIC-271.OP','falls')],
 'RC-B3':[('CALC-TRAVEL-GAP','rises'),('ZI-272','falls'),('ZI-273','rises'),('PI-271','flat'),('FDC-271.MODE','flat'),('LIC-271.OP','falls')],
 'RC-B4':[('CALC-TRAVEL-GAP','rises'),('ZI-272','falls'),('ZI-273','flat'),('PI-271','rises'),('FDC-271.MODE','flat'),('LIC-271.OP','falls')],
 'RC-B5':[('LIC-271.OP','rises'),('PI-271','rises'),('FDC-271.OP','flat'),('ZI-273','flat'),('FDC-271.MODE','flat')],
 'RC-B6':[('FDC-271.MODE','falls'),('ZI-272','falls'),('FDC-271.OP','falls'),('ZI-273','flat'),('PI-271','flat')],
 'RC-C1':[('PIC-272.OP','rises'),('FI-274','rises'),('DPI-271','rises'),('EI-271','flat')],
 'RC-C2':[('PIC-272.OP','rises'),('JI-272','rises'),('FI-274','flat'),('DPI-271','flat'),('EI-271','flat')],
 'RC-C3':[('PIC-272.OP','rises'),('DPI-271','rises'),('FI-274','flat'),('EI-271','flat')],
 'RC-C4':[('PIC-272.OP','rises'),('EI-271','falls'),('FI-274','flat'),('DPI-271','flat')],
 'RC-D1':[('TIC-271.OP','rises'),('AI-272','flat'),('FI-273','flat'),('QI-272','flat')],
 'RC-D2':[('AI-272','rises'),('QI-271','rises'),('QI-272','rises'),('FI-273','flat')],
 'RC-D3':[('FI-273','falls'),('TIC-271.OP','rises'),('AI-272','flat')],
 'RC-D4':[('QI-271','rises'),('QI-272','flat'),('TIC-271.OP','flat'),('AI-272','flat'),('FI-273','flat')]}
# Controlled-variable evidence makes the masking promise measurable.
for _cid in ('RC-A1','RC-A2','RC-A3','RC-A4','RC-A5'):
    EVIDENCE[_cid].append(('SIC-271.PV','flat'))
for _cid in ('RC-C1','RC-C2','RC-C3','RC-C4'):
    EVIDENCE[_cid].append(('PIC-272.PV','flat'))
EVIDENCE['RC-D1'].append(('TIC-271.PV','flat'))
causes=[]
for row in ROWS:
    cid,symptom,name,component,handle,mag,tag,direction=row
    competitors=tuple(r[0] for r in ROWS if r[1]==symptom and r[0]!=cid)
    evidence=tuple(Evidence(etag,expectation,'Compare the controlled value and independent load, material or supply reference.',rules_in=(cid,) if expectation!='flat' else (),rules_out=competitors) for etag,expectation in EVIDENCE[cid])
    causes.append(RootCause(id=cid,name=name,label=name,symptom=symptom,layer=7 if handle.startswith('i:') else 3 if handle.startswith('c:') else 4 if handle.startswith('d:') else 6,
        mechanism=name.lower(),component=component,build=builder(row),evidence=evidence,
        grade='Medium',walkthrough='Compare the controlled value, controller demand and independent physical references. '+name+' changes the relationship at '+tag+'.',competitors=competitors))
CATALOG=FaultCatalog(SYMPTOMS,causes)
