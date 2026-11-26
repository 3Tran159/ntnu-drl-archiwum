"""demo_td3k.py - co 4 min: aktualna polityka TD3 (z ckpt.pt, bez szumu) leci 8 okresow na fali Godo w Faltinsenie B -> runs/<TAG>/demo_ep.json
(do animacji w TD3K_LIVE.html). Rdzen 22, priorytet Idle. Konczy sie, gdy oba treningi maja DONE albo STOP."""
import json, os, time
from pathlib import Path
import numpy as np, torch, torch.nn as nn, psutil
psutil.Process().cpu_affinity([22]); psutil.Process().nice(psutil.IDLE_PRIORITY_CLASS); torch.set_num_threads(1)
HERE = Path(__file__).parent
import godo_falt_env as E
TAGS = ["TD3K_WA1.5", "TD3K_WA0"]


def actor_from(run):
    f = run / "ckpt.pt"
    if not f.exists(): return None, None
    d = torch.load(f, weights_only=False); net = nn.Sequential(nn.Linear(5, 256), nn.ReLU(), nn.Linear(256, 256), nn.ReLU(), nn.Linear(256, 1), nn.Tanh())
    net.load_state_dict(d["agent"]["actor"]); net.eval(); meta = json.loads((run / "meta.json").read_text()); return net, meta


while True:
    for tag in TAGS:
        run = HERE / "runs" / tag
        try:
            net, meta = actor_from(run)
            if net is None: continue
            env = E.GodoVortexEnv(n_periods=8, random_phase=False); o, _ = env.reset(options={"phase": 0.4}); R = dict(z=[], th=[], cmd=[], eta=[], acc=[], P=[]); done = False
            while not done:
                a = net(torch.as_tensor(o).unsqueeze(0)).detach().numpy()[0]
                o, r, term, trunc, info = env.step(a); done = term or trunc
                for k, v in (("z", info["z"]), ("th", info["theta_deg"]), ("cmd", float(a[0]) * E.TH_MAX_DEG), ("eta", info["eta"]), ("acc", info["acc"]), ("P", info["P_drag_W"])):
                    R[k].append(round(float(v), 4))
            n = len(R["z"]); h = slice(max(0, n - 4 * 194), n)
            out = dict(tag=tag, step=meta["step"], episode=meta["episode"], term=bool(term), dt=0.01, ome=float(env.plant.ome), k=float(env.plant.k), depth=E.DEPTH, chord=E.C,
                       dP_pct=round(100 * (np.mean(R["P"][h]) / E.P_CALM_FOIL_W - 1), 2), acc_rms=round(float(np.std(R["acc"][h])), 3), time=time.strftime("%H:%M:%S"), **R)
            t = run / "demo_ep.tmp"; t.write_text(json.dumps(out)); os.replace(t, run / "demo_ep.json")
        except Exception as e:
            print(tag, "demo:", e, flush=True)
    if all((HERE / "runs" / t / "DONE").exists() or (HERE / "runs" / t / "STOP").exists() for t in TAGS): break
    time.sleep(240)
