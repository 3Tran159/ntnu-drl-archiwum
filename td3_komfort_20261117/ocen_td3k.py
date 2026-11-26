"""ocen_td3k.py - ocena polityk TD3K tym samym harnessem co MPC (mpc_falt_bridge.py test): Faltinsen B, fala Godo, 90 %, 15 okresow, ostatnie 4.
4 fazy fali (0,4 = faza harnessu MPC + 3 przesuniete). Wynik: OCENA_TD3K.json. Uzycie: python ocen_td3k.py [TAG ...]"""
import sys, json, os
from pathlib import Path
import numpy as np, torch, psutil
psutil.Process().cpu_affinity([23]); psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
HERE = Path(__file__).parent
out = {}
tags = sys.argv[1:] or ["TD3K_WA1.5", "TD3K_WA0"]
for tag in tags:
    os.environ["TD3K_W_A"] = "1.5"           # W_A dotyczy tylko nagrody; ocena mierzy opor i z'' wprost
    import godo_falt_env as E
    import torch.nn as nn
    out[tag] = {}
    for name in ("best_actor.pt", "final_actor.pt", "best_any_actor.pt"):
        f = HERE / "runs" / tag / name
        if not f.exists(): continue
        net = nn.Sequential(nn.Linear(5, 256), nn.ReLU(), nn.Linear(256, 256), nn.ReLU(), nn.Linear(256, 1), nn.Tanh())
        net.load_state_dict(torch.load(f, weights_only=False)); net.eval()
        act = lambda o: net(torch.as_tensor(o, dtype=torch.float32).unsqueeze(0)).detach().numpy()[0]
        out[tag][name] = [dict(phase=ph, **E.harness(act, phase=ph)) for ph in (0.4, 0.4 + np.pi / 2, 0.4 + np.pi, 0.4 + 1.5 * np.pi)]
        print(tag, name, out[tag][name][0], flush=True)
(HERE / "OCENA_TD3K.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
