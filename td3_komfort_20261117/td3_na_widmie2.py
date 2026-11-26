"""td3_na_widmie.py - 18.11: polityki TD3 (uczone TYLKO na fali regularnej God0) na widmie S1-S4, ta sama realizacja co MPC (seed 100*nr, 300 s, srednie 30-300 s).
Model Faltinsena B, 90 %. Wynik: TD3_WIDMO_bez_stopu.json. Porownanie z MPC W_A 3 (wyniki_act57_wa3)."""
import json, sys, time
from pathlib import Path
import numpy as np, torch, torch.nn as nn, psutil
psutil.Process().cpu_affinity([23]); psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS); torch.set_num_threads(1)
H = Path(__file__).parent
import godo_falt_env as E
E.S2, E.Z2 = -10.0, 1.5   # bez konca epizodu przy zanurzeniu < 1c (jak MPC: liczymy dalej, tylko notujemy); stop dopiero |z| > 1,5 m
SEAS = {"S1": (1.5, 5.0), "S2": (1.0, 3.5), "S3": (1.5, 8.0), "S4": (2.25, 6.0)}
POL = {"TD3 W_A 0 (final)": H / "runs" / "TD3K_WA0" / "final_actor.pt", "TD3 W_A 1.5 (best reward)": H / "runs" / "TD3K_WA1.5" / "best_any_actor.pt"}
out = {}
for pn, pf in POL.items():
    net = nn.Sequential(nn.Linear(5, 256), nn.ReLU(), nn.Linear(256, 256), nn.ReLU(), nn.Linear(256, 1), nn.Tanh()); net.load_state_dict(torch.load(pf, weights_only=False)); net.eval()
    for s, (Hs, Tp) in SEAS.items():
        env = E.GodoVortexEnv(random_phase=False); wp = 2 * np.pi / Tp
        env.plant.set_irregular(Hs=Hs, Tp=Tp, gamma=3.3, seed=100 * int(s[1]), N=80, wmin=0.5 * wp, wmax=3.0 * wp)
        env.n_ticks = 30000; o, _ = env.reset(); rows = []; done = False; term = False
        while not done:
            with torch.no_grad(): a = net(torch.as_tensor(o).unsqueeze(0)).numpy()[0]
            o, r, term, trunc, info = env.step(a); done = term or trunc
            rows.append((env.plant.t, info["P_drag_W"], E.U * info["D_strut"], info["acc"], info["sub"], info["z"]))
        A = np.array(rows); b = A[A[:, 0] > 30.0]
        res = dict(lot_s=float(A[-1, 0]), wyskoczyl=bool(term))
        if len(b) > 100:
            res.update(P_foil_W=float(b[:, 1].mean()), P_strut_W=float(b[:, 2].mean()), acc_rms=float(b[:, 3].std()), sub_min=float(b[:, 4].min()),
                       below_1c_pct=float(100 * np.mean(b[:, 4] < E.C)), z_mean=float(b[:, 5].mean()))
        out[f"{pn}|{s}"] = res; print(pn, s, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items()}, flush=True)
        (H / "TD3_WIDMO_bez_stopu.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
