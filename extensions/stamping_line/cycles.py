"""Cycle-boundary inventory and finite transport queues. No historian rewriting."""
import math
from array import array
from historiansim.core.integrator import rk4_step

class EventLog:
    def __init__(self):self.time=array('d');self.kind=array('b');self.count=array('q')
    def public_status_columns(self):return self.time,self.kind,self.count,{1:'COUNT-STROKES',4:'COUNT-PRODUCED',5:'COUNT-PACKED',2:'DI-FEED'}
    def append(self,t,kind,count):self.time.append(t);self.kind.append({0:1,1:4,2:5,3:2}[kind]);self.count.append(count)
    def __len__(self):return len(self.time)
    def __iter__(self):
        for t,k,c in zip(self.time,self.kind,self.count):yield dict(time_s=t,kind={1:'stroke_complete',4:'product_discharge',5:'packed',2:'feed_complete'}[k],count=c)

class LineCycleEvents:
    def __init__(self,unit,x,u,d,p):
        self.lube_initial_l=x[4];self.lube_makeup_l=0.;self.lube_loss_l=0.;self.integration_steps=0;self.water_initial=x[3];self.water_makeup=0.;self.water_evap=0.;self.water_energy_initial=x[3]*4180*x[1];self.water_energy_in=0.;self.water_energy_out=0.;self.unit=unit;self.phase=0.;self.completed=0;self.produced=0;self.packed=0;self.rejected=0;self.pack_queue=0;self.container_fill=0;self.containers=0;self.change_until=0.;self.pack_credit=0.;self.next_wash=0.;self.blocked=False;self.stop_requested=False
        self.loop_m=p['loop_initial_m'];self.linear_mass=p['width_mm']*.001*p['thickness_mm']*.001*p['density_kg_m3'];self.coils_loaded=1;self.coil_change_until=0.;self.remaining_kg=p['coil_mass_kg'];self.initial_kg=self.remaining_kg+self.loop_m*self.linear_mass;self.consumed_kg=0.;self.scrap_kg=0.;self.scrap_removed_kg=0.;self.die_mass_kg=0.;self.output_mass_kg=0.;self.die=[None]*9;self.discharge=[];self.washer=[];self.events=EventLog();self.energy_in=0.;self.energy_forming=0.;self.energy_loss=0.;self.last_pitch=0.;self.feed_shaft_m=0.;self.feed_strip_m=0.;self.feed_mass_kg=0.;self.feed_failed=False;self.feed_complete=False;self.running=False;self.wash_qualified=False;self.payout=0.;self.straightener_speed=0.
    def on_controls(self,controllers):self.stop_requested=controllers['SIC-1500'].sp<=0
    def material_residual(self):return self.initial_kg-self.remaining_kg-self.loop_m*self.linear_mass-self.die_mass_kg-self.feed_mass_kg-self.output_mass_kg-self.scrap_kg-self.scrap_removed_kg
    def drive(self,x,p):
        occupied=[self.feed_strip_m>0 or self.completed>0]+[item is not None for item in self.die]
        count=sum(occupied)+(self.running and not occupied[0])
        peak,nominal_work=self.unit.forming_demand(p)
        work=nominal_work*count/10
        forming=work*max(float(x[0]),0)/60 if self.running else 0.
        mechanical_loss=5000. if self.running else 1000.
        electrical=(forming+mechanical_loss)/p['efficiency']
        return occupied,work,forming,electrical,electrical-forming
    def observations(self,t,x,u,d,p):
        occupied,work,forming,electrical,loss=self.drive(x,p)
        a=self.phase
        ram_m=p['stroke_mm']*.001*(1-math.cos(2*math.pi*a))/2
        peak,nominal_work=self.unit.forming_demand(p)
        travel=2*nominal_work/peak
        displacement=(ram_m-(p['stroke_mm']*.001-travel))/travel
        force=peak/1000*sum(occupied)/10*max(0.,1-abs(2*displacement-1)) if a<=.5 and self.running else 0.
        out={'PHASE-1500':a,'ZI-RAM':p['stroke_mm']*(1-math.cos(2*math.pi*a))/2,'WI-TOTAL':force,'LI-LOOP':self.loop_m,'WI-COIL':self.remaining_kg,'COUNT-COILS':self.coils_loaded,'DI-REEL-READY':float(self.remaining_kg>0),'ZI-COIL':math.sqrt(.5**2+4*self.remaining_kg/(math.pi*p['width_mm']*.001*p['density_kg_m3'])),'FI-REEL':self.payout,'II-REEL':2+10*self.payout,'SI-STRAIGHTENER':self.straightener_speed,'II-STRAIGHTENER':3+(7*210e9*(p['width_mm']*.001)*(p['thickness_mm']*.001)**3/(24*.05**2))*self.straightener_speed/(math.sqrt(3)*p['voltage_v']*p['power_factor']*.85),'WI-STRAIGHTENER-LOAD':7*210e9*(p['width_mm']*.001)*(p['thickness_mm']*.001)**3/(24*.05**2)/1000,'ZI-STRAIGHTENER-GAP':p['thickness_mm']*.95,'ZI-FEED-SHAFT':self.feed_shaft_m*1000,'ZI-FEED-STRIP':self.feed_strip_m*1000,'CALC-FEED-ERROR':(self.feed_shaft_m-self.feed_strip_m)*1000,'DI-FEED':float(self.feed_complete),'COUNT-STROKES':self.completed,'COUNT-PRODUCED':self.produced,'COUNT-PACKED':self.packed,'COUNT-REJECTED':self.rejected,'COUNT-DISCHARGE':len(self.discharge),'COUNT-WASHER':len(self.washer),'COUNT-PACK-QUEUE':self.pack_queue,'COUNT-CONTAINER':self.container_fill,'COUNT-CONTAINERS':self.containers,'DI-RUN':float(self.running),'DI-BLOCKED':float(self.blocked),'WI-SCRAP':self.scrap_kg,'II-SCRAP':3+2*self.scrap_kg,'SI-WASH':p['washer_speed_m_min'],'DI-PACKING':float(t>=self.change_until),'AUDIT-MATERIAL-RELATIVE-RESIDUAL':abs(self.material_residual())/max(self.initial_kg,1),'AUDIT-COUNTER-RESIDUAL':self.produced-self.packed-self.rejected-len(self.discharge)-len(self.washer)-self.pack_queue,'AUDIT-ENERGY-RELATIVE-RESIDUAL':abs(self.energy_in-self.energy_loss-self.energy_forming)/max(self.energy_in,1)}
        for i,present in enumerate(occupied,1):out[f'FI-LUBE-STATION-{i:02}']=p['lube_flow_l_min']*p['lube_factor']/10 if present and self.running and self.phase>=.5 else 0.
        out['FI-LUBE']=sum(out[f'FI-LUBE-STATION-{i:02}'] for i in range(1,11))
        out.update({'JI-DRIVE':electrical/1000,'II-DRIVE':electrical/(math.sqrt(3)*p['voltage_v']*p['power_factor'])})
        out.update({'AUDIT-WASHER-INITIAL-ENERGY-J':self.water_energy_initial,'AUDIT-WASHER-ENERGY-IN-J':self.water_energy_in,'AUDIT-WASHER-ENERGY-OUT-J':self.water_energy_out,'AUDIT-WASHER-STORED-ENERGY-J':x[3]*4180*x[1],'AUDIT-WASHER-INITIAL-WATER-L':self.water_initial,'AUDIT-WASHER-MAKEUP-L':self.water_makeup,'AUDIT-WASHER-EVAPORATION-L':self.water_evap,'AUDIT-WASHER-WATER-L':x[3],'AUDIT-WASHER-ENERGY-RELATIVE-RESIDUAL':abs(self.water_energy_initial+self.water_energy_in-self.water_energy_out-x[3]*4180*x[1])/max(self.water_energy_in,1.),'AUDIT-WASHER-WATER-RELATIVE-RESIDUAL':abs(self.water_initial+self.water_makeup-self.water_evap-x[3])/max(self.water_initial+self.water_makeup,1.)})
        out.update({'AUDIT-LUBE-INITIAL-L':self.lube_initial_l,'AUDIT-LUBE-MAKEUP-L':self.lube_makeup_l,'AUDIT-LUBE-LOSS-L':self.lube_loss_l,'AUDIT-LUBE-RESERVOIR-L':x[4],'AUDIT-LUBE-MATERIAL-RELATIVE-RESIDUAL':abs(self.lube_initial_l+self.lube_makeup_l-self.lube_loss_l-x[4])/max(self.lube_initial_l+self.lube_makeup_l,1.)})
        out.update({'AUDIT-INITIAL-MASS-KG':self.initial_kg,'AUDIT-COIL-REMAINING-KG':self.remaining_kg,'AUDIT-LOOP-MASS-KG':self.loop_m*self.linear_mass,'AUDIT-DIE-MASS-KG':self.die_mass_kg+self.feed_mass_kg,'AUDIT-OUTPUT-MASS-KG':self.output_mass_kg,'AUDIT-SCRAP-REMOVED-KG':self.scrap_removed_kg,'AUDIT-ENERGY-IN-J':self.energy_in,'AUDIT-FORMING-ENERGY-J':self.energy_forming,'AUDIT-LOSS-ENERGY-J':self.energy_loss})
        for i,item in enumerate(occupied,1):out[f'DI-STATION-{i:02}']=float(item);out[f'WI-STATION-{i:02}']=force/max(sum(occupied),1) if item else 0.
        for i in range(1,5):out[f'WI-CORNER-{i}']=force/4
        return out
    def advance(self,t,x,u,d,p,dt_sim,n_sub):
        # Fixed maximum integration quantum; split at cycle and transport boundaries.
        now=t;end=t+dt_sim*n_sub
        while now<end-1e-10:
            cycle=60/max(float(x[0]),.01);pitch=p['progression_mm']*.001
            # Reserve every piece of the next release before allowing its stroke.
            # Only this press adds to discharge, so draining cannot invalidate the reservation.
            batch=int(p['parts_per_stroke']) if self.die[-1] is not None else 0
            self.blocked=len(self.discharge)+batch>p['buffer_parts'] or self.scrap_kg>=20.
            self.running=not self.stop_requested and bool(p['run_enable']) and not self.blocked and x[2]>=2 and x[4]>1 and (self.loop_m>=pitch-self.feed_strip_m-1e-9) and not self.feed_failed and self.unit.forming_demand(p)[0]<=p['capacity_n'] and 2*self.unit.forming_demand(p)[1]/self.unit.forming_demand(p)[0]<=p['stroke_mm']*.001
            occupied,work,forming,electrical,loss=self.drive(x,p)
            if electrical>p['motor_kw']*1000:self.running=False;occupied,work,forming,electrical,loss=self.drive(x,p)
            feed_phase=p['feed_window_s']/cycle
            boundary=feed_phase if self.phase<feed_phase-1e-9 else 1.
            h=min(p['integration_step_s'],end-now,(boundary-self.phase)*cycle if self.running else .1)
            for deadline in ([self.change_until] if self.change_until>now+1e-9 else [])+[v[0] for v in self.washer[:1]]+[v[0] for v in self.discharge[:1]]:
                if deadline>now+1e-9:h=min(h,deadline-now)
            self.energy_in+=electrical*h;self.energy_forming+=forming*h;self.energy_loss+=loss*h
            duty=(sum(occupied)/10 if self.running and self.phase>=.5 else 0.)
            effective={**p,'_lube_duty':duty}
            self.integration_steps+=1
            stages=[]
            def derivative(tt,xx):
                heat,loss,evap,makeup,spray=self.unit.thermal(xx,d,effective)
                stages.append((heat+makeup*4180*d.get('T_amb',20.),loss+evap*(2260000+4180*xx[1]),makeup,evap,min(.02,max(0.,50.-xx[4])*.01),p['lube_flow_l_min']*p['lube_factor']*duty/60*.1 if xx[4]>1 else 0.))
                return self.unit.derivatives(tt,xx,u,d,effective)
            x=rk4_step(derivative,now,x,h)
            totals=[h*sum(w*stage[i] for w,stage in zip((1,2,2,1),stages))/6 for i in range(6)]
            self.water_energy_in+=totals[0];self.water_energy_out+=totals[1];self.water_makeup+=totals[2];self.water_evap+=totals[3];self.lube_makeup_l+=totals[4];self.lube_loss_l+=totals[5]
            updated=[]
            for deadline,mass,dose,temp in self.washer:
                exchange=(x[1]-temp)*mass*500*.02*h
                self.water_energy_out+=exchange
                x[1]-=exchange/(max(x[3],1.)*4180);temp+=exchange/(mass*500)
                dose+=h*max(0.,(x[1]-35)/25)*p['spray_factor']**2
                updated.append((deadline,mass,dose,temp))
            self.washer=updated
            target=p['loop_capacity_m']*.5
            if self.remaining_kg<=1e-9:
                if not self.coil_change_until:self.coil_change_until=now+p['coil_change_s']
                elif now>=self.coil_change_until:
                    self.remaining_kg=p['coil_mass_kg'];self.initial_kg+=p['coil_mass_kg'];self.coils_loaded+=1;self.coil_change_until=0.
            feed_rate=(min(pitch-self.feed_shaft_m,pitch/p['feed_window_s']*h,p['feeder_speed_m_s']*h)*p['feed_traction']/h if self.running and self.phase<feed_phase-1e-9 else 0.)
            if self.feed_failed and p['feed_traction']>=.999:feed_rate=min(pitch-self.feed_strip_m,p['feeder_speed_m_s']*h)/h
            def supply_derivative(tt,state):
                loop,speed=state
                target_speed=min(p['straightener_speed_m_s']*p['supply_factor'],max(0.,target-loop)/.5)
                import numpy as np
                return np.array([speed-feed_rate,(target_speed-speed)/.5])
            import numpy as np
            supply_next=rk4_step(supply_derivative,now,np.array([self.loop_m,self.straightener_speed]),h)
            average_speed=max(0.,(supply_next[0]-self.loop_m)/h+feed_rate)
            self.straightener_speed=max(0.,float(supply_next[1]))
            self.payout=min(average_speed,max(0.,p['loop_capacity_m']-self.loop_m)/max(h,1e-12),self.remaining_kg/self.linear_mass/max(h,1e-12))
            self.loop_m+=self.payout*h;self.remaining_kg-=self.payout*h*self.linear_mass
            removed=min(self.scrap_kg,{1.:.4,2.:.5,3.:.9}[p['scrap_route_code']]*p['scrap_factor']*h);self.scrap_kg-=removed;self.scrap_removed_kg+=removed
            if self.running and self.phase<feed_phase-1e-9:
                shaft=min(pitch-self.feed_shaft_m,pitch/p['feed_window_s']*h,p['feeder_speed_m_s']*h)
                strip=min(shaft*p['feed_traction'],self.loop_m)
                self.feed_shaft_m+=shaft;self.feed_strip_m+=strip;self.feed_mass_kg+=strip*self.linear_mass;self.loop_m-=strip;self.consumed_kg+=strip*self.linear_mass
            elif self.feed_failed and p['feed_traction']>=.999:
                strip=min(pitch-self.feed_strip_m,p['feeder_speed_m_s']*h,self.loop_m)
                self.feed_shaft_m+=strip;self.feed_strip_m+=strip;self.feed_mass_kg+=strip*self.linear_mass;self.loop_m-=strip;self.consumed_kg+=strip*self.linear_mass
                if self.feed_strip_m>=pitch-1e-9:self.feed_complete=True;self.feed_failed=False;self.events.append(now+h,3,1)
            if self.running:self.phase+=h/cycle
            if self.phase>=feed_phase-1e-9 and not self.feed_complete:
                self.feed_complete=self.feed_strip_m>=pitch-1e-9
                if self.feed_complete:self.events.append(now+h,3,1)
                if not self.feed_complete:self.feed_failed=True;self.running=False
            now+=h
            if self.phase>=1-1e-9:
                self.phase=0.;self.completed+=1;self.last_pitch=p['progression_mm']*p['feed_traction'];mass=self.feed_mass_kg
                scrap=mass*p['trim_fraction'];part_mass=mass-scrap;self.scrap_kg+=scrap
                outgoing=self.die.pop();self.die.insert(0,part_mass);self.die_mass_kg+=part_mass
                if outgoing is not None:
                    self.die_mass_kg-=outgoing;self.output_mass_kg+=outgoing;self.produced+=int(p['parts_per_stroke']);self.discharge.extend([(now+3.,outgoing/p['parts_per_stroke'])]*int(p['parts_per_stroke']));self.events.append(now,1,self.produced)
                self.events.append(now,0,self.completed)
                self.events.append(now,3,0)
                self.feed_shaft_m=0.;self.feed_strip_m=0.;self.feed_mass_kg=0.;self.feed_complete=False
            while self.washer and self.washer[0][0]<=now+1e-9 and self.pack_queue<p['buffer_parts']:
                _,mass,dose,temp=self.washer.pop(0)
                clean=dose>=30.
                # Declared manual visual inspection before packing; reject is measured decision.
                if clean:self.pack_queue+=1
                else:self.rejected+=1
            if self.discharge and self.discharge[0][0]<=now+1e-9 and now>=self.next_wash-1e-9 and len(self.washer)<p['buffer_parts']:
                _,mass=self.discharge.pop(0);duration=p['washer_length_m']/p['washer_speed_m_min']*60;self.wash_qualified=x[1]>=50 and p['spray_factor']>=.7;self.washer.append((now+duration,mass,0.,20.));self.next_wash=now+p['part_spacing_m']/p['washer_speed_m_min']*60
            if now>=self.change_until and self.pack_queue:
                self.pack_credit+=h*p['packers']*p['packing_rate_per_min']/60*p['packing_factor']*(1+.1*math.sin(now/30))
                while self.pack_credit>=1-1e-9 and self.pack_queue:
                    self.pack_credit-=1;self.pack_queue-=1;self.packed+=1;self.container_fill+=1;self.events.append(now,2,self.packed)
                    if self.container_fill>=p['container_parts']:self.containers+=1;self.container_fill=0;self.change_until=now+p['container_change_s'];self.pack_credit=0;break
            elif not self.pack_queue:self.pack_credit=0.
        return x

