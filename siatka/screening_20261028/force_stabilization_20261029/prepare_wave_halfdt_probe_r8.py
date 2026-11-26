from pathlib import Path
R=Path(__file__).resolve().parent
a=R/'WaveHalfDtProbeR8.java';b=R/'run_wave_halfdt_probe_r8.py'
if a.exists() or b.exists():raise RuntimeError('Preserve existing R8')
s=(R/'WaveInner20ProbeR6.java').read_text().replace('class WaveInner20ProbeR6','class WaveHalfDtProbeR8').replace('setMaximumNumberInnerIterations(20)','setMaximumNumberInnerIterations(10)').replace('"inner",20','"inner",10').replace('Matched short diagnostic of the0.618s mass-budget spike; only inneriterations10to20 changed; not propagation acceptance','Matched short timestep diagnostic of mass-budget spikes;1ms to0.5ms,10inner unchangedversusR4; notpropagationacceptance')
s=s.replace('if(!Double.isFinite(v)||','if(!Double.isFinite(mn)||!Double.isFinite(mx)||!Double.isFinite(w)||!Double.isFinite(v)||')
a.write_text(s)
c=(R/'run_wave_inner20_probe_r6.py').read_text()
for x,y in [
('W20_H24_X4_GPUprop_environmentalOutlet_inner20probe_r6','W20_H24_X4_GPUprop_environmentalOutlet_halfdt10inner_r8'),
('wave_inner20_probe_r6.lock','wave_halfdt_probe_r8.lock'),('WaveInner20ProbeR6','WaveHalfDtProbeR8'),
("NTNU_WAVE_DT='.001'","NTNU_WAVE_DT='.0005'"),("NTNU_WAVE_STEPS='250'","NTNU_WAVE_STEPS='500'"),("done.get('steps')==250","done.get('steps')==500"),
("if running(15556):","if running(36724):"),
("change='Matched0.500to0.750s diagnostic;10to20inner only,SO1ms andallBCs unchanged, no reinitialization'","change='Matched0.500to0.750s diagnostic;1ms to0.5ms only versusR4,10inner andallBCs unchanged,no reinitialization'"),
("hardware='OneGPU, sameasR4; inneriterations only'","hardware='OneGPU, sameasR4; timestep only'"),
('GPU inner20 diagnostic r6','GPU halfdt10inner diagnostic r8'),
('Investigate four R4 mass-budget spikes in matched0.5to0.75s with20inner; long continuation remains gated.','Investigate R4 mass spikes withhalfdt10inner; R6twentyinner failed.01%gate; longcontinuation staysgated.')
]:c=c.replace(x,y)
b.write_text(c)
print('R8 halfdt probe prepared; R6 failedbudgetgate preserved; longR7notadmitted.')
