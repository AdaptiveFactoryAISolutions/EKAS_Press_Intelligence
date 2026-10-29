"""P-27 lumped envelope model with a separate material/event clock.

Units are SI internally except pitch (mm), pressure (bar), temperature (C).
The six envelope states are not instantaneous crank measurements.
"""
from __future__ import annotations
import math
import numpy as np
from scipy.optimize import root
from historiansim.plants.unit import UnitModel

class StampingPress(UnitModel):
    name='stamping_press'
    state_names=('omega','pitch','buffer','pressure','oil_temperature','die_temperature')
    mv_names=('DRIVE-271','FEED-271','DECOIL-271','PUMP-272','COOL-271')
    disturbance_names=('T_amb','T_cw','strength','thickness','voltage','cooling')
    stiction_params={}

    @staticmethod
    def default_params():
        return dict(compiled_cycles=1.,cut_perimeter=.376, shear_strength=100000/(.376*.0012), forming_travel=.02,inertia=1000., torque=600., efficiency=.9, bearing_drag=200.,
                    other_loss=100., viscosity=1., die_wear=1., guide_drag=1.,
                    traction=1., backlash=0., obstruction=0., brake_drag=1.,
                    pump_efficiency=1., filter_resistance=1., leakage=0.,
                    film_delivery=1., oil_capacity=40000., die_capacity=80000.,
                    brake_coefficient=100., strip_density=7850., strip_width=.1, trim_fraction=.12,
                    servo_tau=30., hydraulic_tau=30., coolant_ua=30.,
                    oil_ua=20., feed_gain=200., design_rate=60.)

    def validate_params(self,p):
        if p['compiled_cycles'] not in (0.,1.): raise ValueError('compiled_cycles must be0 or1')
        for key in ('inertia','torque','efficiency','oil_capacity','die_capacity','servo_tau','hydraulic_tau'):
            if p[key] <= 0: raise ValueError(key+' must be positive')

    @staticmethod
    def peak_force(p,d):
        # Effective cutting perimeter and cold-strip shear strength define the
        # force, rather than a hand-written historian force signature.
        return p['cut_perimeter']*d['thickness']*p['shear_strength']*d['strength']*p['die_wear']*p['guide_drag']

    @classmethod
    def forming_force(cls,displacement,p,d):
        fraction=displacement/p['forming_travel']
        return cls.peak_force(p,d)*max(0.,1-abs(2*fraction-1))

    @classmethod
    def force_work(cls,p,d):
        return .5*cls.peak_force(p,d)*p['forming_travel']

    def quantities(self,x,u,d,p):
        w,pitch,buf,pressure,oil,die=x
        rate=max(w,0)/(2*math.pi)
        work=self.force_work(p,d)
        visc=p['viscosity']*math.exp(-.015*(oil-40))
        bearing=p['bearing_drag']*visc*(max(w,0)/(2*math.pi))**2
        permitted=pressure>=2. and buf>=.15 and die<=80. and work<=2500. and 50<pitch<150
        permitted=bool(p.get('_cycle_enabled',permitted)) and not bool(p.get('_cycle_stop',False))
        clutch=bool(p.get('_cycle_clutch',permitted)) and permitted
        forming=p.get('_cycle_work',work)*rate if clutch else 0.
        brake=0. if permitted else p['brake_coefficient']*max(w,0)**2
        other_ambient=.25*p['other_loss']*(max(w,0)/(2*math.pi))**2
        die_friction=.75*p['other_loss']*(max(w,0)/(2*math.pi))**2/max(p['film_delivery'],.1) if clutch else 0.
        other=other_ambient+die_friction
        motor_torque=p['efficiency']*p['torque']*u['DRIVE-271']*d['voltage'] if permitted else 0.
        forming_torque=p.get('_cycle_work',work)/(2*math.pi) if clutch else 0.
        motor=motor_torque*max(w,0.)
        pump=10*u['PUMP-272']*p['pump_efficiency']*d['voltage']/p['filter_resistance']**.2
        demand=pressure/visc + p['leakage']*math.sqrt(max(pressure,0))
        traction=min(1.,p['traction']/max(.85+d['strength']*.15,1e-6))
        pitch_target=max(0,p['feed_gain']*u['FEED-271']*traction-p['backlash']-p['obstruction'])
        encoder_pitch=(pitch+p['backlash']+p['obstruction'])/max(traction,1e-6)
        consumed=p.get('_cycle_pitch_m',max(pitch,0)*.001)*rate if clutch else 0.
        delivery=.2*u['DECOIL-271']/p['brake_drag']
        cooling=p['coolant_ua']*u['COOL-271']*d['cooling']*(die-d['T_cw'])
        pump_input=(pressure*pump*100000/60000+100*u['PUMP-272'])/max(p['pump_efficiency'],.05)
        oil_cooling=p['oil_ua']*(oil-d['T_amb'])
        die_ambient=2*(die-d['T_amb'])
        die_heat=.3*forming+die_friction
        part_energy=.7*forming
        film=.02*p['film_delivery']*pump
        dim=100+.012*(die-50)+8*(d['thickness']/.0012-1)+.2*(pitch-100)+.1*(1-p['film_delivery'])
        return dict(motor_torque=motor_torque,forming_torque=forming_torque,clutch=float(clutch),pump_input=pump_input,oil_cooling=oil_cooling,die_ambient=die_ambient,die_heat=die_heat,part_energy=part_energy,other_ambient=other_ambient,encoder_pitch=encoder_pitch,traction=traction,rate=rate,work=work,brake=brake,other=other,permitted=float(permitted),bearing=bearing,forming=forming,motor=motor,pump=pump,demand=demand,
                    pitch_target=pitch_target,consumed=consumed,delivery=delivery,cooling=cooling,film=film,dimension=dim)

    def derivatives(self,t,x,u,d,p):
        q=self.quantities(x,u,d,p); w,pitch,buf,pressure,oil,die=x
        return np.array([(q['motor_torque']-q['forming_torque']-((q['bearing']+q['other']+q['brake'])/w if w>0 else 0.))/p['inertia'],
                         (q['pitch_target']-pitch)/p['servo_tau'],q['delivery']-q['consumed'],
                         (q['pump']-q['demand'])/p['hydraulic_tau'],
                         (q['bearing']+q['pump_input']-q['oil_cooling'])/p['oil_capacity'],
                         (q['die_heat']-q['cooling']-q['die_ambient'])/p['die_capacity']])

    def signals(self,t,x,u,d,p):
        q=self.quantities(x,u,d,p); w,pitch,buf,pressure,oil,die=x
        return {'SI-271':w*60/(2*math.pi),'SI-272':w*60/(2*math.pi),'ZI-271':q['encoder_pitch'],'ZI-276':q['encoder_pitch'],'ZI-272':pitch,
                'LI-271':buf,'LI-272':buf,'PI-272':pressure,'PI-273':pressure,'TI-272':oil,'TI-271':die,
                'JI-271':q['motor']/p['efficiency']/1000,'WI-271':2*q['work']/p['forming_travel']/1000,
                'FI-275':q['delivery'],'FI-271':q['pump'],'DPI-271':.1*p['filter_resistance']*q['pump'],
                'WI-272':(p['guide_drag']-1)*q['work']/.01/1000,
                'ZI-273':p['backlash'], 'FI-274':p['leakage']*math.sqrt(max(pressure,0)),
                'JI-272':q['pump_input']/1000,
                'PI-271':100*p['brake_drag']+10*p['obstruction'],'FI-272':10*u['COOL-271']*d['cooling'],
                'TI-273':d['T_cw'],'QI-271':q['dimension'],'QI-272':q['dimension'],
                'AI-271':d['strength'],'AI-272':d['thickness']*1000,'EI-271':d['voltage']*400,
                'FI-273':q['film'],'CALC-TRAVEL-GAP':q['encoder_pitch']-pitch,'CALC-WORK':q['work'],'CALC-SUPPLY':q['delivery'],
                'CALC-CONSUMPTION':q['consumed']}

    def steady_inputs(self,targets,d,p):
        rate=targets.get('SI-271',p['design_rate'])/60
        pitch=targets.get('ZI-271',100.)
        pressure=targets.get('PI-272',5.)
        die=targets.get('TI-271',50.)
        w=rate*2*math.pi
        # Oil and pump are coupled through viscosity. Solve that physical balance.
        def balance(v):
            oil,pump=v
            visc=p['viscosity']*math.exp(-.015*(oil-40))
            b=p['bearing_drag']*visc*rate**2
            return [10*pump*p['pump_efficiency']*d['voltage']/p['filter_resistance']**.2-pressure/visc-p['leakage']*math.sqrt(pressure),
                    b+(pressure*(10*pump*p['pump_efficiency']*d['voltage']/p['filter_resistance']**.2)*100000/60000+100*pump)/max(p['pump_efficiency'],.05)-p['oil_ua']*(oil-d['T_amb'])]
        sol=root(balance,[35.,.5])
        if not sol.success: raise ValueError('oil equilibrium failed')
        oil,pump=sol.x
        visc=p['viscosity']*math.exp(-.015*(oil-40))
        work=self.force_work(p,d)
        return {'DRIVE-271':(work*rate+p['bearing_drag']*visc*rate**2+p['other_loss']*rate**2*(.25+.75/max(p['film_delivery'],.1)))/(p['efficiency']*p['torque']*w*d['voltage']),
                'FEED-271':(pitch+p['backlash']+p['obstruction'])/p['feed_gain'],
                'DECOIL-271':pitch*.001*rate*p['brake_drag']/.2,'PUMP-272':float(pump),
                'COOL-271':(.3*work*rate+.75*p['other_loss']*rate**2/max(p['film_delivery'],.1)-2*(die-d['T_amb']))/(p['coolant_ua']*d['cooling']*(die-d['T_cw']))}

    def steady_state(self,u,d,p):
        # Mean buffer inventory is a neutral state at exact flow balance.
        # Exclude it from the nonlinear solve rather than pass a singular
        # Jacobian to the solver and later overwrite its answer.
        def expand(v): return np.array([v[0],v[1],1.,v[2],v[3],v[4]])
        indices=[0,1,3,4,5]
        def fun(v): return self.derivatives(0,expand(v),u,d,p)[indices]
        sol=root(fun,[p['design_rate']*2*math.pi/60,100,5,35,50],options={'xtol':1e-11})
        if not sol.success and np.max(np.abs(fun(sol.x)))>1e-10:
            raise ValueError('press equilibrium failed: '+sol.message)
        return expand(sol.x)

    def cycle_event_source(self,x,u,d,p):
        if p['compiled_cycles']:
            from .compiled_backend import CompiledPressCycleEvents
            return CompiledPressCycleEvents(self,x,u,d,p)
        from .cycles import PressCycleEvents
        return PressCycleEvents(self,x,u,d,p)
