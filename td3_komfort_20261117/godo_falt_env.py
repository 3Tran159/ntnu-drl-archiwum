"""godo_falt_env.py - 17.11 (prosba Julka 17:12): srodowisko TD3 na modelu Faltinsena B z TYM SAMYM kosztem co MPC komfortowe.
Cel: uczciwe porownanie TD3 vs MPC przy tym samym kryterium komfortu (NORDFORSK 0,05 g), wszystko "w modelu".
Interfejs jak GodoVortexEnv (train_rl.py dziala bez zmian poza importem).

Plant: FaltinsenPlant wariant B (slope 1, wave_u), obciazenie 90 %, fala regularna Godo (amplituda 0,727 m, T 5 s, od dziobu),
  serwo 2. rzedu 40 rad/s, +-7,5 deg, 90 deg/s; takt sterowania 10 ms; nurzanie zwolnione po 1 okresie spotkania (jak harness MPC).
Obserwacje (5): z, v, wzniesienie fali nad LE, pionowa predkosc wody na placie (fala, jak K0), poprzednia komenda.
  (MPC dostaje wiecej: przyszla fale z dopasowanej sinusoidy. TD3 musi wywnioskowac faze z eta i w - jak u Godo.)
Nagroda = struktura Godo (przezycie + kary z, zanurzenia, predkosci kata) + WE * r_e, gdzie
  r_e = (J_ref - J) / J_ref,  J = opor plata + opor wspornika + W_A * zdd^2 + ACT_K * (dtheta/dt)^2 / U   [N na pasek 0,02 m]
  - te same pozycje co rachunek MPC (mpc_komfort.py); J_ref = woda spokojna (plat 57,03 W / U + wspornik na 1,09 m).
  Kara Godo za predkosc kata (W_RATE) zastapiona kosztem silownika ACT_K jak w MPC.
Zmienne srodowiskowe: TD3K_W_A (domyslnie 1,5), TD3K_ACT_K (57)."""
import os, sys
from pathlib import Path
import numpy as np
import gymnasium as gym
from gymnasium import spaces
ROOT = Path(r"T:\NTNU_GODO_CONTROL_20261109"); sys.path.insert(0, str(ROOT / "60_PANELE_I_WYNIKI" / "ZAWIESZENIE"))
import zaw90 as Z
FP, U, G, BUOY, C = Z.FP, Z.U, Z.G, Z.BUOY, Z.C
DEPTH, SPAN, LOAD = 1.09, 0.02, 0.9
FP.MASS = LOAD * Z.MASS100; MASS = FP.MASS
AMP, T_REL = 0.727, 1.9368
W_A = float(os.environ.get("TD3K_W_A", "1.5")); ACT_K = float(os.environ.get("TD3K_ACT_K", "57"))
STRUT_K = 85.5 * SPAN
W_S = 2e4                                   # jak W_S w mpc_komfort.py
P_CALM_FOIL_W = 57.03
TH_MAX_DEG = 7.5
_p0 = Z.FaltinsenPlant(wave_amp=AMP, **Z.VB)
TH_REF_DEG = FP.TH_REF_DEG + float(np.degrees(((MASS * G - BUOY) / _p0.q - FP.CL_REF) / (_p0.slope * _p0.dcl)))
Z1, Z2 = 0.55, 0.75; S1, S2 = 2.0 * C, 1.0 * C; R1, R2 = 45.0, 80.0; WE, SG = 1.3, 0.5
OBS_SCALE = np.array([0.75, 1.0, 0.75, 1.0, 1.0])


def f_pen(x, x1, x2):
    if x < x1: return 0.0
    if x > x2: return -1.0
    return 0.5 * (np.cos(np.pi * (x - x1) / (x2 - x1)) - 1.0)


