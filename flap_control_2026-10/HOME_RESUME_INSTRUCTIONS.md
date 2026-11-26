# Mini CFD — saved relocation checkpoint, 9 November 2026

State: PAUSED BY USER. No owned STAR/MPI process remains. Queue disabled. Explicit resume required.

Checkpoint: `H:\NTNU_RESEARCH_ARCHIVE\Active_Flaps\CHECKPOINTS\PAUSE_20261109_112944\Flap_CFD_HOME_RESUME_20261109_t1p759.sim`
SHA-256: `783eefa6602608382889bd8c0faa756eaf3c2290577c33cd3f6c0643eec28369`.
Physical time 1.759 s; 3518 steps; iteration 42216; fixed sealed flap 0 degrees; U=14 m/s.
STAR 2606.0002 / 21.04.009; 25,617 cells; span 20 mm; VOF water/air, SST All y+.
dt=0.0005 s; 12 inner iterations; 2 MPI ranks on logical CPUs 22/23, High priority, no GPU.

## Resume after explicit user instruction

Run `H:\NTNU_RESEARCH_ARCHIVE\Active_Flaps\CHECKPOINTS\PAUSE_20261109_112944\RESUME_MINI_CFD.cmd`. A convenience copy is at `F:\ntnu\flap_control\RESUME_MINI_CFD.cmd`.
The launcher verifies the frozen checkpoint and history hashes, then continues from 1.759 s.
It does not reset fields or time, and does not regenerate the mesh. It performs the remaining 482 steps to the original 2.000 s cap, or stops earlier if the unchanged native gates demand it.
The 718-sample rolling-force seed preserves alignment of the 0.2 s convergence windows. The stable-window counter is 0.
After this segment, pending speed cases remain paused for review; the expired overnight window is not silently restarted.
For file-only preflight: run `"C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "H:\NTNU_RESEARCH_ARCHIVE\Active_Flaps\CHECKPOINTS\PAUSE_20261109_112944\resume_paused_calm.py" --check`.

## Preserved files and dependencies

This directory contains a complete copied .sim, both .simh files, force/gauge/residual CSV histories, mesh diagnostics, Java macro, logs, configuration and SHA256_MANIFEST.json.
Original run: `H:\NTNU_RESEARCH_ARCHIVE\Active_Flaps\URANS_XFOIL_CALIBRATION_20261107\runs\XFOIL_CAL_CALM_U14_INITFIX_R2_20261109_093959`. Keep it: saved STAR replay references may still point to these original history paths.
Active history copy: `H:\NTNU_RESEARCH_ARCHIVE\Active_Flaps\CHECKPOINTS\PAUSE_20261109_112944\XFOIL_CAL_CALM_U14_INITFIX_R2_20261109_093959_AF_resume.simh`.
Controller dependency: `H:\NTNU_RESEARCH_ARCHIVE\Active_Flaps\URANS_XFOIL_CALIBRATION_20261107\CALM_SPEED_NIGHT_20261108\night_speed_queue.py` and its existing F-drive run_day/resume modules. Existing authorized STAR licensing mechanism is unchanged; no key is stored here by this launcher.
The launcher was file-checked and compiled. It has NOT been executed after pause.

## Scientific status and pending work

U14 is partial, not force-stabilized or accepted for training. Final residual window passed before user pause.
Last complete 0.2 s-window comparison at t=1.6 s: CL drift 0.630%, CD drift 2.219%; required <0.5% for both with four confirmations.
U18 completed its 2 s diagnostic cap but remains force-unstabilized. Wave ±2°/90° previously passed its wave/motion/repeatability checks.
U10, U12 and U16 are paused. Old FAIL/HOLD attempts remain archived.
No automatic launch on Windows startup has been configured.

## Shutdown warning

Independent W04k was still active when Mini was paused, with native solver PID 30200. Its case is `E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs\W04k_20261109_093752_f821d8\native_solve\input.sim`.
It was not stopped or modified. Shutting down Windows will interrupt it; global SAFE TO SHUT DOWN is not declared.
Checkpoint integrity: native save reported complete and clean STAR exit; copied file SHA-256 matches. It was not reopened in a new STAR session during shutdown preparation.
