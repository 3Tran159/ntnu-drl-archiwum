"""Train a pitch-only TD3 pilot on the NTNU XFOIL lookup and wave preview."""
from copy import deepcopy
import csv
import ctypes
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from numpy.random import default_rng

OUT = Path(__file__).resolve().parent
sys.path.append(str(OUT.parents[1] / "td3_cpu_deps_312"))
import torch
from torch import nn

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
if os.name == "nt":
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 1 << 4):
        raise ctypes.WinError(ctypes.get_last_error())

SEED = 27
DT = .005
U = 18.
PERIOD = .4555125731921526
RATE = 90.
RANGE = .60
AREA_GODO = 25.6 * .312**2
U_GODO = 24 * 1852 / 3600
TARGET = 12500 * 9.81 / (.5 * 1000 * U_GODO**2 * AREA_GODO)
BAND = .01 * TARGET
STEPS = 18000
STEPS_PER_CYCLE = round(PERIOD / DT)
RNG = default_rng(SEED)
torch.manual_seed(SEED)


def load_polar():
    with (OUT.parent/"ANGLES_PM5/XFOIL_CL_CD_ANGLES_PM5.csv").open(newline="") as stream:
        rows=[r for r in csv.DictReader(stream) if float(r["flap_deflection_deg"])==0 and r["status"]=="CONVERGED"]
    a,cl,cd=np.array([[float(r[k]) for k in ("foil_angle_deg","CL","CD")] for r in rows]).T
    if not (np.all(np.diff(a)==.5) and np.all(np.diff(cl)>0)):
        raise ValueError("Pitch-only polar must be complete and monotone")
    return a,cl,cd


def load_wave():
    with (OUT.parent/"XFOIL_PHASE_MAP.csv").open(newline="") as stream:
        rows=list(csv.DictReader(stream))
    phase,ux,uy=np.array([[float(r[k]) for k in ("phase_deg","Ux_m_s","Uy_m_s")] for r in rows]).T
    if not np.array_equal(phase,np.arange(361)):
        raise ValueError("Expected one periodic wave map")
    return ux,uy


ANGLES, CL, CD = load_polar()
WAVE_X, WAVE_Y = load_wave()
TRIM = float(np.interp(TARGET,CL,ANGLES))


def flow(phi, amplitude):
    phase=math.degrees(phi) % 360
    lo=int(phase)
    w=phase-lo
    ux=U+amplitude*((1-w)*WAVE_X[lo]+w*WAVE_X[lo+1]-U)
    uy=amplitude*((1-w)*WAVE_Y[lo]+w*WAVE_Y[lo+1])
    beta=math.atan2(uy,ux)
    return ux,uy,beta,(ux*ux+uy*uy)/U**2


def force(theta, fluid):
    _,_,beta,scale=fluid
    alpha=theta+math.degrees(beta)
    if not ANGLES[0]<=alpha<=ANGLES[-1]:
        raise ValueError(f"Out-of-polar angle {alpha}")
    cl=np.interp(alpha,ANGLES,CL)
    cd=np.interp(alpha,ANGLES,CD)
    s,c=math.sin(beta),math.cos(beta)
    return float(scale*(cl*c+cd*s)),float(scale*(cd*c-cl*s))


def inverse(fluid):
    _,_,beta,scale=fluid
    actual=scale*(CL*math.cos(beta)+CD*math.sin(beta))
    if not actual[0]<=TARGET<=actual[-1]:
        raise ValueError("Lift target outside polar")
    theta=np.interp(TARGET,actual,ANGLES)-math.degrees(beta)
    return float(np.clip((theta-TRIM)/RANGE,-1,1))


class Environment:
    def reset(self, phase, amplitude, initial=0.):
        self.phase=phase
        self.amplitude=amplitude
        self.theta=TRIM+initial
        self.cl,self.cd=force(self.theta,flow(self.phase,self.amplitude))
        return self.observe()

    def preview(self):
        return flow(self.phase+2*math.pi*DT/PERIOD,self.amplitude)

    def observe(self):
        u,w,_,_=self.preview()
        return np.array([(u-U)/.06,w/.06,(self.theta-TRIM)/RANGE,
                         np.clip((self.cl-TARGET)/(4*BAND),-3,3)],dtype=np.float32)

    def step(self, action):
        want=TRIM+RANGE*float(np.clip(action,-1,1))
        change=float(np.clip(want-self.theta,-RATE*DT,RATE*DT))
        self.theta+=change
        self.phase+=2*math.pi*DT/PERIOD
        self.cl,self.cd=force(self.theta,flow(self.phase,self.amplitude))
        error=(self.cl-TARGET)/BAND
        reward=-error**2-.15*(self.cd-.007)/.001-.01*(change/(RATE*DT))**2
        return self.observe(),reward


def model(inputs, final_tanh=False):
    layers=[nn.Linear(inputs,64),nn.ReLU(),nn.Linear(64,64),nn.ReLU(),nn.Linear(64,1)]
    if final_tanh:
        layers.append(nn.Tanh())
    return nn.Sequential(*layers)


def evaluate(policy, amplitude=1., phases=(.37,2.21,4.13)):
    data=[]
    for episode,phase in enumerate(phases):
        env=Environment()
        observation=env.reset(phase,amplitude)
        for i in range(5*STEPS_PER_CYCLE):
            action=policy(observation,env)
            observation,reward=env.step(action)
            if i>=STEPS_PER_CYCLE:
                data.append((episode,(i+1)*DT,env.cl,env.cd,env.theta,reward))
    arr=np.array(data)
    errors=100*(arr[:,2]-TARGET)/TARGET
    return {"cl_mean":float(arr[:,2].mean()),"in_band_pct":float(100*np.mean(np.abs(errors)<=1)),
            "cl_rms_pct":float(np.sqrt(np.mean(errors**2))),"cl_max_abs_pct":float(np.max(abs(errors))),
            "cd_x_mean":float(arr[:,3].mean()),"reward_mean":float(arr[:,5].mean())},arr


