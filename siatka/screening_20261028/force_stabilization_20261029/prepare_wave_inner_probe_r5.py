from pathlib import Path
R=Path(__file__).resolve().parent
a=R/'WaveInner20ProbeR5.java';b=R/'run_wave_inner20_probe_r5.py'
if a.exists() or b.exists():raise RuntimeError('Preserve existing probe')
s=(R/'WavePropagationContinuationR5.java').read_text().replace('class WavePropagationContinuationR5','class WaveInner20ProbeR5').replace('getPhysicalTime()-1.2','getPhysicalTime()-.5').replace('"target_time_s",4.0','"target_time_s",.75').replace('setMaximumNumberInnerIterations(10)','setMaximumNumberInnerIterations(20)').replace('"inner",10','"inner",20').replace('Longer propagation continuation; no foil forces and no final reflection claim','Matched short diagnostic of the0.618s mass-budget spike; only inneriterations10to20 changed; not propagation acceptance')
a.write_text(s)
c=(R/'run_wave_continuation_r5.py').read_text()
for old,new in [
('W20_H24_X4_GPUprop_environmentalOutlet_long_dt1ms_r5','W20_H24_X4_GPUprop_environmentalOutlet_inner20probe_r5'),
('wave_continuation_r5.lock','wave_inner20_probe_r5.lock'),
('WavePropagationContinuationR5','WaveInner20ProbeR5'),
("NTNU_WAVE_STEPS='2800'","NTNU_WAVE_STEPS='250'"),
("done.get('steps')==2800","done.get('steps')==250"),
("source=W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'/'final.sim'","source=W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'/'checkpoint_t0.500.sim'"),
("if sp['max_speed']['speed_m_s']>25 or review['BDF2_budget_after_0p2_max_abs_pct_inlet']>.01:raise RuntimeError('R4 spatial/conservation diagnostic requires investigation')","if sp['max_speed']['speed_m_s']>25:raise RuntimeError('R4 spatial diagnostic requires investigation')\n # This short probe investigates the failed0.01%mass gate; it does not authorize longer propagation."),
("restart_from='reviewed r4 t1.2 checkpoint'","restart_from='r4 t0.500 checkpoint, matched to10innerhistory'"),
("change='No numerical/boundary change; continue reviewed stable R4 t1.2 to4.0s without reinitialization'","change='Matched0.500to0.750s diagnostic;10to20inner only,SO1ms andallBCs unchanged, no reinitialization'"),
("hardware='One GPU, same as prior r3; boundary termination is the controlled change'","hardware='OneGPU, sameasR4; inneriterations only'"),
('Continue only the reviewed stable R4 checkpoint to4s; no source modification or reinitialization.','Investigate four R4 mass-budget spikes in matched0.5to0.75s with20inner; long continuation remains gated.'),
('no-foil GPU continuation r5','no-foil GPU inner20 diagnostic r5'),
]:c=c.replace(old,new)
b.write_text(c)
print('Prepared controlled250step20inner diagnostic; longer continuation gate unchanged.')
