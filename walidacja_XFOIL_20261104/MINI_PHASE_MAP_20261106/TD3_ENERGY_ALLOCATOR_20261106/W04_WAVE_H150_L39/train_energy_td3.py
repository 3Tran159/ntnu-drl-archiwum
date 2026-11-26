"""TD3 wave-energy pilot with separate pitch, flap, and joint allocation."""
from copy import deepcopy
import csv
import json
import math
from pathlib import Path
import sys

import numpy as np

OUT=Path(__file__).resolve().parent
BASE=OUT.parent.parent
sys.path.insert(0,str(BASE/"TD3_GODO_LOAD_PILOT"))
from train_td3 import torch, nn, U, TARGET, TRIM, save_csv

HEIGHT = 1.50
WAVELENGTH = 38.99857691441418
SUBMERGENCE = 2.0
G = 9.81
K = 2 * math.pi / WAVELENGTH
OMEGA = math.sqrt(G * K)
PERIOD = 2 * math.pi / (OMEGA + K * U)
DT = PERIOD / round(PERIOD / .005)
ORBITAL = HEIGHT / 2 * OMEGA * math.exp(-K * SUBMERGENCE)
TRAIN_SCALE = (0.92, 1.08)
PITCH_STATIC = min(TRIM, 4.96 - math.degrees(math.asin(ORBITAL * TRAIN_SCALE[1] / U)))


def flow(phi, amplitude):
    """Deep-water linear wave, running upstream in the foil frame."""
    orbital = amplitude * ORBITAL
    ux = U - orbital * math.cos(phi)
    uy = orbital * math.sin(phi)
    return ux, uy, math.atan2(uy, ux), (ux*ux + uy*uy) / U**2

ANGLES=np.arange(-5,5.01,.5)
FLAPS=np.arange(-1.5,1.51,.5)
RATES=np.array([90.,15.])
LIFT_BAND=.10*TARGET
PITCH_MIN,PITCH_MAX=TRIM-1.25,TRIM+1.25
FLAP_LIMIT=1.5
STEPS=12000
N=round(PERIOD/DT)
MODES=("pitch_only","flap_only","combined")
CAL_PHASES=(.74,3.31)
TEST_PHASES=(.38,2.22,4.16)
AUX=[HEIGHT]


def read_map():
    raw={}
    with (BASE/"ANGLES_PM5/XFOIL_CL_CD_ANGLES_PM5.csv").open(newline="") as file:
        for r in csv.DictReader(file):
            if r["status"]=="CONVERGED":
                raw[(float(r["flap_deflection_deg"]),float(r["foil_angle_deg"]))]=[float(r["CL"]),float(r["CD"])]
    # The usable central strip covers all angles the actuators may command.
    a=ANGLES[ANGLES>=0]
    table=np.array([[raw[(d,x)] for x in a] for d in FLAPS])
    if np.any(np.diff(table[:,:,0],axis=1)<=0) or np.any(np.diff(table[:,:,0],axis=0)<=0):
        raise RuntimeError("XFOIL strip must be monotone in lift")
    return a,table


ALPHAS,POLAR=read_map()


def delta_polar(delta):
    i=int(np.clip(np.searchsorted(FLAPS,delta)-1,0,len(FLAPS)-2))
    w=(delta-FLAPS[i])/(FLAPS[i+1]-FLAPS[i])
    return (1-w)*POLAR[i]+w*POLAR[i+1]


def forces(theta,delta,fluid):
    _,_,beta,scale=fluid
    a=theta+math.degrees(beta)
    if not ALPHAS[0]-1e-7<=a<=ALPHAS[-1]+1e-7:
        raise RuntimeError(f"Angle outside qualified map: {a}")
    polar=delta_polar(delta)
    cl=np.interp(a,ALPHAS,polar[:,0])
    cd=np.interp(a,ALPHAS,polar[:,1])
    return scale*(cl*math.cos(beta)+cd*math.sin(beta)),scale*(cd*math.cos(beta)-cl*math.sin(beta))


