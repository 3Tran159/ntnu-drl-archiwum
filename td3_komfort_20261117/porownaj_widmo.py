import json
from pathlib import Path
import numpy as np
H = Path(__file__).parent; M = H.parent / "20261117_mpc_komfort"; SH = Path(r"T:\NTNU_GODO_CONTROL_20261109\60_PANELE_I_WYNIKI\MPC_WIDMO")
PF, PS = 57.06, 12.35 * 85.5 * 0.02 * 1.09
T = json.loads((H / "TD3_WIDMO.json").read_text())
def mpc(s):
    pts = []
    for wa, d in (("0", SH / "wyniki_act57"), ("0.03", M / "wyniki_act57_wa0.03"), ("0.1", M / "wyniki_act57_wa0.1"), ("0.3", M / "wyniki_act57_wa0.3"), ("1", M / "wyniki_act57_wa1"), ("3", M / "wyniki_act57_wa3")):
        f = d / f"{s}__s0.json"
        if f.exists():
            r = json.loads(f.read_text())
            if "error" not in r: pts.append((r["acc_rms"], 100 * (r["P_foil_W"] / PF - 1), 100 * ((r["P_foil_W"] + r["P_strut_W"]) / (PF + PS) - 1), wa))
    return sorted(pts)
for s in ("S1", "S2", "S3", "S4"):
    P = mpc(s); a = np.array([p[0] for p in P]); f = np.array([p[1] for p in P]); t = np.array([p[2] for p in P])
    print(s, "MPC:", " | ".join(f"W_A {p[3]}: z'' {p[0]:.2f}, plat {p[1]:+.1f}, +wsp {p[2]:+.1f}" for p in P))
    for k, r in T.items():
        if not k.endswith(s): continue
        if "P_foil_W" not in r: print("  ", k, "WYSKOCZYL po", r["lot_s"], "s"); continue
        df = 100 * (r["P_foil_W"] / PF - 1); dt = 100 * ((r["P_foil_W"] + r["P_strut_W"]) / (PF + PS) - 1)
        im = (np.interp(r["acc_rms"], a, f), np.interp(r["acc_rms"], a, t)) if a.min() <= r["acc_rms"] <= a.max() else (None, None)
        print("  ", k.split("|")[0], f"z'' {r['acc_rms']:.2f}, plat {df:+.1f}, +wsp {dt:+.1f}, sub_min {r['sub_min']:.2f}, <1c {r['below_1c_pct']:.1f} % | MPC przy tym z'': plat {im[0] if im[0] is None else round(im[0],1)}, +wsp {im[1] if im[1] is None else round(im[1],1)}")
