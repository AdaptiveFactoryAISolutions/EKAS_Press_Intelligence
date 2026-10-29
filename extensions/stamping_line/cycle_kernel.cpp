// Exact translation of cycles.py/model.py RK4 and finite event equations.
// Build without fast-math or fused contraction; no schedules or gates altered.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <deque>
#include <limits>
#include <new>
using std::min;using std::max;
enum P {capacity_n,speed_spm,stations,parts_per_stroke,width_mm,thickness_mm,progression_mm,density_kg_m3,coil_mass_kg,loop_capacity_m,loop_initial_m,feeder_speed_m_s,feed_window_s,straightener_speed_m_s,forming_force_n,work_per_stroke_j,motor_kw,voltage_v,efficiency,power_factor,stroke_mm,lube_pressure_bar,lube_flow_l_min,washer_temperature_c,washer_volume_l,heater_kw,spray_flow_l_min,spray_pressure_bar,pump_kw,washer_length_m,washer_speed_m_min,part_spacing_m,buffer_parts,packers,packing_rate_per_min,container_parts,container_change_s,feed_traction,supply_factor,lube_factor,scrap_factor,heater_factor,spray_factor,packing_factor,run_enable,trim_fraction,scrap_route_code,coil_change_s,integration_step_s,compiled_cycles};
struct State {
 double integration_steps;
 double water_initial;
 double water_makeup;
 double water_evap;
 double water_energy_initial;
 double water_energy_in;
 double water_energy_out;
 double phase;
 double completed;
 double produced;
 double packed;
 double rejected;
 double pack_queue;
 double container_fill;
 double containers;
 double change_until;
 double pack_credit;
 double next_wash;
 double blocked;
 double stop_requested;
 double loop_m;
 double linear_mass;
 double coils_loaded;
 double coil_change_until;
 double remaining_kg;
 double initial_kg;
 double consumed_kg;
 double scrap_kg;
 double scrap_removed_kg;
 double die_mass_kg;
 double output_mass_kg;
 double energy_in;
 double energy_forming;
 double energy_loss;
 double last_pitch;
 double feed_shaft_m;
 double feed_strip_m;
 double feed_mass_kg;
 double feed_failed;
 double feed_complete;
 double running;
 double wash_qualified;
 double payout;
 double straightener_speed;
 double lube_initial_l,lube_makeup_l,lube_loss_l;
 double die[9];std::deque<std::array<double,4>> discharge,washer;
};
struct Event {double time,kind,count;};
extern "C" int line_abi_version(){return 2;}
extern "C" int line_scalar_count(){return 47;}
extern "C" void* line_create(const double* v,const double* die){State*s=new(std::nothrow) State{};if(!s)return nullptr;
 s->integration_steps=v[0];
 s->water_initial=v[1];
 s->water_makeup=v[2];
 s->water_evap=v[3];
 s->water_energy_initial=v[4];
 s->water_energy_in=v[5];
 s->water_energy_out=v[6];
 s->phase=v[7];
 s->completed=v[8];
 s->produced=v[9];
 s->packed=v[10];
 s->rejected=v[11];
 s->pack_queue=v[12];
 s->container_fill=v[13];
 s->containers=v[14];
 s->change_until=v[15];
 s->pack_credit=v[16];
 s->next_wash=v[17];
 s->blocked=v[18];
 s->stop_requested=v[19];
 s->loop_m=v[20];
 s->linear_mass=v[21];
 s->coils_loaded=v[22];
 s->coil_change_until=v[23];
 s->remaining_kg=v[24];
 s->initial_kg=v[25];
 s->consumed_kg=v[26];
 s->scrap_kg=v[27];
 s->scrap_removed_kg=v[28];
 s->die_mass_kg=v[29];
 s->output_mass_kg=v[30];
 s->energy_in=v[31];
 s->energy_forming=v[32];
 s->energy_loss=v[33];
 s->last_pitch=v[34];
 s->feed_shaft_m=v[35];
 s->feed_strip_m=v[36];
 s->feed_mass_kg=v[37];
 s->feed_failed=v[38];
 s->feed_complete=v[39];
 s->running=v[40];
 s->wash_qualified=v[41];
 s->payout=v[42];
 s->straightener_speed=v[43];
s->lube_initial_l=v[44];s->lube_makeup_l=v[45];s->lube_loss_l=v[46];for(int i=0;i<9;i++)s->die[i]=die[i];return s;}
extern "C" void line_destroy(State*s){delete s;}
inline void output(State&s,double*v,double*die,double*counts){
 v[0]=s.integration_steps;
 v[1]=s.water_initial;
 v[2]=s.water_makeup;
 v[3]=s.water_evap;
 v[4]=s.water_energy_initial;
 v[5]=s.water_energy_in;
 v[6]=s.water_energy_out;
 v[7]=s.phase;
 v[8]=s.completed;
 v[9]=s.produced;
 v[10]=s.packed;
 v[11]=s.rejected;
 v[12]=s.pack_queue;
 v[13]=s.container_fill;
 v[14]=s.containers;
 v[15]=s.change_until;
 v[16]=s.pack_credit;
 v[17]=s.next_wash;
 v[18]=s.blocked;
 v[19]=s.stop_requested;
 v[20]=s.loop_m;
 v[21]=s.linear_mass;
 v[22]=s.coils_loaded;
 v[23]=s.coil_change_until;
 v[24]=s.remaining_kg;
 v[25]=s.initial_kg;
 v[26]=s.consumed_kg;
 v[27]=s.scrap_kg;
 v[28]=s.scrap_removed_kg;
 v[29]=s.die_mass_kg;
 v[30]=s.output_mass_kg;
 v[31]=s.energy_in;
 v[32]=s.energy_forming;
 v[33]=s.energy_loss;
 v[34]=s.last_pitch;
 v[35]=s.feed_shaft_m;
 v[36]=s.feed_strip_m;
 v[37]=s.feed_mass_kg;
 v[38]=s.feed_failed;
 v[39]=s.feed_complete;
 v[40]=s.running;
 v[41]=s.wash_qualified;
 v[42]=s.payout;
 v[43]=s.straightener_speed;
v[44]=s.lube_initial_l;v[45]=s.lube_makeup_l;v[46]=s.lube_loss_l;for(int i=0;i<9;i++)die[i]=s.die[i];counts[0]=s.discharge.size();counts[1]=s.washer.size();}
struct Thermal {double heat,loss,evap,makeup,spray;};
inline Thermal thermal(const double*x,double ambient,const double*p){
 Thermal q{};q.loss=200*(x[1]-ambient);q.spray=x[3]>100?p[spray_flow_l_min]*p[spray_factor]:0.;q.evap=.005+q.spray/60*.001;
 q.makeup=min(.25,max(0.,p[washer_volume_l]-x[3])*.1+q.evap);
 q.heat=x[3]>100?min(p[heater_kw]*1000*p[heater_factor],max(0.,(p[washer_temperature_c]-x[1])*10000+q.loss+q.evap*2260000+q.makeup*4180*(x[1]-ambient))):0.;return q;
}
inline void derivative(const double*x,double u,double ambient,const double*p,double duty,double*out,Thermal&q){
 q=thermal(x,ambient,p);double lube=x[4]>1?p[lube_flow_l_min]*p[lube_factor]*duty:0.;
 out[0]=(min(10.,10*u)-x[0])/2.;out[1]=(q.heat-q.loss+q.makeup*4180*(ambient-x[1])-q.evap*2260000)/(max(x[3],1.)*4180.);
 out[2]=(p[lube_pressure_bar]*p[lube_factor]*(x[4]>1)-x[2])/2.;out[3]=q.makeup-q.evap;out[4]=-lube/60*.1+min(.02,max(0.,50.-x[4])*.01);
}
inline void rk4(double*x,double u,double ambient,const double*p,double duty,double h,State&s){
 double k[4][5],trial[5];Thermal q[4];derivative(x,u,ambient,p,duty,k[0],q[0]);
 for(int j=0;j<5;j++)trial[j]=x[j]+.5*h*k[0][j];derivative(trial,u,ambient,p,duty,k[1],q[1]);
 for(int j=0;j<5;j++)trial[j]=x[j]+.5*h*k[1][j];derivative(trial,u,ambient,p,duty,k[2],q[2]);
 for(int j=0;j<5;j++)trial[j]=x[j]+h*k[2][j];derivative(trial,u,ambient,p,duty,k[3],q[3]);
 double ein[4],eout[4];double temps[4]={x[1],x[1]+.5*h*k[0][1],x[1]+.5*h*k[1][1],x[1]+h*k[2][1]};
 for(int i=0;i<4;i++){ein[i]=q[i].heat+q[i].makeup*4180*ambient;eout[i]=q[i].loss+q[i].evap*(2260000+4180*temps[i]);}
 s.water_energy_in+=h*(ein[0]+2*ein[1]+2*ein[2]+ein[3])/6;s.water_energy_out+=h*(eout[0]+2*eout[1]+2*eout[2]+eout[3])/6;
 double levels[4]={x[4],x[4]+.5*h*k[0][4],x[4]+.5*h*k[1][4],x[4]+h*k[2][4]};double lmi[4],lmo[4];for(int i=0;i<4;i++){lmi[i]=min(.02,max(0.,50.-levels[i])*.01);lmo[i]=levels[i]>1?p[lube_flow_l_min]*p[lube_factor]*duty/60*.1:0.;}
 s.lube_makeup_l+=h*(lmi[0]+2*lmi[1]+2*lmi[2]+lmi[3])/6;s.lube_loss_l+=h*(lmo[0]+2*lmo[1]+2*lmo[2]+lmo[3])/6;
 s.water_makeup+=h*(q[0].makeup+2*q[1].makeup+2*q[2].makeup+q[3].makeup)/6;s.water_evap+=h*(q[0].evap+2*q[1].evap+2*q[2].evap+q[3].evap)/6;
 for(int j=0;j<5;j++)x[j]=x[j]+(h/6)*(k[0][j]+2*k[1][j]+2*k[2][j]+k[3][j]);
}
inline void supply_derivative(const double*x,double feed,double target,const double*p,double*out){
 double target_speed=min(p[straightener_speed_m_s]*p[supply_factor],max(0.,target-x[0])/.5);out[0]=x[1]-feed;out[1]=(target_speed-x[1])/.5;
}
inline void supply_rk4(const double*x,double feed,double target,const double*p,double h,double*out){
 double k[4][2],trial[2];supply_derivative(x,feed,target,p,k[0]);
 for(int j=0;j<2;j++)trial[j]=x[j]+.5*h*k[0][j];supply_derivative(trial,feed,target,p,k[1]);
 for(int j=0;j<2;j++)trial[j]=x[j]+.5*h*k[1][j];supply_derivative(trial,feed,target,p,k[2]);
 for(int j=0;j<2;j++)trial[j]=x[j]+h*k[2][j];supply_derivative(trial,feed,target,p,k[3]);
 for(int j=0;j<2;j++)out[j]=x[j]+(h/6)*(k[0][j]+2*k[1][j]+2*k[2][j]+k[3][j]);
}
inline void demand(const double*p,double&peak,double&work){double scale=p[width_mm]/600*p[thickness_mm]/1.5;peak=p[forming_force_n]*scale/max(p[lube_factor],.2);work=p[work_per_stroke_j]*scale*p[progression_mm]/800/max(p[lube_factor],.2);}
inline void drive(State&s,const double*x,const double*p,int&occupied,double&forming,double&electrical,double&loss){
 occupied=(s.feed_strip_m>0||s.completed>0);for(double mass:s.die)occupied+=!std::isnan(mass);
 int count=occupied+(s.running&&!(s.feed_strip_m>0||s.completed>0));double peak,work;demand(p,peak,work);work=work*count/10;
 forming=s.running?work*max(x[0],0.)/60:0.;double mloss=s.running?5000.:1000.;electrical=(forming+mloss)/p[efficiency];loss=electrical-forming;
}
extern "C" int line_queue(State*s,int index,double*out,int capacity){auto&q=index==0?s->discharge:s->washer;if((int)q.size()>capacity)return -1;int i=0;for(auto&row:q){for(int j=0;j<4;j++)out[4*i+j]=row[j];i++;}return i;}
extern "C" int line_advance(State*sp,double t,double*x,double u,double ambient,const double*p,double duration,double stop,Event*events,int capacity,int*out_count,double*scalars,double*die,double*counts){
 State&s=*sp;s.stop_requested=stop;int ne=0,iterations=0;double now=t,end=t+duration;
 auto emit=[&](double when,int kind,double count){if(ne>=capacity)return false;events[ne++]={when,double(kind),count};return true;};
 while(now<end-1e-10){
  if(++iterations>10000000)return -3;
  double cycle=60/max(x[0],.01),pitch=p[progression_mm]*.001;int batch=!std::isnan(s.die[8])?int(p[parts_per_stroke]):0;
  s.blocked=s.discharge.size()+batch>p[buffer_parts]||s.scrap_kg>=20.;double peak,work;demand(p,peak,work);
  s.running=!s.stop_requested&&bool(p[run_enable])&&!s.blocked&&x[2]>=2&&x[4]>1&&s.loop_m>=pitch-s.feed_strip_m-1e-9&&!s.feed_failed&&peak<=p[capacity_n]&&2*work/peak<=p[stroke_mm]*.001;
  int occupied;double forming,electrical,loss;drive(s,x,p,occupied,forming,electrical,loss);
  if(electrical>p[motor_kw]*1000){s.running=0;drive(s,x,p,occupied,forming,electrical,loss);}
  double feed_phase=p[feed_window_s]/cycle,boundary=s.phase<feed_phase-1e-9?feed_phase:1.;
  double h=min({p[integration_step_s],end-now,s.running?(boundary-s.phase)*cycle:.1});
  if(s.change_until>now+1e-9)h=min(h,s.change_until-now);
  if(!s.washer.empty()&&s.washer.front()[0]>now+1e-9)h=min(h,s.washer.front()[0]-now);
  if(!s.discharge.empty()&&s.discharge.front()[0]>now+1e-9)h=min(h,s.discharge.front()[0]-now);
  if(!(h>0)||!std::isfinite(h))return -3;
  s.energy_in+=electrical*h;s.energy_forming+=forming*h;s.energy_loss+=loss*h;
  double duty=s.running&&s.phase>=.5?occupied/10.:0.;s.integration_steps+=1;rk4(x,u,ambient,p,duty,h,s);
  for(auto&row:s.washer){double mass=row[1],exchange=(x[1]-row[3])*mass*500*.02*h;s.water_energy_out+=exchange;x[1]-=exchange/(max(x[3],1.)*4180);row[3]+=exchange/(mass*500);row[2]+=h*max(0.,(x[1]-35)/25)*p[spray_factor]*p[spray_factor];}
  double target=p[loop_capacity_m]*.5;
  if(s.remaining_kg<=1e-9){if(!s.coil_change_until)s.coil_change_until=now+p[coil_change_s];else if(now>=s.coil_change_until){s.remaining_kg=p[coil_mass_kg];s.initial_kg+=p[coil_mass_kg];s.coils_loaded+=1;s.coil_change_until=0.;}}
  double feed_rate=s.running&&s.phase<feed_phase-1e-9?min({pitch-s.feed_shaft_m,pitch/p[feed_window_s]*h,p[feeder_speed_m_s]*h})*p[feed_traction]/h:0.;
  if(s.feed_failed&&p[feed_traction]>=.999)feed_rate=min(pitch-s.feed_strip_m,p[feeder_speed_m_s]*h)/h;
  double supply_x[2]={s.loop_m,s.straightener_speed},supply_next[2];supply_rk4(supply_x,feed_rate,target,p,h,supply_next);
  double average_speed=max(0.,(supply_next[0]-s.loop_m)/h+feed_rate);s.straightener_speed=max(0.,supply_next[1]);
  s.payout=min({average_speed,max(0.,p[loop_capacity_m]-s.loop_m)/max(h,1e-12),s.remaining_kg/s.linear_mass/max(h,1e-12)});
  s.loop_m+=s.payout*h;s.remaining_kg-=s.payout*h*s.linear_mass;
  double route=p[scrap_route_code]==1?.4:p[scrap_route_code]==2?.5:.9;double removed=min(s.scrap_kg,route*p[scrap_factor]*h);s.scrap_kg-=removed;s.scrap_removed_kg+=removed;
  if(s.running&&s.phase<feed_phase-1e-9){double shaft=min({pitch-s.feed_shaft_m,pitch/p[feed_window_s]*h,p[feeder_speed_m_s]*h}),strip=min(shaft*p[feed_traction],s.loop_m);s.feed_shaft_m+=shaft;s.feed_strip_m+=strip;s.feed_mass_kg+=strip*s.linear_mass;s.loop_m-=strip;s.consumed_kg+=strip*s.linear_mass;}
  else if(s.feed_failed&&p[feed_traction]>=.999){double strip=min({pitch-s.feed_strip_m,p[feeder_speed_m_s]*h,s.loop_m});s.feed_shaft_m+=strip;s.feed_strip_m+=strip;s.feed_mass_kg+=strip*s.linear_mass;s.loop_m-=strip;s.consumed_kg+=strip*s.linear_mass;if(s.feed_strip_m>=pitch-1e-9){s.feed_complete=1;s.feed_failed=0;if(!emit(now+h,2,1))return -2;}}
  if(s.running)s.phase+=h/cycle;
  if(s.phase>=feed_phase-1e-9&&!s.feed_complete){s.feed_complete=s.feed_strip_m>=pitch-1e-9;if(s.feed_complete&&!emit(now+h,2,1))return -2;if(!s.feed_complete){s.feed_failed=1;s.running=0;}}
  now+=h;
  if(s.phase>=1-1e-9){
   s.phase=0.;s.completed+=1;s.last_pitch=p[progression_mm]*p[feed_traction];double mass=s.feed_mass_kg,scrap=mass*p[trim_fraction],part_mass=mass-scrap;s.scrap_kg+=scrap;
   double outgoing=s.die[8];for(int i=8;i>0;i--)s.die[i]=s.die[i-1];s.die[0]=part_mass;s.die_mass_kg+=part_mass;
   if(!std::isnan(outgoing)){s.die_mass_kg-=outgoing;s.output_mass_kg+=outgoing;s.produced+=int(p[parts_per_stroke]);for(int i=0;i<int(p[parts_per_stroke]);i++)s.discharge.push_back({now+3.,outgoing/p[parts_per_stroke],0,0});if(!emit(now,4,s.produced))return -2;}
   if(!emit(now,1,s.completed)||!emit(now,2,0))return -2;s.feed_shaft_m=0.;s.feed_strip_m=0.;s.feed_mass_kg=0.;s.feed_complete=0;
  }
  while(!s.washer.empty()&&s.washer.front()[0]<=now+1e-9&&s.pack_queue<p[buffer_parts]){auto row=s.washer.front();s.washer.pop_front();if(row[2]>=30.)s.pack_queue+=1;else s.rejected+=1;}
  if(!s.discharge.empty()&&s.discharge.front()[0]<=now+1e-9&&now>=s.next_wash-1e-9&&s.washer.size()<p[buffer_parts]){auto row=s.discharge.front();s.discharge.pop_front();double transit=p[washer_length_m]/p[washer_speed_m_min]*60;s.wash_qualified=x[1]>=50&&p[spray_factor]>=.7;s.washer.push_back({now+transit,row[1],0.,20.});s.next_wash=now+p[part_spacing_m]/p[washer_speed_m_min]*60;}
  if(now>=s.change_until&&s.pack_queue){
   s.pack_credit+=h*p[packers]*p[packing_rate_per_min]/60*p[packing_factor]*(1+.1*std::sin(now/30));
   while(s.pack_credit>=1-1e-9&&s.pack_queue){s.pack_credit-=1;s.pack_queue-=1;s.packed+=1;s.container_fill+=1;if(!emit(now,5,s.packed))return -2;if(s.container_fill>=p[container_parts]){s.containers+=1;s.container_fill=0;s.change_until=now+p[container_change_s];s.pack_credit=0;break;}}
  }else if(!s.pack_queue)s.pack_credit=0.;
  for(int j=0;j<5;j++)if(!std::isfinite(x[j]))return -1;
  if(s.discharge.size()>100000||s.washer.size()>100000)return -4;
 }
 *out_count=ne;output(s,scalars,die,counts);return 0;
}