def allocation(mode, target, delta_action, fluid):
    _,_,beta,scale=fluid
    s,c=math.sin(beta),math.cos(beta)
    if mode=="flap_only":
        a=PITCH_STATIC+math.degrees(beta)
        local=np.array([np.interp(a,ALPHAS,r[:,0])*c+np.interp(a,ALPHAS,r[:,1])*s for r in POLAR])*scale
        return np.array([PITCH_STATIC,np.interp(target,local,FLAPS)])
    delta=0. if mode=="pitch_only" else FLAP_LIMIT*float(np.clip(delta_action,-1,1))
    p=delta_polar(delta)
    lift=scale*(p[:,0]*c+p[:,1]*s)
    pitch=np.interp(target,lift,ALPHAS)-math.degrees(beta)
    return np.array([np.clip(pitch,max(PITCH_MIN,.06-math.degrees(beta)),min(PITCH_MAX,4.94-math.degrees(beta))),delta])


def calm_reference(mode):
    fluid=(U,0.,0.,1.)
    actions=np.linspace(-1,1,121) if mode=="combined" else [0.]
    candidates=[]
    for action in actions:
        angles=allocation(mode,TARGET,action,fluid)
        cl,cd=forces(*angles,fluid)
        if abs(cl-TARGET)<1e-7:
            candidates.append((cd,*angles))
    return min(candidates)


def steady_drag_slope():
    f=(U,0.,0.,1.)
    def drag(cl):
        return forces(*allocation("pitch_only",cl,0.,f),f)[1]
    return (drag(TARGET+.003)-drag(TARGET-.003))/.006


SLOPE=steady_drag_slope()
CALM={mode:calm_reference(mode) for mode in MODES}


class Env:
    def __init__(self,mode):
        self.mode=mode

    def reset(self,phi,amplitude,initial=None):
        self.phi,self.amplitude=phi,amplitude
        self.angles=allocation(self.mode,TARGET,CALM[self.mode][2]/FLAP_LIMIT,flow(phi,amplitude)) if initial is None else np.array(initial)
        self.cl,self.cd=forces(*self.angles,flow(phi,amplitude))
        return self.obs()

    def preview(self):
        return flow(self.phi+2*math.pi*DT/PERIOD,self.amplitude)

    def obs(self):
        ux,uy,_,_=self.preview()
        return np.array([(ux-U)/ORBITAL,uy/ORBITAL,(self.amplitude-1.)/.08,
                         (self.angles[0]-TRIM)/1.25,self.angles[1]/1.5,
                         (self.cl-TARGET)/LIFT_BAND],dtype=np.float32)

    def step(self,action,bias=0.,fixed=False):
        action=np.clip(action,-1,1)
        fluid=self.preview()
        self.phi+=2*math.pi*DT/PERIOD
        load=TARGET+LIFT_BAND*float(np.clip(action[0]+bias,-1,1))
        desired=self.angles if fixed else allocation(
            self.mode,load,action[1] if self.mode=="combined" else 0.,fluid)
        change=np.clip(desired-self.angles,-RATES*DT,RATES*DT)
        self.angles+=change
        self.cl,self.cd=forces(*self.angles,fluid)
        excess=max(abs(self.cl-TARGET)/LIFT_BAND-1,0)
        reward=-(self.cd-CALM[self.mode][0]-SLOPE*(self.cl-TARGET))/.001-2*excess**2
        reward-=.005*np.sum((change/(RATES*DT))**2)
        return self.obs(),float(reward)


def actor_action(actor,obs):
    with torch.no_grad():
        return actor(torch.from_numpy(obs)).numpy()


def rollout(mode,actor,amp,phases,bias=0.,fixed=False,initial=None):
    data=[]
    for episode,phase in enumerate(phases):
        env=Env(mode)
        obs=env.reset(phase,amp,initial)
        for i in range(5*N):
            a=np.zeros(2) if fixed else actor_action(actor,obs)
            obs,r=env.step(a,bias,fixed)
            if i>=N:
                _,uy,_,_=flow(env.phi,amp)
                data.append((episode,(i+1)*DT,env.cl,env.cd,*env.angles,uy,r))
    return np.array(data)


def trim_bias(mode,actor,amp):
    lo,hi=-2.,2.
    for _ in range(13):
        mid=(lo+hi)/2
        a=rollout(mode,actor,amp,CAL_PHASES,mid)
        if a[:,2].mean()<TARGET:
            lo=mid
        else:
            hi=mid
    return (lo+hi)/2


