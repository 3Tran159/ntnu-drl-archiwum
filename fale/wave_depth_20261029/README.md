# NTNU HFF1 | No-foil regular wave tank | 2026-10-29

## Purpose and isolation

This is a 3-D thin-slab numerical wave tank to verify **incident regular waves** before any submerged foil is added. It intentionally excludes the foil by placing the computational slab at y=20.0..20.8 m; the foil CAD is at y approximately -5.5..+5.5 m. The original geometry and historical CFD runs are not overwritten.

Original clean source (2.86 MB): `F:\ntnu\mesh_screening_20261028\inspection\baseline_clean.sim`. Each run has its own copied `baseline_copy.sim`. The input macro is `WaveTankBuild.java`; the matrix is `cases.csv` and `cases.json`.

**Status:** Config files and baseline copies are real. Do not assume `built.sim` exists until `SUCCESS.txt` and `mesh_count.txt` are present, STAR log is checked, and source SIM is reopenable. A macro returncode of zero by itself is insufficient.

## Physical setup

- Waterline: z=+2 m. Bottom: z=2-h, slip wall. Top: z=+12 m, pressure outlet.
- Thin 3D slab: y=20..20.8 m; two transverse faces remain symmetry boundaries.
- Domain length: `Nlambda * lambda`. At Nlambda=3: x=(-1.25 lambda, +1.75 lambda), at Nlambda=4: x=(-1.75 lambda,+2.25 lambda).
- Forcing on inlet, damping on outlet; lengths 1 lambda each. Boundary-selective configuration requires validation in STAR.
- First-order finite-depth gravity wave, lambda specified, amplitude a=0.25 m (H=0.5 m), advancing +x, current +18 m/s; wave field initialization and inlet use this specific wave.
- HF_wave current sizing: approx dx=0.2048 m, dy=0.4096 m, dz=0.0256 m in z=1.25..2.75 m, x covering full tank. Additional HF_fine refinement is disabled. Surface remeshing defaults retained.
- Initial continuum is reused from NTNU baseline, with VOF water/air, gravity, and turbulence settings. First-order wave theory is suitable for the modest H/lambda (0.0167..0.025).

## Time step

Finite-depth dispersion: c=sqrt(g/k * tanh(k h)), k=2pi/lambda, intrinsic T=lambda/c. With +18 m/s following the imposed x direction, fixed-foil encounter T_e=lambda/(18+c).

- For 20 m: T_e ~0.848 s, dt=0.002 s gives ~424 steps per encountered wave and U*dt/dx ~0.176.
- For 30 m: T_e ~1.208 s, dt=0.002 s gives ~604 steps per encountered wave.
- Vertical interface CFL estimate at W20: a*(2pi/T)*dt/dz ~0.034; confirm actual maximum CFL in STAR.
- dt sensitivity at identical W20 h16 X3: 0.001, 0.002, 0.004 s.
- The original NTNU foil stability run used dt=1e-5 s because it was a startup stress test; that tiny dt is not a proven wave-accuracy requirement.
- Consider second-order time discretization once the setup passes startup smoke tests. Check solver stabilization.

## Model-verification acceptance

First verify geometry and boundary mapping: no actual foil boundary should intersect the slim computational slab; measure boundary area and wave field to confirm. Confirm no zero-volume or invalid cells, correct h and no surprise porous/solid boundary.

Wave-only monitors to add/verify before long solves:
- At x=0 and x=0.5 lambda, integrate solved water volume fraction alpha over the vertical fluid slice and divide by slab width. Subtract h to obtain eta(t).
- For comparison, use analytical eta(t), c(h), phase, amplitude, u(x,z,t) and w(x,z,t) at z=0 (about 2m beneath mean free surface).
- Report numerical reflection via a two- or three-probe decomposition or compare upstream/downstream wave phases.
- Compare h=12/16/24 for fixed lambda and fixed boundary forcing; the physical finite-depth wave period changes slightly with h for a fixed lambda.
- Compare L=3lambda and L=4lambda at h=16 to reveal whether reflection and forcing-zone placement contaminate the x=0 signal.
- Compare dt=1/2/4ms at the reference case after spatial resolution is held fixed.
- A **screening** target is <2% change in measured H and <2deg phase at x=0 between spatial/time-step-adequate runs, subject to checks on reflection and solver residuals. Not a universal validation tolerance.
- At least several (preferably 8-10) encounter periods after transient spin-up for a credible amplitude/phase comparison.

## How to run a single case manually

From Windows PowerShell, with STAR-CCM+ installed:

```powershell
python "F:\ntnu\wave_depth_20261029\wave_runner.py" "F:\ntnu\wave_depth_20261029\W20_H16_X3\job.json"
```

Run **one STAR process at a time**, and only with ample RAM and CPU headroom. Read each case's `build.log` and check for `[NTNU_WAVE] BUILT`, `SUCCESS.txt` and `mesh_count.txt`. An existing log is never overwritten. For retries, clone the case to a new directory.

After a saved `built.sim` is inspected, run a very short CFD smoke test and only then proceed to the longer incident-wave validation. Do **not** launch all cases when the existing NTNU meshing/visualization runs are active.

## Literature

- Simcenter STAR-CCM+ VOF Waves Guidelines: dx~lambda/80..100, dz~H/20, dt near T/(2.4*n) before corrections for current-driven encounter frequencies and interface CFL.
- ITTC 7.5-03-02-03, numerical CFD procedures: ~100 steps per regular-wave period as a minimum temporal guideline.
- ITTC 7.5-02-07-02.8: wave generation requires numerical spatial and temporal verification; recommend >=10 encountered wave periods in production added-resistance simulations.
