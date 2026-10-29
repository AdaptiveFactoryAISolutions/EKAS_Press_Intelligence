"""Native envelope control loops and named disturbance channels."""
from historiansim.config.schema import LoopConfig, ChannelConfig
from .model import StampingPress
DESIGN_D=dict(T_amb=20.,T_cw=29.,strength=1.,thickness=.0012,voltage=1.,cooling=1.)
DESIGN_TARGETS={'SI-271':60.,'ZI-271':100.,'LI-271':1.,'PI-272':5.,'TI-271':50.}
def design_point():
    unit=StampingPress(); u=unit.steady_inputs(DESIGN_TARGETS,DESIGN_D,unit.params)
    x=unit.steady_state(u,DESIGN_D,unit.params)
    return unit,u,x,unit.signals(0,x,u,DESIGN_D,unit.params)
def plant_loops():
    return [LoopConfig(name=n,pv_source=pv,mv_tag=mv,kc=kc,ti=ti,sp=DESIGN_TARGETS[pv],action=action)
            for n,pv,mv,kc,ti,action in [('SIC-271','SI-271','DRIVE-271',.003,120.,'reverse'),
            ('FDC-271','ZI-271','FEED-271',.003,60.,'reverse'),('LIC-271','LI-271','DECOIL-271',.1,300.,'reverse'),
            ('PIC-272','PI-272','PUMP-272',.03,120.,'reverse'),('TIC-271','TI-271','COOL-271',.03,600.,'direct')]]
def plant_channels():
    return {name:ChannelConfig(mean=mean,units=units,description=description,sigma=sigma,tau_s=1800.)
        for name,mean,units,description,sigma in [('T_cw',29.,'degC','Cooling supply temperature',.15),
        ('strength',1.,'-','Incoming stock strength ratio',.003),('thickness',.0012,'m','Incoming strip thickness',.000001),
        ('voltage',1.,'-','Electrical supply fraction',.002),('cooling',1.,'-','Available coolant supply fraction',.003)]}