def metrics(data,calm):
    cl,cd=data[:,2:4].T
    return dict(CL_mean=float(cl.mean()),CL_mean_error_pct=float(100*(cl.mean()/TARGET-1)),
                CL_min=float(cl.min()),CL_max=float(cl.max()),
                CL_in_band_10_pct=float(100*np.mean(abs(cl-TARGET)<=LIFT_BAND)),
                CD_x_mean=float(cd.mean()),delta_CD_vs_calm_pct=float(100*(cd.mean()/calm-1)),
                pitch_range_deg=[float(data[:,4].min()),float(data[:,4].max())],
                flap_range_deg=[float(data[:,5].min()),float(data[:,5].max())],
                CL_Uy_covariance=float(np.mean((cl-cl.mean())*(data[:,6]-data[:,6].mean()))),
                reward_mean=float(data[:,-1].mean()))


def network(n_in,n_out,actor=False):
    layers=[nn.Linear(n_in,64),nn.ReLU(),nn.Linear(64,64),nn.ReLU(),nn.Linear(64,n_out)]
    if actor:
        layers.append(nn.Tanh())
    return nn.Sequential(*layers)


def train(mode,seed):
    rng=np.random.default_rng(seed)
    torch.manual_seed(seed)
    dim=2 if mode=="combined" else 1
    actor=network(6,dim,True)
    q1,q2=(network(6+dim,1) for _ in range(2))
    targets=[deepcopy(n).requires_grad_(False) for n in (actor,q1,q2)]
    ao=torch.optim.Adam(actor.parameters(),lr=2e-4)
    qo=torch.optim.Adam([*q1.parameters(),*q2.parameters()],lr=5e-4)
    buffer=np.empty((STEPS,13+dim),np.float32)
    env=Env(mode)
    learning=[]
    best_score=-float("inf")
    for i in range(STEPS):
        if i%(5*N)==0:
            obs=env.reset(rng.uniform(0,2*np.pi),rng.uniform(*TRAIN_SCALE))
        if i<500:
            action=rng.uniform(-1,1,dim)
        elif i<2300:
            uy=env.preview()[1]
            action=np.array([.86*uy/(ORBITAL*env.amplitude),
                             CALM[mode][2]/FLAP_LIMIT][:dim])+rng.normal(0,.20,dim)
        else:
            action=actor_action(actor,obs)+rng.normal(0,.10,dim)
        action=np.clip(action,-1,1)
        nxt,r=env.step(action)
        buffer[i]=np.r_[obs,action,r,nxt]
        obs=nxt
        if i>=500:
            batch=torch.from_numpy(buffer[rng.integers(0,i+1,128)])
            obs_b,act,rew,next_b=batch[:,:6],batch[:,6:6+dim],batch[:,6+dim:7+dim],batch[:,7+dim:]
            with torch.no_grad():
                next_action=(targets[0](next_b)+(torch.randn_like(act)*.08).clamp(-.15,.15)).clamp(-1,1)
                feat=torch.cat((next_b,next_action),1)
                y=rew+.88*torch.minimum(targets[1](feat),targets[2](feat))
            feat=torch.cat((obs_b,act),1)
            qloss=nn.functional.mse_loss(q1(feat),y)+nn.functional.mse_loss(q2(feat),y)
            qo.zero_grad(); qloss.backward(); qo.step()
            if i%2==0:
                aloss=-q1(torch.cat((obs_b,actor(obs_b)),1)).mean()
                ao.zero_grad(); aloss.backward(); ao.step()
                with torch.no_grad():
                    for live,target in zip((actor,q1,q2),targets):
                        for a,b in zip(live.parameters(),target.parameters()):
                            b.lerp_(a,.005)
        if (i+1)%2000==0:
            v=[metrics(rollout(mode,actor,h/HEIGHT,CAL_PHASES,trim_bias(mode,actor,h/HEIGHT)),CALM[mode][0]) for h in AUX]
            score=float(np.mean([x["reward_mean"]-.15*abs(x["CL_mean_error_pct"]) for x in v]))
            learning.append((i+1,score,*[x["delta_CD_vs_calm_pct"] for x in v]))
            if i>=2300 and score>best_score:
                best_score=score
                best=deepcopy(actor.state_dict())
                best_step=i+1
            print(mode,i+1,round(score,5),flush=True)
    actor.load_state_dict(best)
    actor.eval()
    save_csv(OUT/f"{mode}_seed{seed}_training.csv",["step","validation_score","CD_delta_H150_pct"],learning)

    return actor,best_step,best_score


