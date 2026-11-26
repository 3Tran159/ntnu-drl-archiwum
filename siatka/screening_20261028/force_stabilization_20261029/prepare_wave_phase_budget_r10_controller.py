from pathlib import Path
import ast
R=Path(__file__).resolve().parent
src=R/'run_wave_halfdt_probe_r8.py';out=R/'run_wave_phase_budget_probe_r10.py'
if out.exists():raise RuntimeError('Prepared controller already exists; inspect')
s=src.read_text()
s=s.replace('WaveHalfDtProbeR8','WavePhaseBudgetProbeR10').replace('halfdt10inner_r8','phaseBudget_dt1ms_r10').replace('wave_halfdt_probe_r8.lock','wave_phase_budget_probe_r10.lock')
s=s.replace("NTNU_WAVE_DT='.0005'","NTNU_WAVE_DT='.001'").replace("NTNU_WAVE_STEPS='500'","NTNU_WAVE_STEPS='250'").replace("done.get('steps')==500","done.get('steps')==250")
s=s.replace("if running(36724):raise RuntimeError('Prior GPU pilot still active')","if running(33140):raise RuntimeError('Prior zero-step audit still active')")
s=s.replace("cpu.get('purpose')!='Paired foil calm/W01 zero-step CPU1 preparation'","cpu.get('purpose') not in ['Paired foil calm/W01 zero-step CPU1 preparation','Wave free-surface M10 variant CPU2 build; no GPU']")
s=s.replace("if (R/'STOP_ALL').exists():raise RuntimeError('User stop marker')","if (R/'STOP_ALL').exists():raise RuntimeError('User stop marker')\n if e.read(R/'wave_report_definition_review.json',{}).get('status')!='definitions_and_saved_values_verified_next_phase_flux_consistency':raise RuntimeError('Report definition audit prerequisite')")
s=s.replace("change='Matched0.500to0.750s diagnostic;1ms to0.5ms only,10inner andallBCs unchanged, no reinitialization'","change='ReplayR4 matched0.500to0.750s,SO1ms10inner unchanged; addnativephaseconservationreports only; no reinitialization'")
s=s.replace("hardware='OneGPU, sameasR4; timestep only'","hardware='OneGPU, sameasR4; reporting only, no numerical or physics change'")
s=s.replace("GPU halfdt10inner diagnostic r8","GPU nativephasebudget diagnostic r10")
s=s.replace('Investigate four R4 mass-budget spikes in matched0.5to0.75s withhalfdt10inner; long continuation remains gated.','Replay matched R4 settings with native phase conservation diagnostics; no physics changes.')
ast.parse(s);out.write_text(s)
for l in s.splitlines():
 if any(k in l for k in ['case=W','own=','if running','cpu.get','NTNU_WAVE_DT','source_identity','done.get','probe','audit prerequisite']):print(l)
