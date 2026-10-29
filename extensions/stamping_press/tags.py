"""Native tag definitions. Instrument dynamics follow native class settings."""
from historiansim.tags import TagSpec
from .loops import plant_loops
from . import instruments
RANGES={'SI-271':('SPM',-5,150,'pulse_speed'),'ZI-271':('mm',0,250,'pulse_position'),
        'LI-271':('m',0,2.5,'level'),'PI-272':('bar',0,12,'pressure'),'TI-271':('degC',0,120,'temperature')}
INDICATORS=[('ZI-276','mm',0,250,'pulse_position'),('CALC-TRAVEL-GAP','mm',-25,75,'calculated'),('FI-275','m/s',0,.3,'flow'),('SI-272','SPM',-5,150,'pulse_speed'),('ZI-272','mm',0,250,'pulse_position'),('ZI-274','mm',-5,250,'pulse_position'),('ZI-275','mm',-5,250,'pulse_position'),('LI-272','m',0,2.5,'level'),
 ('PI-273','bar',0,12,'pressure'),('TI-272','degC',0,100,'temperature_slow'),('JI-271','kW',0,5,'power'),
 ('WI-271','kN',0,250,'pressure'),('WI-273','kN',-5,250,'pressure'),('FI-271','L/min',0,12,'flow'),('DPI-271','bar',0,3,'pressure'),
 ('PI-271','N',0,300,'pressure'),('FI-272','L/min',0,15,'flow'),('TI-273','degC',0,80,'temperature'),
 ('QI-271','mm',95,105,'optical_gauge'),('QI-272','mm',95,105,'optical_gauge'),('AI-271','ratio',.5,2,'analyzer'),
 ('AI-272','mm',0,3,'analyzer'),('EI-271','V',0,600,'power'),('FI-273','L/min',0,.3,'flow'),
 ('DI-271','-',0,1,'status'),('DI-272','-',0,1,'status'),('PHASE-271','rev',0,1,'status'),
 ('COUNT-271','pieces',0,1e8,'status'),('COUNT-272','pieces',0,1e8,'status'),('COUNT-273','pieces',0,1e8,'status'),('COUNT-274','pieces',0,1e8,'status'),
 ('CALC-WORK','J',0,3000,'calculated'),('CALC-SUPPLY','m/s',0,.3,'calculated'),
 ('CALC-CONSUMPTION','m/s',0,.3,'calculated'),('CALC-MATERIAL-RESIDUAL','kg',-1,1,'calculated'),
 ('CALC-ENERGY-RESIDUAL','J',-100,100,'calculated'),
 ('WI-272','kN',-100,100,'pressure'),('ZI-273','mm',-10,20,'level'),('FI-274','L/min',-.25,5,'flow'),('JI-272','kW',0,1,'power')]
def plant_tags():
    out=[]
    for loop in plant_loops():
        units,lo,hi,instrument=RANGES[loop.pv_source]
        for suffix,unit,a,b,inst,source in [('PV',units,lo,hi,instrument,loop.pv_source),
            ('SP',units,lo,hi,'status',loop.name+'.SP'),('OP','%',0,100,'valve',loop.name+'.OP'),
            ('MODE','-',0,2,'status',loop.name+'.MODE')]:
            out.append(TagSpec(loop.name+'.'+suffix,loop.name+' '+suffix,unit,a,b,inst,suffix,source=source,loop=loop.name))
    for name,units,lo,hi,instrument in INDICATORS:
        if name in ('CALC-MATERIAL-RESIDUAL','CALC-ENERGY-RESIDUAL'): continue
        out.append(TagSpec(name,name+' measured observation',units,lo,hi,instrument,role='CALC' if instrument=='calculated' else 'IND',source=name,node='NODE-B' if name.endswith('272') else 'NODE-A'))
    return out

def recompute_dcs_calculations(values,params=None):
    # These are DCS calculations from the actual instrument observations.
    # Neither true parameters nor a fault label is used to reconstruct a tag.
    if 'WI-271' in values: values['CALC-WORK']=values['WI-271']*1000*(params or {}).get('forming_travel',.02)/2
    if 'ZI-276' in values and 'ZI-272' in values: values['CALC-TRAVEL-GAP']=values['ZI-276']-values['ZI-272']
    if 'FI-275' in values: values['CALC-SUPPLY']=values['FI-275'].copy()
    if all(tag in values for tag in ('ZI-272','SIC-271.PV','DI-271')):
        values['CALC-CONSUMPTION']=values['ZI-272']*.001*values['SIC-271.PV']/60.*values['DI-271']
    for name in ('CALC-MATERIAL-RESIDUAL','CALC-ENERGY-RESIDUAL'):
        values.pop(name,None)
