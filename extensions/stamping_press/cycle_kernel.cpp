// Authoritative RK4 and hybrid-event equations translated from cycles.py/model.py.
// No fast math, surrogate trajectories, output faults or shortened event paths.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
using std::max; using std::min;
constexpr double PI=3.141592653589793238462643383279502884;
enum P {CUT,SHEAR,TRAVEL,J,TORQUE,ETA,BEARING,OTHER,VISCOSITY,WEAR,GUIDE,TRACTION,BACKLASH,OBSTRUCTION,BRAKE_DRAG,PUMP_EFF,FILTER,LEAK,FILM,OIL_CAP,DIE_CAP,BRAKE_COEF,DENSITY,WIDTH,TRIM,SERVO_TAU,HYDRAULIC_TAU,CW_UA,OIL_UA,FEED_GAIN,DESIGN_RATE};
struct State {
 double gate,cycle_work,cycle_pitch,cycle_encoder,phase,completed,good,reject,pitch,encoder,feed_complete,running,token,token_pitch,token_mass,token_thickness;
 double buffer_mass,supplied_mass,withdrawn_mass,trim_mass,product_mass,inspection,checked,motor_energy,loss_energy,forming_energy,actual_forming_energy,initial_energy,energy_residual,energy_relative_residual;
 double pending_start,pending_count,stop,clutch,paused_work,pending_time[512],pending_dimension[512];
};
struct Event {double time,pitch,count,kind,rejected;};
struct Q {double strip_pitch,rate,work,bearing,forming,motor,pump,demand,pitch_target,consumed,delivery,cooling,film,dimension,brake,other,pump_input,oil_cooling,die_ambient,die_heat,encoder,motor_torque,forming_torque;bool enabled,clutched;};
inline double work(const double *p,const double *d){return .5*(p[CUT]*d[3]*p[SHEAR]*d[2]*p[WEAR]*p[GUIDE])*p[TRAVEL];}
inline double strip_travel(double shaft,const double*d,const double*p){double traction=min(1.,p[TRACTION]/max(.85+d[2]*.15,1e-6));return max(0.,shaft*traction-p[BACKLASH]-p[OBSTRUCTION]);}
inline Q quantities(const double*x,const double*u,const double*d,const double*p,double cw=-1,double cp=-1,int enabled=-1,int clutched=-1){
 Q q{};double w=x[0],pitch=x[1],buf=x[2],pressure=x[3],oil=x[4],die=x[5];
 q.rate=max(w,0.)/(2*PI);q.work=work(p,d);
 double visc=p[VISCOSITY]*std::exp(-.015*(oil-40));
 q.bearing=p[BEARING]*visc*std::pow(max(w,0.)/(2*PI),2);
 q.strip_pitch=strip_travel(pitch,d,p);
 bool permit=pressure>=2&&buf>=.15&&die<=80&&q.work<=2500&&50<q.strip_pitch&&q.strip_pitch<150;
 q.enabled=enabled<0?permit:bool(enabled);
 q.clutched=(clutched<0?q.enabled:bool(clutched))&&q.enabled;
 q.forming=(cw<0?q.work:cw)*q.rate*(q.clutched?1:0);
 q.brake=q.enabled?0:p[BRAKE_COEF]*std::pow(max(w,0.),2);
 double other_ambient=.25*p[OTHER]*std::pow(max(w,0.)/(2*PI),2);
 double die_friction=q.clutched?.75*p[OTHER]*std::pow(max(w,0.)/(2*PI),2)/max(p[FILM],.1):0.;q.other=other_ambient+die_friction;
 q.motor_torque=q.enabled?p[ETA]*p[TORQUE]*u[0]*d[4]:0;q.forming_torque=q.clutched?(cw<0?q.work:cw)/(2*PI):0;q.motor=q.motor_torque*max(w,0.);
 q.pump=10*u[3]*p[PUMP_EFF]*d[4]/std::pow(p[FILTER],.2);
 q.demand=pressure/visc+p[LEAK]*std::sqrt(max(pressure,0.));
 double traction=min(1.,p[TRACTION]/max(.85+d[2]*.15,1e-6));
 q.pitch_target=max(0.,p[FEED_GAIN]*u[1]);
 q.encoder=pitch;
 q.consumed=(cp<0?q.strip_pitch*.001:cp)*q.rate*(q.clutched?1:0);
 q.delivery=.2*u[2]/p[BRAKE_DRAG];q.cooling=p[CW_UA]*u[4]*d[5]*(die-d[1]);
 q.pump_input=(pressure*q.pump*100000/60000+100*u[3])/max(p[PUMP_EFF],.05);
 q.oil_cooling=p[OIL_UA]*(oil-d[0]);q.die_ambient=2*(die-d[0]);q.die_heat=.3*q.forming+die_friction;
 q.film=.02*p[FILM]*q.pump;
 q.dimension=100+.012*(die-50)+8*(d[3]/.0012-1)+.2*(q.strip_pitch-100)+.1*(1-p[FILM]);
 return q;
}
inline void deriv(const double*x,const double*p,const Q&q,double*out){
 out[0]=(q.motor_torque-q.forming_torque-(x[0]>0?(q.bearing+q.other+q.brake)/x[0]:0))/p[J];
 out[1]=(q.pitch_target-x[1])/p[SERVO_TAU];out[2]=q.delivery-q.consumed;out[3]=(q.pump-q.demand)/p[HYDRAULIC_TAU];
 out[4]=(q.bearing+q.pump_input-q.oil_cooling)/p[OIL_CAP];out[5]=(q.die_heat-q.cooling-q.die_ambient)/p[DIE_CAP];
}
struct Step {double x[6];Q q[4];double phase;};
inline Step rk4(const double*x,const double*u,const double*d,const double*p,const State&s,double h){
 Step r{};double k[4][6],trial[6];
 r.q[0]=quantities(x,u,d,p,s.cycle_work,s.cycle_pitch,int(s.gate&&!s.stop),int(s.clutch));deriv(x,p,r.q[0],k[0]);
 for(int j=0;j<6;j++)trial[j]=x[j]+.5*h*k[0][j];
 r.q[1]=quantities(trial,u,d,p,s.cycle_work,s.cycle_pitch,int(s.gate&&!s.stop),int(s.clutch));deriv(trial,p,r.q[1],k[1]);
 double rate1=max(trial[0],0.)/(2*PI)*(r.q[1].clutched?1:0);
 for(int j=0;j<6;j++)trial[j]=x[j]+.5*h*k[1][j];
 r.q[2]=quantities(trial,u,d,p,s.cycle_work,s.cycle_pitch,int(s.gate&&!s.stop),int(s.clutch));deriv(trial,p,r.q[2],k[2]);
 double rate2=max(trial[0],0.)/(2*PI)*(r.q[2].clutched?1:0);
 for(int j=0;j<6;j++)trial[j]=x[j]+h*k[2][j];
 r.q[3]=quantities(trial,u,d,p,s.cycle_work,s.cycle_pitch,int(s.gate&&!s.stop),int(s.clutch));deriv(trial,p,r.q[3],k[3]);
 double rate3=max(trial[0],0.)/(2*PI)*(r.q[3].clutched?1:0);
 r.phase=h*(r.q[0].rate*(r.q[0].clutched?1:0)+2*rate1+2*rate2+rate3)/6;
 for(int j=0;j<6;j++)r.x[j]=x[j]+(h/6)*(k[0][j]+2*k[1][j]+2*k[2][j]+k[3][j]);return r;
}
inline double margin(const double*x,const double*d,const double*p,bool enabled){
 if(enabled)return min({x[3]-2.,x[2]-.15,80-x[5],2500-work(p,d),strip_travel(x[1],d,p)-50.,150-strip_travel(x[1],d,p)});
 return min({x[3]-2.5,x[2]-.25,75-x[5],2200-work(p,d),strip_travel(x[1],d,p)-55.,145-strip_travel(x[1],d,p)});
}
inline double fraction(double phase){double a=max(0.,min(1.,(phase-.5)*2));return a<=.5?2*a*a:1-2*std::pow(1-a,2);}
inline double quadrature(const Step&r,double Q::*member,double h){return h*(r.q[0].*member+2*(r.q[1].*member)+2*(r.q[2].*member)+r.q[3].*member)/6;}
inline double clutch_margin(const double*x,const double*p,const State&s){return .5*p[J]*x[0]*x[0]-(s.paused_work*(s.phase-fraction(s.phase))+.5*p[J]);}
inline bool change_work(double*x,const double*p,State&s,double newwork){double energy=.5*p[J]*x[0]*x[0]+(s.cycle_work-newwork)*(s.phase-fraction(s.phase));if(energy<0)return false;x[0]=std::sqrt(2*energy/p[J]);s.cycle_work=newwork;return true;}
extern "C" int press_advance(double t,double*x,const double*u,const double*d,const double*p,State*s,double dt,int nsub,Event*events,int capacity,int*out_count){
 int ne=0,iterations=0;
 auto emit=[&](double now,double pitch,double kind,double rejected){if(ne>=capacity)return false;events[ne++]={now,pitch,s->completed,kind,rejected};return true;};
 for(int sub=0;sub<nsub;sub++){
  double now=t+sub*dt,remaining=dt;
  while(remaining>1e-12){
   if(++iterations>10000000)return -4;
   double m=margin(x,d,p,bool(s->gate));if(s->gate&&m < -1e-9)s->gate=0;else if(!s->gate&&m>1e-9)s->gate=1;
   bool drive_enabled=s->gate&&!s->stop;
   if(s->clutch&&!drive_enabled){s->paused_work=s->cycle_work;if(!change_work(x,p,*s,0))return -1;s->clutch=0;}
   else if(!s->clutch&&drive_enabled&&clutch_margin(x,p,*s)>=-1e-9){if(!change_work(x,p,*s,s->paused_work))return -1;s->clutch=1;}
   if(s->clutch&&s->phase<=1e-12){s->cycle_pitch=strip_travel(x[1],d,p)*.001;s->cycle_encoder=quantities(x,u,d,p).encoder;}
   Q q=quantities(x,u,d,p,s->cycle_work,s->cycle_pitch,int(s->gate&&!s->stop),int(s->clutch));
   double rate=max(q.rate,1e-12),next=s->phase<.5-1e-10?.5:1.,left=next-s->phase;
   Q base=quantities(x,u,d,p);double accel[6];deriv(x,p,base,accel);
   double discriminant=max(0.,rate*rate+2*(accel[0]/(2*PI))*left);
   double crossing=2*left/max(rate+std::sqrt(discriminant),1e-12);
   double h=q.clutched?min({remaining,crossing,.5}):min(remaining,.5);if(s->pending_count>0)h=min(h,max(s->pending_time[int(s->pending_start)]-now,1e-12));bool boundary=q.clutched&&crossing<=h;
   if(!(h>0)||!std::isfinite(h))return -4;
   Step r{};
   for(int locate=0;locate<8;locate++){
    r=rk4(x,u,d,p,*s,h);if(!boundary||std::abs(r.phase-left)<1e-11)break;h*=left/max(r.phase,1e-12);
   }
   double mend=margin(r.x,d,p,bool(s->gate));bool gate_cross=(s->gate&&mend < -1e-10)||(!s->gate&&mend>1e-10);
   bool spin_cross=!s->clutch&&drive_enabled&&clutch_margin(r.x,p,*s)>1e-10;
   if(gate_cross||spin_cross){
    double limits[2]={std::numeric_limits<double>::infinity(),std::numeric_limits<double>::infinity()};
    for(int event=0;event<2;event++){
     if((event==0&&!gate_cross)||(event==1&&!spin_cross))continue;
     double lo=0,hi=h;
     for(int locate=0;locate<40;locate++){
      double mid=(lo+hi)*.5;Step trial=rk4(x,u,d,p,*s,mid);
      double mm=event==0?margin(trial.x,d,p,bool(s->gate)):clutch_margin(trial.x,p,*s);
      bool crossed=event==0?(s->gate?mm<0:mm>0):mm>0;
      if(crossed)hi=mid;else lo=mid;if(hi-lo<1e-10)break;
     }limits[event]=(lo+hi)*.5;
    }
    // Python compares (time, event-name): gate precedes spin at equal time.
    bool gate_first=limits[0]<=limits[1];h=gate_first?limits[0]:limits[1];gate_cross=gate_first;spin_cross=!gate_first;
    r=rk4(x,u,d,p,*s,h);boundary=false;
   }
   for(int j=0;j<6;j++){x[j]=r.x[j];if(!std::isfinite(x[j]))return -1;}
   double incoming=quadrature(r,&Q::delivery,h)*p[WIDTH]*d[3]*p[DENSITY];s->supplied_mass+=incoming;s->buffer_mass+=incoming;
   s->motor_energy+=quadrature(r,&Q::motor,h);s->loss_energy+=quadrature(r,&Q::bearing,h)+quadrature(r,&Q::other,h)+quadrature(r,&Q::brake,h);
   s->forming_energy+=quadrature(r,&Q::forming,h);s->actual_forming_energy+=s->cycle_work*(fraction(s->phase+r.phase)-fraction(s->phase));
   s->phase+=r.phase;now+=h;remaining-=h;
   if(next==.5&&s->phase>=.5-1e-10&&!s->token){
    double pitch=max(s->cycle_pitch*1000,0.);s->pitch=pitch;s->encoder=s->cycle_encoder;double mass=pitch*.001*p[WIDTH]*d[3]*p[DENSITY];
    bool permit=x[3]>=2&&s->buffer_mass>=mass&&50<q.strip_pitch&&q.strip_pitch<150&&x[0]>1;s->feed_complete=permit?1:0;
    double old=s->cycle_pitch;s->cycle_pitch=permit?pitch*.001:0;x[2]+=(old-s->cycle_pitch)*s->phase;
    double newwork=permit?work(p,d):0, potential=s->phase-fraction(s->phase);
    double energy=.5*p[J]*x[0]*x[0]+(s->cycle_work-newwork)*potential;if(energy<0)return -1;
    x[0]=std::sqrt(2*energy/p[J]);s->cycle_work=newwork;s->paused_work=newwork;
    if(permit){s->buffer_mass-=mass;s->withdrawn_mass+=mass;s->token=1;s->token_pitch=pitch;s->token_mass=mass;s->token_thickness=d[3];if(!emit(now,pitch,2,0))return -2;}
   }
   if(s->phase>=1-1e-10){
    s->phase=0;s->cycle_pitch=!s->token?strip_travel(x[1],d,p)*.001:0;s->cycle_encoder=quantities(x,u,d,p).encoder;bool permit=s->token&&x[3]>=2&&x[0]>1;s->running=permit?1:0;
    if(permit){double pitch=s->token_pitch,mass=s->token_mass;s->token=0;s->completed+=1;s->cycle_pitch=strip_travel(x[1],d,p)*.001;
     s->trim_mass+=mass*p[TRIM];s->product_mass+=mass*(1-p[TRIM]);double part_x[6],part_d[6];for(int j=0;j<6;j++){part_x[j]=x[j];part_d[j]=d[j];}part_x[1]=pitch;part_d[3]=s->token_thickness;double dim=100+.012*(x[5]-50)+8*(s->token_thickness/.0012-1)+.2*(pitch-100)+.1*(1-p[FILM]);bool rejected=std::abs(dim-100)>.25;
     int count=int(s->pending_count),start=int(s->pending_start);if(count>=512)return -3;int at=(start+count)%512;
     s->pending_time[at]=now+10;s->pending_dimension[at]=dim;s->pending_count=count+1;
     if(!emit(now,pitch,1,rejected?1:0))return -2;s->feed_complete=0;
    }else if(!emit(now,std::numeric_limits<double>::quiet_NaN(),0,0))return -2;
   }
   if(gate_cross)s->gate=!bool(s->gate);
   if(spin_cross){if(!change_work(x,p,*s,s->paused_work))return -1;s->clutch=1;}
   while(s->pending_count>0&&s->pending_time[int(s->pending_start)]<=now+1e-10){int at=int(s->pending_start);double dim=s->pending_dimension[at];s->inspection=s->checked=dim;s->pending_start=(at+1)%512;s->pending_count-=1;bool rejected=std::abs(dim-100)>.25;s->reject+=rejected?1:0;s->good+=rejected?0:1;if(!emit(now,dim,3,0))return -2;events[ne-1].count=s->good+s->reject;}
   double stored=.5*p[J]*x[0]*x[0]+s->cycle_work*(s->phase-fraction(s->phase))-s->initial_energy;
   s->energy_residual=s->motor_energy-s->loss_energy-s->actual_forming_energy-stored;s->energy_relative_residual=std::abs(s->energy_residual)/max(s->motor_energy,1.);
  }
 }
 *out_count=ne;return 0;
}
extern "C" std::uint64_t press_state_size(){return sizeof(State);}
extern "C" std::uint64_t press_event_size(){return sizeof(Event);}
extern "C" int press_abi_version(){return 7;}
