from pathlib import Path
import ast
R=Path(__file__).resolve().parent
cp=R/'run_wave_inner40_phase_probe_r11.py';mp=R/'WaveInner40PhaseProbeR11.java'
if cp.exists() or mp.exists():raise RuntimeError('Preparedattempt exists')
s=(R/'run_wave_phase_budget_probe_r10.py').read_text().replace('WavePhaseBudgetProbeR10','WaveInner40PhaseProbeR11').replace('phaseBudget_dt1ms_r10','inner40phaseBudget_dt1ms_r11').replace('wave_phase_budget_probe_r10.lock','wave_inner40_phase_probe_r11.lock').replace('if running(33140)','if running(35120)').replace('Prior zero-step audit still active','Prior reporter probe still active')
s=s.replace("'Wave free-surface M10 long-domain CPU1 extension; no GPU']","'Wave free-surface M10 long-domain CPU1 extension; no GPU','Paired M10 foil calm/W01 zero-step CPU1 preparation']")
s=s.replace(" if (R/'STOP_ALL').exists():raise RuntimeError('User stop marker')"," if (R/'STOP_ALL').exists():raise RuntimeError('User stop marker')\n proof=e.read(R/'wave_phase_budget_probe_r10_review.json',{})\n if not proof.get('reporting_equivalence_supported') or proof.get('legacy_faceflux_mass_gate_pass') or not proof.get('source_unchanged'):raise RuntimeError('R10mustconfirmreportingandfailedmassgatebefore40innerprobe')")
s=s.replace("change='ReplayR4 matched0.500to0.750s,SO1ms10inner unchanged; addnativephaseconservationreports only; no reinitialization'","change='MatchedR4t0.500to0.750,onlyinner10to40;SO1msandBCunchanged;nativephasereportsretained;no reinitialization'")
s=s.replace("hardware='OneGPU, sameasR4; reporting only, no numerical or physics change'","hardware='OneGPU, sameasR4; onlyinneriterationcountchanged'")
s=s.replace("GPU nativephasebudget diagnostic r10","GPU nativephasebudget inner40 diagnostic r11")
s=s.replace('Replay R4 with identical settings and independent native phase conservation reports; no physics change.','Controlled10to40inner diagnostic with independent native phase conservation reports; SO1ms unchanged.')
m=(R/'WavePhaseBudgetProbeR10.java').read_text().replace('WavePhaseBudgetProbeR10','WaveInner40PhaseProbeR11').replace('R10','R11')
m=m.replace('setMaximumNumberInnerIterations(10)','setMaximumNumberInnerIterations(40)').replace('"inner",10','"inner",40')
m=m.replace('Reporter-only matched diagnostic of phase transport mass errors; same SO 1 ms and 10 inner iterations as R4, no initialization or physics changes; not propagation acceptance','Matched phase transport diagnostic; only 10 to 40 inner iterations relative to R4, SO1ms unchanged; no initialization or boundary changes; not propagation acceptance')
m=m.replace('Reporter-only native phase budget diagnostic; original 0.01% inventory budget gate retained; no force or final propagation acceptance','40-inner phase budget diagnostic; original0.01%gate retained; no force or final propagation acceptance')
ast.parse(s);cp.write_text(s);mp.write_text(m)
print('R11 prepared only, explicitlygated onR10review andfreeGPUlock')
