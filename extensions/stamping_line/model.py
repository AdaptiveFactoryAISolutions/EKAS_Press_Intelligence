"""Generic SI connected line: continuous thermal envelope plus discrete material clock."""
import math
import numpy as np
from historiansim.plants.unit import UnitModel

class StampingLine(UnitModel):
    name='stamping_line'
    state_names=('speed_spm','washer_temperature_c','lube_pressure_bar','washer_water_l','lube_reservoir_l')
    mv_names=('DRIVE-1500',)
    disturbance_names=('T_amb',)
    stiction_params={}
    @staticmethod
    def default_params():
        return dict(capacity_n=1500*9806.65,speed_spm=8.,stations=10.,parts_per_stroke=1.,width_mm=600.,thickness_mm=1.5,progression_mm=800.,density_kg_m3=7850.,coil_mass_kg=10000.,loop_capacity_m=6.,loop_initial_m=3.,feeder_speed_m_s=2.,feed_window_s=2.,straightener_speed_m_s=.25,forming_force_n=1000*9806.65,work_per_stroke_j=100000.,motor_kw=110.,voltage_v=400.,efficiency=.9,power_factor=.85,stroke_mm=400.,lube_pressure_bar=5.,lube_flow_l_min=2.,washer_temperature_c=60.,washer_volume_l=2000.,heater_kw=90.,spray_flow_l_min=100.,spray_pressure_bar=3.,pump_kw=4.,washer_length_m=3.,washer_speed_m_min=4.,part_spacing_m=.4,buffer_parts=20.,packers=2.,packing_rate_per_min=6.,container_parts=50.,container_change_s=30.,feed_traction=1.,supply_factor=1.,lube_factor=1.,scrap_factor=1.,heater_factor=1.,spray_factor=1.,packing_factor=1.,run_enable=1.,trim_fraction=.2,scrap_route_code=3.,coil_change_s=120.,integration_step_s=.1,compiled_cycles=1.)
    @staticmethod
    def forming_demand(p):
        scale=p['width_mm']/600*p['thickness_mm']/1.5
        return p['forming_force_n']*scale/max(p['lube_factor'],.2),p['work_per_stroke_j']*scale*p['progression_mm']/800/max(p['lube_factor'],.2)
    def validate_params(self,p):
        if p['compiled_cycles'] not in (0.,1.):raise ValueError('compiled_cycles must be 0 or 1')
        if not 0<p['integration_step_s']<=.1:raise ValueError('integration_step_s must be above 0 and no greater than 0.1s')
        if not 0<p['speed_spm']<=10 or p['stations']!=10:raise ValueError('ten stations and speed above zero through 10 SPM required')
        if any(not math.isfinite(v) or v<0 for v in p.values()):raise ValueError('finite nonnegative parameters required')
        if p['forming_force_n']>p['capacity_n']:raise ValueError('load exceeds rating')
        if p['progression_mm']/1000>p['feeder_speed_m_s']*p['feed_window_s']:raise ValueError('feed window insufficient')
    def steady_inputs(self,targets,d,p):return {'DRIVE-1500':targets.get('SI-1500',p['speed_spm'])/10.}
    def steady_state(self,u,d,p):return np.array([10*u['DRIVE-1500'],p['washer_temperature_c'],p['lube_pressure_bar'],p['washer_volume_l'],50.],dtype=float)
    def thermal(self,x,d,p):
        ambient=d.get('T_amb',20.)
        loss=200*(x[1]-ambient)
        spray=p['spray_flow_l_min']*p['spray_factor'] if x[3]>100 else 0.
        evaporation=.005+spray/60*.001
        makeup=min(.25,max(0.,p['washer_volume_l']-x[3])*.1+evaporation)
        heater=min(p['heater_kw']*1000*p['heater_factor'],max(0.,(p['washer_temperature_c']-x[1])*10000+loss+evaporation*2260000+makeup*4180*(x[1]-ambient))) if x[3]>100 else 0.
        return heater,loss,evaporation,makeup,spray
    def derivatives(self,t,x,u,d,p):
        heat,loss,evap,makeup,spray=self.thermal(x,d,p)
        ambient=d.get('T_amb',20.)
        lube_flow=p['lube_flow_l_min']*p['lube_factor']*p.get('_lube_duty',0.) if x[4]>1 else 0.
        return np.array([(min(10.,10*u['DRIVE-1500'])-x[0])/2.,(heat-loss+makeup*4180*(ambient-x[1])-evap*2260000)/(max(x[3],1.)*4180.),(p['lube_pressure_bar']*p['lube_factor']*(x[4]>1)-x[2])/2.,makeup-evap,-lube_flow/60*.1+min(.02,max(0.,50.-x[4])*.01)])
    def signals(self,t,x,u,d,p):
        heater,loss,evap,makeup,spray=self.thermal(x,d,p)
        power=p['work_per_stroke_j']*max(x[0],0)/60/p['efficiency']/1000+5.
        return {'SI-1500':x[0],'TI-WASH':x[1],'PI-LUBE':x[2],'LI-LUBE':x[4],'FI-LUBE-MAKEUP':min(.02,max(0.,50.-x[4])*.01)*60,'FI-LUBE':p['lube_flow_l_min']*p['lube_factor']*p.get('_lube_duty',0.),'FI-WASH':spray,'PI-WASH':p['spray_pressure_bar']*p['spray_factor']**2,'LI-WASH':x[3],'FI-MAKEUP':makeup*60,'DPI-WASH':.2/max(p['spray_factor'],.1),'JI-WASH':p['pump_kw']*p['spray_factor'],'JI-HEATER':heater/1000,'JI-DRIVE':power,'II-DRIVE':power*1000/(math.sqrt(3)*p['voltage_v']*p['power_factor']),'WI-TOTAL':p['forming_force_n']/1000}
    def cycle_event_source(self,x,u,d,p):
        if p['compiled_cycles']:
            from .compiled_backend import CompiledLineCycleEvents
            return CompiledLineCycleEvents(self,x,u,d,p)
        from .cycles import LineCycleEvents
        return LineCycleEvents(self,x,u,d,p)
