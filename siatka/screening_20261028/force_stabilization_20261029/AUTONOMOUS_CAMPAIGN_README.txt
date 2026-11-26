AUTONOMOUS NTNU WAVE CAMPAIGN
================================
Location: F:/ntnu/mesh_screening_20261028/force_stabilization_20261029
New case storage: E:/ntnu/quasi2d_waves_20261029

CURRENT STATE
The original 1 ms campaign is UNARMED. Existing W01 ended on its physical
stability guard at 1.064 s. The controller rejects its adoption and blocks
the complete automatic sequence. A separate half-step diagnostic does not
approve or resume this plan. Existing H050 zero-step registry periods were
also zero when checked: a positive audited actual encounter period is
required before a fresh wave launch. No period is estimated from a formula.

SAFE COMMANDS (CMD)
"C:\Python315\python.exe" "F:\ntnu\mesh_screening_20261028\force_stabilization_20261029\autonomous_wave_campaign.py"
"C:\Python315\python.exe" "F:\ntnu\mesh_screening_20261028\force_stabilization_20261029\test_autonomous_wave_campaign.py"
"C:\Python315\python.exe" "F:\ntnu\mesh_screening_20261028\force_stabilization_20261029\build_autonomous_campaign_report.py"

The first command defaults to --dry-run. It reads inputs, hashes and process
ownership, prints readiness, and does not create locks, attempts, or solver
processes. Tests use only temporary mock cases; they never launch STAR.

EXPLICIT EXECUTION — ONLY AFTER CONFIGURATION REVIEW
The flag --run enables sequential execution; --run --once executes at most
one ready case or one waiting check. Neither bypasses readiness or guard
failures. Do not use --run now: the current configuration is unarmed.
No service is installed and this script does not self-start.

FILES / CONTRACT
campaign_plan.json:
  version 1, campaign_id, exact settings, cases, final_accuracy_admitted=false.
  Cases: id, domain_id, height_m, source_label, prerequisites, stage;
  optional notes and explicit adopt_existing contract.
  Stage order is original / original_check before extension.
campaign_inputs/{domain_id}.json:
  paired_inputs_audited_zero_steps, source_unchanged=true, flow_steps=0,
  audited domain, exact cells, CALM/H025/H050/H075 input entries.
  Every input requires its own .sim path, SHA256, zero-step audit, height,
  cells and actual wave_period_s (positive for waves).
  H025/H075 cannot silently reuse or mutate H050.
campaign_macro_build_receipt.json:
  javac_passed plus exact CampaignFoilWave.java SHA256.

The controller preserves source files, copies a verified source into a new
campaign_id__case_id__a001 directory, retains macro/plan/registry/source
identity, redacts logs via run_until_settled.redact, and uses one solver
worker and one GPU. It never touches the separate HF session.

CONCURRENCY AND RESOURCES
autonomous_wave_campaign.lock protects the controller.
queue.lock protects each GPU run. Existing/stale locks are never stolen or
deleted. Held external STAR sessions and existing GPU compute PIDs block
new work. No existing solver is adopted, killed, or attached by this driver.
Start reserves: 24 GiB free RAM and 30 GiB free storage.
Run reserves: 8 GiB each; 4 GiB critical threshold requests termination
only of the exact process launched by this controller.
A stop gets up to 600 seconds to save. An unresolved live owned process
retains locks for inspection. A dead/stale lock still needs manual review.

STOP / RESUME
Create STOP_CAMPAIGN or STOP_ALL in the controller directory, or STOP in
the active attempt directory. Existing macro checks honour STOP.
The controller also stops for nonfinite independent reports, physical
guards, no physical-time progress, resources, or the 36 h wall limit.
Physical guards in the compiled macro remain unchanged.

Re-running the controller consumes verified completed results and resumes
the sequence. It NEVER restarts an existing attempt. A crashed, guarded or
user-stopped incomplete attempt is preserved and blocks further cases.
CampaignFoilWave.java currently accepts zero-time inputs only: checkpoint
continuation needs a separately audited resume macro and explicit
reconciliation. This controller never relabels a failed checkpoint safe.

Existing W01 can be recorded only after a clean saved completion,
controller source_unchanged=true, matching cell identity, saved final.sim,
and a matching authoritative four-cycle pass reproduced from saved history.
A physical-guard failure, macro error or unrepeatable 20T cap is never a
successful adoption. An active session is not a completed result; a held
server still blocks the next solver even after a result is recorded.

STOPPING / RESULTS
Waves target 20 ACTUAL encounter periods using the audited period. They
request a stop on the first passing four consecutive complete cycles.
Ten periods is indicative, never a minimum. Incomplete initial cycles are
excluded by wave_cycle_repeatability.py. No phase realignment is applied.
Calm cases stop on the first pass of both adjacent, non-overlapping 0.2 s
mean changes below 0.5%, once two full windows exist; 6 s is only a cap.
The 0.01% native mass flag is reported, not hidden or used as an accuracy
claim under the explicitly authorised exploratory exception.

campaign_state.json records current progress or the blocking condition.
campaign_results.json stores case outcomes, timestamps, complete-cycle
means, independent diagnostic audit, paths and hashes.
Each attempt retains controller_result.json, logs, history, native phase
reports, final.sim when saved, and every other saved state/checkpoint.
The first unresolved original case blocks later originals and extensions.

REPORT
F:/ntnu/mesh_screening_20261028/campaign_results.html
All configured cases remain visible, including pending inputs and rejected
trials. Mean coefficients are shown only for supported complete windows.
The report is local HTML; nothing is published or sent.
Repeatability is not mesh/time accuracy, conservation, wave quality, or
reflection validation. All pending accuracy checks stay visible.

TEST EVIDENCE
test_autonomous_wave_campaign_results.json is produced by the mock suite.
It covers read-only audit, lock ownership/conflicting PIDs, hash changes,
missing/incorrect-height inputs, zero periods, resources, STOP, consumed
attempts, matched calm prerequisites, early stopping, source preservation,
failed-trial blocking, safe controller resume and HTML escaping.
