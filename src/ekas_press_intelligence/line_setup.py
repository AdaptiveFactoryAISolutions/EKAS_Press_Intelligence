"""Versioned beginner settings, engineering feasibility and native configuration.

All defaults are synthetic engineering assumptions, never a calibrated customer
recipe. This module imports no native runtime until resolving a run.
"""
from __future__ import annotations
import hashlib
import json
import math
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

PRESET_ID='generic-1500t-continuous-strip'
PRESET_VERSION=1
FORCE={'metric_tonne_force':9806.65,'short_ton_force':8896.443230521}
CASES={'healthy':None,'feed_slip':'LINE-FEED-SLIP','supply_starvation':'LINE-SUPPLY-STARVATION',
       'lube_restriction':'LINE-LUBE-RESTRICTION','station_sensor':'LINE-STATION-SENSOR',
       'scrap_blockage':'LINE-SCRAP-BLOCKAGE','washer_cold':'LINE-WASHER-COLD',
       'washer_low_flow':'LINE-WASHER-LOW-FLOW','packing_slow':'LINE-PACKING-SLOW'}
STEPS=[{'number':i+1,'title':title,'description':description} for i,(title,description) in enumerate([
 ('Choose your line','A complete synthetic training line, already filled in.'),
 ('Capacity and speed','Check force units and production rate.'),
 ('Material and feeding','Confirm the strip and its route to the die.'),
 ('Die, lubrication and scrap','Ten connected stations with independent scrap removal.'),
 ('Wash and pack','Hot-water spray washing followed by manual packing.'),
 ('Choose your test','Start healthy, then introduce one known problem.'),
 ('Choose where to view results','Use the built-in workspace; external EKAS needs a provisioned adapter.'),
 ('Review and run','Check all settings before creating an immutable run.')])]


def setting(default,step,label,unit,help,tooltip=None,**bounds):
    return Field(default, json_schema_extra={'step':step,'label':label,'unit':unit,'help':help,
                                           'tooltip':tooltip or help},**bounds)