def engineering_acceptance(truth):
    """Recompute private ledger arithmetic independently of reported residuals."""
    import numpy as np
    names=('AUDIT-INITIAL-MASS-KG','AUDIT-COIL-REMAINING-KG','AUDIT-LOOP-MASS-KG','AUDIT-DIE-MASS-KG','AUDIT-OUTPUT-MASS-KG','AUDIT-SCRAP-REMOVED-KG','WI-SCRAP','AUDIT-ENERGY-IN-J','AUDIT-FORMING-ENERGY-J','AUDIT-LOSS-ENERGY-J','AUDIT-MATERIAL-RELATIVE-RESIDUAL','AUDIT-ENERGY-RELATIVE-RESIDUAL','AUDIT-COUNTER-RESIDUAL','COUNT-PRODUCED','COUNT-PACKED','COUNT-REJECTED','COUNT-DISCHARGE','COUNT-WASHER','COUNT-PACK-QUEUE','AUDIT-WASHER-ENERGY-RELATIVE-RESIDUAL','AUDIT-WASHER-WATER-RELATIVE-RESIDUAL','AUDIT-WASHER-INITIAL-ENERGY-J','AUDIT-WASHER-ENERGY-IN-J','AUDIT-WASHER-ENERGY-OUT-J','AUDIT-WASHER-STORED-ENERGY-J','AUDIT-WASHER-INITIAL-WATER-L','AUDIT-WASHER-MAKEUP-L','AUDIT-WASHER-EVAPORATION-L','AUDIT-WASHER-WATER-L','AUDIT-LUBE-INITIAL-L','AUDIT-LUBE-MAKEUP-L','AUDIT-LUBE-LOSS-L','AUDIT-LUBE-RESERVOIR-L','AUDIT-LUBE-MATERIAL-RELATIVE-RESIDUAL')
    if set(names)-set(truth.signals):raise ValueError('PRIVATE_ENGINEERING_AUDIT_REQUIRED: missing line ledger')
    v={n:np.asarray(truth.signals[n],dtype=float) for n in names};shape=v[names[0]].shape
    if len(shape)!=1 or not shape[0] or any(a.shape!=shape or not np.all(np.isfinite(a)) for a in v.values()):raise ValueError('INVALID_PRIVATE_ENGINEERING_AUDIT: nonfinite or mismatched line ledger')
    material=np.abs(v[names[0]]-sum(v[n] for n in names[1:7]))/np.maximum(v[names[0]],1.)
    energy=np.abs(v['AUDIT-ENERGY-IN-J']-v['AUDIT-FORMING-ENERGY-J']-v['AUDIT-LOSS-ENERGY-J'])/np.maximum(v['AUDIT-ENERGY-IN-J'],1.)
    balance=v['COUNT-PRODUCED']-sum(v[n] for n in ('COUNT-PACKED','COUNT-REJECTED','COUNT-DISCHARGE','COUNT-WASHER','COUNT-PACK-QUEUE'))
    thermal=np.abs(v['AUDIT-WASHER-INITIAL-ENERGY-J']+v['AUDIT-WASHER-ENERGY-IN-J']-v['AUDIT-WASHER-ENERGY-OUT-J']-v['AUDIT-WASHER-STORED-ENERGY-J'])/np.maximum(v['AUDIT-WASHER-ENERGY-IN-J'],1.)
    water=np.abs(v['AUDIT-WASHER-INITIAL-WATER-L']+v['AUDIT-WASHER-MAKEUP-L']-v['AUDIT-WASHER-EVAPORATION-L']-v['AUDIT-WASHER-WATER-L'])/np.maximum(v['AUDIT-WASHER-INITIAL-WATER-L']+v['AUDIT-WASHER-MAKEUP-L'],1.)
    lube=np.abs(v['AUDIT-LUBE-INITIAL-L']+v['AUDIT-LUBE-MAKEUP-L']-v['AUDIT-LUBE-LOSS-L']-v['AUDIT-LUBE-RESERVOIR-L'])/np.maximum(v['AUDIT-LUBE-INITIAL-L']+v['AUDIT-LUBE-MAKEUP-L'],1.)
    for a,n in ((lube,'AUDIT-LUBE-MATERIAL-RELATIVE-RESIDUAL'),(thermal,'AUDIT-WASHER-ENERGY-RELATIVE-RESIDUAL'),(water,'AUDIT-WASHER-WATER-RELATIVE-RESIDUAL'),(material,'AUDIT-MATERIAL-RELATIVE-RESIDUAL'),(energy,'AUDIT-ENERGY-RELATIVE-RESIDUAL'),(balance,'AUDIT-COUNTER-RESIDUAL')):
        if not np.allclose(a,v[n],rtol=1e-10,atol=1e-12):raise ValueError('AUDIT_ARITHMETIC_MISMATCH: '+n)
    checks={name:{'maximum':float(np.max(np.abs(a))),'limit':limit,'passed':bool(np.max(np.abs(a))<=limit)} for name,a,limit in (('material_relative_residual',material,1e-6),('energy_relative_residual',energy,.001),('counter_reconciliation',balance,0.))}
    for name,limit in [('AUDIT-LUBE-MATERIAL-RELATIVE-RESIDUAL',1e-6),('AUDIT-WASHER-ENERGY-RELATIVE-RESIDUAL',.001),('AUDIT-WASHER-WATER-RELATIVE-RESIDUAL',1e-6)]:
        checks[name]={'maximum':float(np.max(v[name])),'limit':limit,'passed':bool(np.max(v[name])<=limit)}
    checks['integer_nonnegative_counters']={'passed':all(bool(np.all((v[n]>=0)&(v[n]==np.floor(v[n])))) for n in names if n.startswith('COUNT-'))}
    return {'passed':all(c['passed'] for c in checks.values()),'checks':checks,'samples':shape[0],'scope':'Private within-model discrete strip mass, output counts, averaged cycle energy. Does not qualify acquisition, rigid-crank mechanics or real equipment.'}