def save_csv(path,header,rows):
    with path.open("w",newline="",encoding="utf8") as file:
        writer=csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    actor, q1, q2=model(4,True),model(5),model(5)
    targets=[deepcopy(network).requires_grad_(False) for network in (actor,q1,q2)]
    actor_opt=torch.optim.Adam(actor.parameters(),lr=2e-4)
    critic_opt=torch.optim.Adam([*q1.parameters(),*q2.parameters()],lr=6e-4)
    buf=np.zeros((STEPS,10),dtype=np.float32)
    env=Environment()
    observation=env.reset(0.,1.)
    best_score=-float("inf")
    learning=[]
    for step in range(STEPS):
        if step%(5*STEPS_PER_CYCLE)==0:
            observation=env.reset(RNG.uniform(0,2*np.pi),RNG.uniform(.85,1.15),RNG.uniform(-.06,.06))
        with torch.no_grad():
            if step<800:
                action=RNG.uniform(-.8,.8)
            elif step<2300:
                action=inverse(env.preview())+RNG.normal(0,.13)
            else:
                action=actor(torch.from_numpy(observation)).item()+RNG.normal(0,.08)
        action=np.clip(action,-1,1)
        next_obs,reward=env.step(action)
        buf[step]=np.r_[observation,action,reward,next_obs]
        observation=next_obs
        if step>=800:
            batch=torch.from_numpy(buf[RNG.integers(0,step+1,128)])
            obs,act,rew,nxt=batch[:,:4],batch[:,4:5],batch[:,5:6],batch[:,6:]
            with torch.no_grad():
                noise=(torch.randn_like(act)*.025).clamp(-.05,.05)
                nxt_act=(targets[0](nxt)+noise).clamp(-1,1)
                features=torch.cat((nxt,nxt_act),dim=1)
                y=rew+.90*torch.minimum(targets[1](features),targets[2](features))
            features=torch.cat((obs,act),dim=1)
            loss=nn.functional.mse_loss(q1(features),y)+nn.functional.mse_loss(q2(features),y)
            critic_opt.zero_grad()
            loss.backward()
            critic_opt.step()
            if step%2==0:
                actor_loss=-q1(torch.cat((obs,actor(obs)),dim=1)).mean()
                actor_opt.zero_grad()
                actor_loss.backward()
                actor_opt.step()
                with torch.no_grad():
                    for live,target in zip((actor,q1,q2),targets):
                        for source,dest in zip(live.parameters(),target.parameters()):
                            dest.lerp_(source,.005)
        if step in (0,799,2299) or (step+1)%1000==0:
            with torch.no_grad():
                v,_=evaluate(lambda obs,e:actor(torch.from_numpy(obs)).item(),phases=(0.84,3.15))
            learning.append((step+1,v["reward_mean"],v["cl_rms_pct"],v["in_band_pct"],v["cd_x_mean"]))
            score=v["reward_mean"]
            if step>=2300 and score>best_score:
                best_score=score
                best=deepcopy(actor.state_dict())
                best_step=step+1
            print(step+1,v,flush=True)
    actor.load_state_dict(best)
    actor.eval()
    torch.jit.trace(actor,torch.zeros(4)).save(str(OUT/"TD3_PITCH_POLICY.pt"))
    save_csv(OUT/"TRAINING_HISTORY.csv",["step","reward_mean","cl_rms_pct","in_band_pct","cd_x_mean"],learning)
    results={}
    policies={"fixed_trim":lambda obs,e:0.,"xfoil_inverse":lambda obs,e:inverse(e.preview()),
              "td3_pitch":lambda obs,e:actor(torch.from_numpy(obs)).item()}
    with torch.no_grad():
        for label,policy in policies.items():
            results[label],rows=evaluate(policy)
            save_csv(OUT/(label+"_eval.csv"),["episode","time_s","CL_vertical","CD_x","foil_pitch_deg","reward"],rows)
    result={"status":"XFOIL_DIAGNOSTIC_ONLY","CL_target":TARGET,"band_1pct":[TARGET-BAND,TARGET+BAND],
            "godo_mass_kg":12500,"godo_mean_chord_m":.312,"godo_aspect_ratio":25.6,"godo_area_m2_inferred":AREA_GODO,
            "godo_speed_m_s":U_GODO,"assumed_density_kg_m3":1000,"weight_balance_ignores_buoyancy":True,
            "training_interactions":STEPS,"selected_checkpoint_step":best_step,"seed":SEED,
            "trim_deg":TRIM,"action_residual_limit_deg":RANGE,"pitch_rate_limit_deg_s":RATE,
            "flap_deg":0,"controller_dt_s":DT,"wave_period_s":PERIOD,
            "observation":["(preview_Ux-18)/0.06","preview_Uy/0.06","(pitch-trim)/0.6",
                           "clip((CL-target)/(4*band),-3,3)"],
            "evaluation":"Three held-out initial phases of the same nominal wave, four periods after one discarded period",
            "evaluation_results":results,"urans_validation":False}
    (OUT/"TD3_XFOIL_PILOT_RESULT.json").write_text(json.dumps(result,indent=2),encoding="utf8")
    print(json.dumps(result,indent=2),flush=True)


if __name__=="__main__":
    main()