class LineSetup(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    capacity_tons:float=setting(1500,2,'Press rated capacity','selected tons-force','Fixed physical capacity; changing force units converts this displayed number.',ge=1000,le=1800)
    force_unit:Literal['metric_tonne_force','short_ton_force']=setting('metric_tonne_force',2,'Force unit','','Generic default: metric tonnes-force. Check the rating plate for a real machine.')
    speed_spm:float=setting(8,2,'Operating speed','strokes/minute','Maximum 10 strokes/minute = 600 strokes/hour.','One stroke is a complete press cycle. Ten stations do not multiply finished parts by ten.',gt=0,le=10)
    stations:StrictInt=setting(10,2,'Die stations','stations','This preset uses ten continuous-strip stations.',ge=10,le=10)
    parts_per_stroke:StrictInt=setting(1,2,'Finished parts per production stroke','parts','One-out tooling is the generic default. Output begins after the die fills.',ge=1,le=4)
    width_mm:float=setting(600,3,'Strip width','mm','Width of incoming steel strip.',ge=50,le=1500)
    thickness_mm:float=setting(1.5,3,'Strip thickness','mm','Generic steel strip thickness.',ge=.3,le=6)
    density_kg_m3:float=setting(7850,3,'Material density','kg/m³','Generic steel density; used for material accounting.',ge=7000,le=8100)
    progression_mm:float=setting(800,3,'Progression per stroke','mm','Distance the continuous strip advances each cycle.',ge=50,le=2000)
    coil_mass_kg:float=setting(10000,3,'Loaded coil mass','kg','Available initial stock. Exhausted stock must stop production.',ge=100,le=30000)
    loop_capacity_m:float=setting(6,3,'Loop-pit slack capacity','m','Maximum usable strip stored in the loop pit.',ge=1,le=30)
    loop_initial_m:float=setting(3,3,'Starting slack','m','Initial strip available between reel and straightener.',gt=0,le=30)
    feeder_speed_m_s:float=setting(2,3,'Maximum feeder travel speed','m/s','Must be sufficient for the selected progression and feed window.',gt=0,le=5)
    feed_window_s:float=setting(2,3,'Permitted feed window','seconds','Reserved portion of each cycle for advancing strip.',gt=0,le=5)
    straightener_speed_m_s:float=setting(.25,3,'Straightener delivery capacity','m/s','Maximum material delivery speed.',gt=0,le=2)
    forming_force_tons:float=setting(1000,4,'Reference die peak forming force','selected tons-force','Recipe reference: 600 mm wide, 1.5 mm thick steel. Actual demand scales with width and thickness.',gt=0,le=1800)
    work_per_stroke_j:float=setting(100000,4,'Reference forming work per stroke','joules','Recipe reference: 600 mm width, 1.5 mm thickness, 800 mm progression. Actual work scales with these dimensions.',gt=0,le=1000000)
    motor_kw:float=setting(110,4,'Main drive rated power','kW','Generic installed motor rating; consumption follows load.',gt=0,le=500)
    voltage_v:float=setting(400,4,'Electrical supply','volts','Used with efficiency and power factor to derive drive current.',ge=200,le=700)
    efficiency:float=setting(.9,4,'Drive efficiency','fraction','0.90 means 90 percent of input power reaches the modeled drive.',gt=.1,le=1)
    power_factor:float=setting(.85,4,'Electrical power factor','fraction','Generic three-phase electrical assumption.',gt=.1,le=1)
    stroke_mm:float=setting(400,4,'Press stroke','mm','Declared envelope stroke; not a certified crank-motion model.',ge=100,le=1200)
    lube_pressure_bar:float=setting(5,4,'Lubrication pressure target','bar','Supply pressure for the in-die lubrication circuit.',ge=1,le=20)
    lube_flow_l_min:float=setting(2,4,'Lubrication delivery target','L/min','Total nominal delivery across the die zones.',gt=0,le=20)
    scrap_route:Literal['combined','shaker','conveyor']=setting('combined',4,'Offal removal','','Combined routes use shaker chutes and a motorized conveyor.')
    washer_temperature_c:float=setting(60,5,'Washer temperature target','°C','Hot-water spray recipe; heating responds to heat loss and parts.',ge=40,le=85)
    washer_volume_l:float=setting(2000,5,'Washer tank working volume','litres','Generic recirculating wash-water inventory.',ge=100,le=10000)
    heater_kw:float=setting(90,5,'Washer heater capacity','kW','Maximum installed heating power; actual duty varies.',gt=0,le=300)
    spray_flow_l_min:float=setting(100,5,'Spray circulation flow','L/min','Recirculating spray flow, not fresh-water consumption.',gt=0,le=500)
    spray_pressure_bar:float=setting(3,5,'Spray pressure target','bar','Pressure supplied to the wash spray header.',gt=0,le=10)
    pump_kw:float=setting(4,5,'Washer pump rated power','kW','Pump input must cover hydraulic duty and losses.',gt=0,le=30)
    washer_length_m:float=setting(3,5,'Active wash-zone length','m','Together with conveyor speed, determines washing time.',gt=0,le=20)
    washer_speed_m_min:float=setting(4,5,'Washer conveyor speed','m/min','Generic belt speed; affects capacity and residence time.',gt=0,le=20)
    part_spacing_m:float=setting(.4,5,'Part spacing on washer belt','m','Minimum modeled distance between arriving parts.',gt=0,le=2)
    buffer_parts:StrictInt=setting(20,5,'Capacity of each part buffer','parts','Finite accumulation before washing and manual packing.',ge=1,le=1000)
    packers:StrictInt=setting(2,5,'Packing operators','people','Manual packing; this is not an automatic packer.',ge=1,le=10)
    packing_rate_per_min:float=setting(6,5,'Packing rate per operator','parts/minute','Nominal manual rate; worker availability and changeovers affect output.',gt=0,le=30)
    container_parts:StrictInt=setting(50,5,'Customer container capacity','parts','Completing a container starts a modeled changeover.',ge=1,le=1000)
    container_change_s:float=setting(30,5,'Container change time','seconds','Time before packing resumes into an empty container.',ge=0,le=600)
    duration_minutes:float=setting(60,6,'Practice run length','minutes','Practice only. Native qualification requires its own approved campaign.',ge=10,le=1440)
    seed:StrictInt=setting(7,6,'Repeat number','','Same settings, source and repeat number reproduce a case.',ge=0,le=2147483647)
    test_case:Literal['healthy','feed_slip','supply_starvation','lube_restriction','station_sensor','scrap_blockage','washer_cold','washer_low_flow','packing_slow']=setting('healthy',6,'Training case','','Start with a healthy line before investigating one introduced fault.')
    fault_start_minutes:float=setting(10,6,'Fault-free starting period','minutes','For fault cases, the native scheduler places the fault after this clean baseline.',ge=1,le=1200)
    allow_bottleneck:Literal['no','yes']=setting('no',6,'Deliberate throughput bottleneck','','Choose Yes only when intentionally testing washer or packing capacity below press output.')

    @model_validator(mode='before')
    @classmethod
    def no_boolean_numbers(cls,value):
        if isinstance(value,dict):
            for key,item in value.items():
                if isinstance(item,bool):raise ValueError(key+': enter a number or a listed choice, not true/false')
        return value

    @model_validator(mode='after')
    def feasible(self):
        if not math.isclose(self.capacity_tons*FORCE[self.force_unit],1500*FORCE['metric_tonne_force'],rel_tol=1e-8):raise ValueError('capacity_tons: this preset has fixed physical capacity; convert its value when changing force units')
        if self.loop_initial_m>self.loop_capacity_m:raise ValueError('loop_initial_m: starting slack exceeds loop capacity')
        if self.buffer_parts<self.parts_per_stroke:raise ValueError('buffer_parts: each buffer must hold at least one complete output batch')
        if self.loop_initial_m<self.progression_mm/1000:raise ValueError('loop_initial_m: provide at least one progression of starting slack')
        if self.progression_mm/1000>self.feeder_speed_m_s*self.feed_window_s*.8:raise ValueError('feed_window_s: insufficient feed time including 20 percent acceleration margin')
        if self.feed_window_s>60/self.speed_spm*.5:raise ValueError('feed_window_s: feeding must fit within half the press cycle')
        if self.progression_mm/1000*self.speed_spm/60>self.straightener_speed_m_s:raise ValueError('straightener_speed_m_s: capacity cannot support the selected strip consumption')
        material_scale=(self.width_mm/600)*(self.thickness_mm/1.5)
        resolved_force=self.forming_force_tons*FORCE[self.force_unit]*material_scale
        resolved_work=self.work_per_stroke_j*material_scale*self.progression_mm/800
        if resolved_force>self.capacity_tons*FORCE[self.force_unit]:raise ValueError('forming_force_tons: material-adjusted forming demand exceeds rated force; reduce the reference load or material dimensions')
        if resolved_work>resolved_force*self.stroke_mm/1000*.5:raise ValueError('work_per_stroke_j: material-adjusted energy exceeds the declared force/travel envelope')
        if resolved_work*self.speed_spm/60>self.motor_kw*1000*self.efficiency*.8:raise ValueError('motor_kw: insufficient drive power for material-adjusted work including 20 percent recovery margin')
        if self.spray_flow_l_min/60000*self.spray_pressure_bar*1e5>self.pump_kw*1000*.65:raise ValueError('pump_kw: pump cannot provide the requested hydraulic duty')
        if self.test_case!='healthy' and self.fault_start_minutes+2>self.duration_minutes:raise ValueError('fault_start_minutes: leave at least two minutes after the clean baseline')
        return self


LABELS={'force_unit':{'metric_tonne_force':'Metric tonnes-force','short_ton_force':'US short tons-force'},
        'allow_bottleneck':{'no':'No — require normal downstream capacity','yes':'Yes — intentionally test accumulation and line stops'},
        'scrap_route':{'combined':'Shaker chutes and conveyor','shaker':'Shaker chutes','conveyor':'Motorized conveyor'},
        'test_case':{'healthy':'Healthy line — first test','feed_slip':'Feeder slipping','supply_starvation':'Material supply starvation',
        'lube_restriction':'Lubrication restriction','station_sensor':'Station sensor failure','scrap_blockage':'Offal removal blocked',
        'washer_cold':'Washer heating lost','washer_low_flow':'Washer spray flow low','packing_slow':'Manual packing slowed'}}


def fields():
    schema=LineSetup.model_json_schema()['properties'];result=[]
    for name,prop in schema.items():
        item={k:prop[k] for k in ('step','label','unit','help','tooltip','default')}
        item['name']=name;item['type']='select' if 'enum' in prop else prop['type']
        if name=='capacity_tons':item['readOnly']=True
        if 'enum' in prop:item['choices']=[{'value':x,'label':LABELS[name][x]} for x in prop['enum']]
        for key in ('minimum','maximum','exclusiveMinimum'):
            if key in prop:item[key]=prop[key]
        if item['type'] in ('number','integer'):item['step_size']=1 if item['type']=='integer' else 'any'
        result.append(item)
    return result


def preset():
    return {'preset_id':PRESET_ID,'preset_version':PRESET_VERSION,'config':LineSetup().model_dump(),
            'fields':fields(),'steps':STEPS,'simulation_only':True,'practice':True}


def parameters(setup:LineSetup):
    values=setup.model_dump()
    for key in ('duration_minutes','seed','test_case','fault_start_minutes','force_unit','capacity_tons','forming_force_tons','scrap_route','allow_bottleneck'):values.pop(key)
    values['capacity_n']=setup.capacity_tons*FORCE[setup.force_unit]
    values['forming_force_n']=setup.forming_force_tons*FORCE[setup.force_unit]
    values['scrap_route_code']={'shaker':1.,'conveyor':2.,'combined':3.}[setup.scrap_route]
    return values


def preflight(setup:LineSetup):
    config=setup.model_dump();digest=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    output=setup.speed_spm*setup.parts_per_stroke
    packing=60/(60/(setup.packers*setup.packing_rate_per_min)+setup.container_change_s/setup.container_parts)
    warnings=['Generic synthetic assumptions; this does not qualify a physical press.']
    if packing<output:warnings.append('Manual packing is slower than press output; accumulation can stop the line.')
    if setup.washer_speed_m_min/setup.part_spacing_m<output:warnings.append('Washer throughput is below press output; its inlet queue can fill.')
    mass=setup.width_mm/1000*setup.thickness_mm/1000*setup.progression_mm/1000*setup.density_kg_m3
    if mass*setup.speed_spm*setup.duration_minutes>setup.coil_mass_kg:warnings.append('The loaded coil can run out during this test; stock exhaustion is modeled.')
    bottleneck=packing<output or setup.washer_speed_m_min/setup.part_spacing_m<output
    return {'passed':True,'practice':True,'simulation_only':True,'config':config,'config_sha256':digest,
            'requires_bottleneck_acknowledgment':bottleneck and setup.allow_bottleneck!='yes',
            'preset_id':PRESET_ID,'preset_version':PRESET_VERSION,'warnings':warnings,
            'summary':{'maximum_spm':10,'maximum_strokes_per_hour':600,'operating_spm':setup.speed_spm,
                       'capacity_n':parameters(setup)['capacity_n'],'stations':10,'nominal_parts_per_minute':output,
                       'resolved_forming_force_n':parameters(setup)['forming_force_n']*(setup.width_mm/600)*(setup.thickness_mm/1.5),
                       'resolved_work_per_stroke_j':setup.work_per_stroke_j*(setup.width_mm/600)*(setup.thickness_mm/1.5)*(setup.progression_mm/800),
                       'strip_mass_per_progression_kg':mass,'washer_residence_seconds':60*setup.washer_length_m/setup.washer_speed_m_min,
                       'packing_effective_parts_per_minute':packing}}


def native_config(setup:LineSetup):
    from historiansim.plants import get_plant
    from historiansim.config.schema import ScenarioConfig,TimeConfig,EpisodeConfig,DisturbanceConfig
    plant=get_plant('stamping_line')
    loops=plant.loops()
    for loop in loops:
        if loop.name=='SIC-1500':loop.sp=setup.speed_spm
    fault=CASES[setup.test_case]
    cfg=ScenarioConfig(name='generic-1500t-practice',unit='stamping_line',seed=setup.seed,
        time=TimeConfig(days=setup.duration_minutes/1440,dt_scan=1.,dt_sim=.1,timezone='UTC'),
        params=parameters(setup),loops=loops,ballast_tags=0,
        disturbances=DisturbanceConfig(channels=plant.channels()),
        episodes=EpisodeConfig(n_faults=1 if fault else 0,n_benign=0,n_concurrent=0,background_fouling=False,
            baseline_days=setup.fault_start_minutes/1440 if fault else 0,min_gap_days=0,
            cause_ids=[fault] if fault else None,severities=['obvious'] if fault else None))
    return cfg.model_dump(mode='json')