class GodoVortexEnv(gym.Env):
    """nazwa zostawiona dla train_rl.py; w srodku Faltinsen B"""
    metadata = {"render_modes": []}

    def __init__(self, n_periods=8, random_phase=True, seed=None, **kw):
        super().__init__()
        self.plant = Z.FaltinsenPlant(wave_amp=AMP, **Z.VB)
        self.n_ticks = int(round(n_periods * self.plant.Te / (self.plant.tick * self.plant.dt)))
        self.random_phase = random_phase
        self.D_cw = P_CALM_FOIL_W / U
        self.J_ref = self.D_cw + STRUT_K * DEPTH
        self.observation_space = spaces.Box(-5.0, 5.0, (5,), np.float32); self.action_space = spaces.Box(-1.0, 1.0, (1,), np.float32)
        self._rng = np.random.default_rng(seed)

    def _wfoil(self):
        p = self.plant; return float(np.mean(p.gust(p.F.xc, p.t)[1]))

    def _obs(self):
        p = self.plant
        o = np.array([p.z, p.v, p.eta_LE(), self._wfoil(), 0.0]) / OBS_SCALE; o[4] = self.prev_a
        return np.clip(o, -5, 5).astype(np.float32)

    def reset(self, seed=None, options=None):
        if seed is not None: self._rng = np.random.default_rng(seed)
        p = self.plant
        p.beta = float(self._rng.uniform(0, 2 * np.pi)) if self.random_phase else 0.4
        if options and "phase" in options: p.beta = float(options["phase"])
        p.reset(theta_deg=TH_REF_DEG); p.cmd = np.radians(TH_REF_DEG)
        while p.t < T_REL - 0.5e-3: p.step(free_heave=False)
        self.prev_a = TH_REF_DEG / TH_MAX_DEG; self.k = 0
        return self._obs(), {}

    def step(self, action):
        p = self.plant; a = float(np.clip(np.asarray(action).reshape(-1)[0], -1, 1))
        p.cmd = np.radians(a * TH_MAX_DEG); Ls = Fx = 0.0; rate_max = 0.0; rate2 = 0.0
        for _ in range(p.tick):
            r = p.step(free_heave=True); Ls += r["L"]; Fx += r["Fx"]; rate_max = max(rate_max, abs(r["rate_deg_s"])); rate2 += np.radians(r["rate_deg_s"]) ** 2
        D = Fx / p.tick * SPAN; acc = (Ls / p.tick + BUOY) / MASS - G; rate2 /= p.tick
        self.k += 1; z = p.z; sub = r["sub_true"]
        bad = (not np.isfinite(z)) or abs(z) > Z2 or sub < S2
        D_strut = STRUT_K * max(sub, 0.0)
        # v2 (17.11 21:25): + miekkie ograniczenia jak w MPC (W_S 2e4: zanurzenie >= 2 cieciwy, |z| <= 0,5 m) - w v1 TD3 W_A 1,5 nauczyl sie
        # podchodzic pod powierzchnie, gdzie Faltinsen B daje niefizyczny ciag, i konczyc epizod (oplacalo sie, bo nagroda za krok byla ujemna);
        # + kara za zakonczenie = pozostale kroki (smierc nigdy sie nie oplaca)
        J = D + D_strut + W_A * acc * acc + ACT_K * rate2 / U + W_S * (max(0.0, 2 * C - sub) ** 2 + max(0.0, abs(z) - 0.5) ** 2)
        r_e = (self.J_ref - J) / self.J_ref
        rew = SG * ((0.0 if bad else 1.0) + f_pen(abs(z), Z1, Z2) + f_pen(-sub, -S1, -S2) + f_pen(rate_max, R1, R2) + WE * r_e)
        if bad: rew -= float(self.n_ticks - self.k)
        self.prev_a = a
        info = dict(D=D, r_e=r_e, z=z, theta_deg=r["theta_deg"], rate=r["rate_deg_s"], acc=acc, eta=r["eta_LE"], sub=sub, D_strut=D_strut, J=J, P_drag_W=U * D)
        return self._obs(), float(rew if np.isfinite(rew) else -10.0), bool(bad), bool(self.k >= self.n_ticks and not bad), info


def harness(act, phase=0.4, nper=15):
    """ten sam protokol co `mpc_falt_bridge.py - W_A KI test`: 15 okresow, ostatnie 4; dP_pct plata vs 57,03 W, z'' RMS (std)"""
    env = GodoVortexEnv(n_periods=nper, random_phase=False); o, _ = env.reset(options={"phase": phase}); rows = []; done = False
    while not done:
        o, r, term, trunc, info = env.step(act(o)); done = term or trunc
        rows.append((env.plant.t, info["P_drag_W"], info["acc"], info["z"], info["theta_deg"], info["sub"]))
    a = np.array(rows); b = a[a[:, 0] > a[-1, 0] - 4 * env.plant.Te]
    return dict(term=bool(term), dP_pct=round(100 * (b[:, 1].mean() / P_CALM_FOIL_W - 1), 2), acc_rms=round(float(b[:, 2].std()), 3),
                z=[round(float(b[:, 3].min()), 3), round(float(b[:, 3].max()), 3)], th=[round(float(b[:, 4].min()), 2), round(float(b[:, 4].max()), 2)],
                sub_min=round(float(b[:, 5].min()), 3))


if __name__ == "__main__":
    import time, psutil
    psutil.Process().cpu_affinity([23]); psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    print("trym", round(TH_REF_DEG, 3), "deg, W_A", W_A, "J_ref", round(GodoVortexEnv().J_ref, 3), "N")
    kp, ki = 2.01, 0.196; st = {"i": 0.0}

    def pid(o):
        z = o[0] * OBS_SCALE[0]; st["i"] = float(np.clip(st["i"] - z * 0.01, -1, 1))
        return np.array([np.clip((TH_REF_DEG + kp * (-z) + ki * st["i"]) / TH_MAX_DEG, -1, 1)])
    t0 = time.time(); h = harness(pid, nper=6); print("PID1:", h, round(time.time() - t0, 1), "s na 6 okresow")
