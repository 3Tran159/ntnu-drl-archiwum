from pathlib import Path
import json,ast
R=Path(__file__).resolve().parent
src=R/'WaveLinearTraceR12.java';p=R/'WaveVofToleranceR13.java'
assert not p.exists()
s=src.read_text()
s=s.replace('WaveLinearTraceR12','WaveVofToleranceR13').replace('R12','R13').replace('steps!=150','steps!=250').replace('and150steps','and250steps').replace('"target_time_s",.65','"target_time_s",.75')
s=s.replace('Reporter-only nativephase andAMG per-inner trace0.500to0.650s; sameSO1ms10inner asR4, no initialization/numericalchanges; notpropagationacceptance','Single-control VOF AMG tolerance0.1to0.001 sensitivity0.500to0.750s; SO1ms10inner unchanged; no reinitialization; notpropagationacceptance')
s=s.replace('Reporter-only native phase budget diagnostic; original 0.01% inventory budget gate retained; no force or final propagation acceptance','Single-control VOF AMG tolerance sensitivity; original 0.01% inventory budget gate retained; no force or final propagation acceptance')
needle='   Files.writeString(out.resolve("linear_trace_setup.json")'
assert s.count(needle)==1
s=s.replace(needle,'   vofAmg.setConvergeTol(.001);\n   if(Math.abs(vofAmg.getConvergeTol()-.001)>1e-12||Math.abs(pressureAmg.getConvergeTol()-.1)>1e-12)throw new IllegalStateException("Single-control tolerance change failed");\n'+needle)
s=s.replace('Only reporting/verbositychanges; nativephase monitors everyinner, VOF/pressureAMGLOW onlyaroundspikes','Only numericalchange VOFrelativeAMGtolerance0.1to0.001; pressuretol0.1, allothercontrols unchanged; everyinnernative and LOWtrace retained')
p.write_text(s)
src=R/'run_wave_linear_trace_r12.py';p=R/'run_wave_vof_tolerance_r13.py'
assert not p.exists()
s=src.read_text().replace('linearTrace_dt1ms_r12','vofTol001_dt1ms_r13').replace('wave_linear_trace_r12.lock','wave_vof_tolerance_r13.lock').replace('WaveLinearTraceR12','WaveVofToleranceR13')
s=s.replace('if running(36136):raise RuntimeError(\'Prior40innerprobe stillactive\')','if running(39344):raise RuntimeError(\'PriorR12trace stillactive\')')
s=s.replace("proof=e.read(R/'wave_inner40_phase_probe_r11_review.json',{})\n if proof.get('short_mass_gate_pass') or not proof.get('native_inventory_consistent') or not proof.get('source_unchanged'):raise RuntimeError('R11reviewprerequisite')","proof=e.read(R/'wave_linear_trace_r12_review.json',{})\n if proof.get('short_mass_gate_pass') or not proof.get('native_inner_endpoints_match_physical_history') or not proof.get('source_unchanged'):raise RuntimeError('R12reviewprerequisite')\n if proof['AMG']['VOF']['cycles_max']!=1 or proof['AMG']['VOF']['ratio_min']<=.001 or proof['AMG']['VOF']['ratio_max']>=.01:raise RuntimeError('Observed stopping evidence prerequisite')")
s=s.replace('No-foil nativephase andAMGconvergence trace; reporting only, no numericalchange, no forceadmission','No-foil VOF AMG tolerance0.1to0.001 sensitivity; SO1ms10inner and allothercontrols unchanged; no forceadmission')
s=s.replace('GPU linear-convergence trace r12','GPU VOF AMG tolerance sensitivity r13')
s=s.replace('ReplayR4t0.500to0.650 SO1ms10inner; addperinnernativephase andVOF/pressureAMGverbosityaround0.605to0.635only; no numericalchange/reinitialization','R4t0.500to0.750 SO1ms10inner; ONLY VOF AMGrelative tolerance0.1to0.001, pressuretol0.1 and allothernumerics unchanged; nativephase/LOWAMGtrace retained; no reinitialization')
s=s.replace('OneGPU, sameasR4; reporting only, no numerical or physics change','OneGPU, sameasR4; only VOF AMGrelative tolerance changes')
s=s.replace("NTNU_WAVE_STEPS='150'","NTNU_WAVE_STEPS='250'").replace("done.get('steps')==150","done.get('steps')==250")
s=s.replace('Check outlet spatial fields, full-cycle gauges, mean level and conservation; reflection and timestep checks still pending','Compare matched .502-.750 native and legacy mass budget versus R10; actual VOF cycles/target, inner traces, gauges and cost. No longer propagation until scientific review.')
s=s.replace('"""Replay R4 with identical settings and independent native phase conservation reports; no physics change."""','"""Single numerical-control probe: VOF AMG relative tolerance .1 to .001."""')
ast.parse(s);p.write_text(s)
print(json.dumps({'created':[str(R/'WaveVofToleranceR13.java'),str(p)],'one_numerical_change':'VOF AMG tolerance .1 -> .001','steps':250,'start':.5,'target':.75}))
