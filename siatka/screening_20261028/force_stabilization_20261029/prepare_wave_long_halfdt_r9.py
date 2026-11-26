from pathlib import Path
R=Path(__file__).resolve().parent
a=R/'WaveLongHalfDtR9.java';b=R/'run_wave_long_halfdt_r9.py'
if a.exists() or b.exists():raise RuntimeError('Preserve R9')
s=(R/'WaveLongInner20R7.java').read_text().replace('class WaveLongInner20R7','class WaveLongHalfDtR9').replace('steps>3000','steps>6000').replace('setMaximumNumberInnerIterations(20)','setMaximumNumberInnerIterations(10)').replace('"inner",20','"inner",10').replace('Longer20inner propagation aftermatchedinnerdiagnostic','Longerhalfdt10inner propagation aftermatchedtimesteptest')
# Continue0.5ms withquartersecond, notone-eighth-second, checkpoint spacing.
s=s.replace('step%250==0','step%500==0')
a.write_text(s)
s=(R/'run_wave_long_inner20_r7.py').read_text()
for x,y in [
('W20_H24_X4_GPUprop_environmentalOutlet_long_inner20_r7','W20_H24_X4_GPUprop_environmentalOutlet_long_halfdt_r9'),
('wave_long_inner20_r7.lock','wave_long_halfdt_r9.lock'),('WaveLongInner20R7','WaveLongHalfDtR9'),
("NTNU_WAVE_DT='.001'","NTNU_WAVE_DT='.0005'"),("NTNU_WAVE_STEPS='2800'","NTNU_WAVE_STEPS='5600'"),("done.get('steps')==2800","done.get('steps')==5600"),
("if running(36724):","if running(29860):"),
("cpu.get('purpose')!='Paired foil calm/W01 zero-step CPU1 preparation'","cpu.get('purpose') not in ['Paired foil calm/W01 zero-step CPU1 preparation','Wave free-surface M10 variant CPU2 build; no GPU']"),
('wave_inner20_probe_r6_review.json','wave_halfdt_probe_r8_review.json'),
('max_gauge_difference_20minus10_mm','max_gauge_difference_halfdtminus1ms_mm'),('max_speed_20inner_m_s','max_speed_halfdt_m_s'),
('Matched20inner','Matchedhalfdt10inner'),('matched20inner','matchedhalfdt10inner'),
('20inner supportedbyr6probe','halfdt10inner supportedbyr8probe'),
('Continue1.200to4.000s withsupported20inner,SO1ms','Continue1.200to4.000s withsupported10inner,SO0.5ms'),
('OneGPU, sameasR4; inneriterations only','OneGPU, sameasR4; timestep only'),
('longerpropagation20inner r7','longerpropagationhalfdt10inner r9'),
('Longer20inner propagation only aftermatchedmass/gaugeprobe','Longerhalfdt10inner propagation only aftermatchedmass/gaugeprobe'),
]:s=s.replace(x,y)
b.write_text(s)
print('R9 halfdt10inner longercontinuation prepared but strictlygatedonR8; notlaunched.')
