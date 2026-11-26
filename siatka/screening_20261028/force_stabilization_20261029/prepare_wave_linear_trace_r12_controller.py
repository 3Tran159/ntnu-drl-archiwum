from pathlib import Path
import ast
R=Path(__file__).resolve().parent;out=R/'run_wave_linear_trace_r12.py'
if out.exists():raise RuntimeError('PreparedR12exists')
s=(R/'run_wave_phase_budget_probe_r10.py').read_text().replace('WavePhaseBudgetProbeR10','WaveLinearTraceR12').replace('phaseBudget_dt1ms_r10','linearTrace_dt1ms_r12').replace('wave_phase_budget_probe_r10.lock','wave_linear_trace_r12.lock').replace('if running(33140)','if running(36136)').replace('Prior zero-step audit still active','Prior40innerprobe stillactive')
s=s.replace("NTNU_WAVE_STEPS='250'","NTNU_WAVE_STEPS='150'").replace("done.get('steps')==250","done.get('steps')==150")
s=s.replace(" if (R/'STOP_ALL').exists():raise RuntimeError('User stop marker')"," if (R/'STOP_ALL').exists():raise RuntimeError('User stop marker')\n proof=e.read(R/'wave_inner40_phase_probe_r11_review.json',{})\n if proof.get('short_mass_gate_pass') or not proof.get('native_inventory_consistent') or not proof.get('source_unchanged'):raise RuntimeError('R11reviewprerequisite')")
s=s.replace("change='ReplayR4 matched0.500to0.750s,SO1ms10inner unchanged; addnativephaseconservationreports only; no reinitialization'","change='ReplayR4t0.500to0.650 SO1ms10inner; addperinnernativephase andVOF/pressureAMGverbosityaround0.605to0.635only; no numericalchange/reinitialization'")
s=s.replace("GPU nativephasebudget diagnostic r10","GPU linear-convergence trace r12")
s=s.replace("scope='Environmental outlet and slip bed no-foil pilot; not force or final propagation validation'","scope='No-foil nativephase andAMGconvergence trace; reporting only, no numericalchange, no forceadmission'")
ast.parse(s);out.write_text(s);print('R12controllerpreparedonly')