def main():
    phase = np.arange(720) * 2 * np.pi / 720
    def fixed_at(flap):
        return np.array([forces(PITCH_STATIC,flap,flow(x,1.)) for x in phase])
    lo,hi=-FLAP_LIMIT,FLAP_LIMIT
    for _ in range(30):
        mid=(lo+hi)/2
        if fixed_at(mid)[:,0].mean()<TARGET:
            lo=mid
        else:
            hi=mid
    static_angles=(PITCH_STATIC,(lo+hi)/2)
    assert abs(fixed_at(static_angles[1])[:,0].mean()-TARGET)<1e-6
    report=dict(status="XFOIL_DIAGNOSTIC_ONLY",wave_height_m=HEIGHT,wavelength_m=WAVELENGTH,
                submergence_m=SUBMERGENCE,period_s=PERIOD,orbital_velocity_amplitude_m_s=ORBITAL,
                dt_s=DT,current_m_s=U,common_fixed_pitch_deg=static_angles[0],
                common_fixed_flap_deg=static_angles[1],target_CL=TARGET,instantaneous_CL_band_pct=10,
                rates_deg_s={"pitch":90,"flap":15},load_balance_bias_calibration="separate initial phases",
                mean_lift_reward_multiplier=SLOPE,interactions_per_policy=STEPS,
                observations=["(preview_Ux-18)/orbital","preview_Uy/orbital","(amplitude_scale-1)/.08",
                              "(pitch-trim)/1.25","flap/1.5","(CL-target)/(.1*target)"],
                actuator_work_evaluated=False,heading="Head wave; deep-water Airy kinematics; W04 nominal wavelength and height",
                mode_results={})
    for i,mode in enumerate(MODES):
        seeds=(91+i,191+i)
        results=[(*train(mode,seed),seed) for seed in seeds]
        actor,best_step,_,selected_seed=max(results,key=lambda r:r[2])
        torch.jit.trace(actor,torch.zeros(6)).save(str(OUT/f"{mode}_policy.pt"))
        calm=CALM[mode][0]
        mode_result=dict(selected_step=best_step,selected_seed=selected_seed,tested_seeds=seeds,calm_CD_x=calm,calm_pitch_deg=CALM[mode][1],
                         calm_flap_deg=CALM[mode][2],cases={})
        for h in AUX:
            amp=h/HEIGHT
            bias=trim_bias(mode,actor,amp)
            learned=rollout(mode,actor,amp,TEST_PHASES,bias)
            fixed=rollout(mode,None,amp,TEST_PHASES,fixed=True,initial=static_angles)
            lm,fm=metrics(learned,calm),metrics(fixed,calm)
            lm["CL_in_band_1_pct"]=float(100*np.mean(abs(learned[:,2]/TARGET-1)<=.01))
            lm["delta_CD_vs_same_wave_fixed_pct"]=100*(lm["CD_x_mean"]/fm["CD_x_mean"]-1)
            mode_result["cases"][str(h)]={"policy":lm,"fixed":fm,"normalized_lift_bias":bias,
                "mean_lift_comparable":abs(lm["CL_mean_error_pct"])<=.10 and abs(fm["CL_mean_error_pct"])<=.10}
            save_csv(OUT/f"{mode}_H{int(round(h*100)):03d}.csv",
                     ["episode","t_s","CL_vertical","CD_x","pitch_deg","flap_deg","Uy_m_s","reward"],learned)
        report["mode_results"][mode]=mode_result
        (OUT/"TD3_ENERGY_RESULTS.json").write_text(json.dumps(report,indent=2),encoding="utf8")
        print(mode,"COMPLETE",flush=True)


if __name__=="__main__":
    main()
