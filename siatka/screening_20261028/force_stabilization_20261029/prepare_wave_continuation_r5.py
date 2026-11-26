from pathlib import Path
R=Path(__file__).resolve().parent
a=R/'WavePropagationContinuationR5.java';b=R/'run_wave_continuation_r5.py'
if a.exists() or b.exists():raise RuntimeError('Preserve R5')
s=(R/'WavePropagationEnvironmentalOutletR4.java').read_text().replace('class WavePropagationEnvironmentalOutletR4','class WavePropagationContinuationR5')
s=s.replace('steps>2000','steps>3000')
s=s.replace('||Math.abs(s.getSolution().getPhysicalTime())>1e-10','||Math.abs(s.getSolution().getPhysicalTime()-1.2)>1e-8')
start=s.index('   // Match the damped outlet')
end=s.index('   FieldFunction alpha=',start)
replacement=r'''   double initialTime=s.getSolution().getPhysicalTime();
   Boundary outlet=reg.getBoundaryManager().getBoundary("DOMAIN.outlet"),bed=reg.getBoundaryManager().getBoundary("DOMAIN.bottom");
   if(!String.valueOf(outlet.getConditions().get(BackflowSpecification.class).getReversedFlowPressureOption().getSelectedElement()).equals("ENVIRONMENTAL")||!String.valueOf(bed.getConditions().get(WallShearStressOption.class).getSelectedElement()).equals("SLIP"))throw new IllegalStateException("Checkpoint boundary settings mismatch");
   Files.writeString(out.resolve("continuation_identity.json"),json(Map.of("initial_time_s",initialTime,"target_time_s",4.0,"reinitialized",false,"outlet_backflow","ENVIRONMENTAL","bottom","SLIP","scope","Longer propagation continuation; no foil forces and no final reflection claim")));
'''
s=s[:start]+replacement+s[end:]
old='   UserFieldFunction one=s.getFieldFunctionManager().createFieldFunction();one.setFunctionName("PropagationUnit");one.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);one.setDefinition("1.0");'
assert old in s;s=s.replace(old,'   FieldFunction one=s.getFieldFunctionManager().getFunction("PropagationUnit");')
s=s.replace('Math.abs(t-step*dt)','Math.abs(t-(initialTime+step*dt))')
a.write_text(s)
c=(R/'run_wave_environmental_outlet_r4.py').read_text()
for old,new in [
('W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4','W20_H24_X4_GPUprop_environmentalOutlet_long_dt1ms_r5'),
('wave_environmental_outlet_r4.lock','wave_continuation_r5.lock'),
('WavePropagationEnvironmentalOutletR4','WavePropagationContinuationR5'),
("NTNU_WAVE_STEPS='1200'","NTNU_WAVE_STEPS='2800'"),
("done.get('steps')==1200","done.get('steps')==2800"),
("source=srcdir/'built.sim'","source=W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'/'final.sim'"),
("if (W/'preparation.lock').exists() or running(28480) or running(14348):raise RuntimeError('Prior campaign or CPU pilot/audit still active')",
"if running(15556):raise RuntimeError('Prior GPU pilot still active')\n cpu=e.read(W/'preparation.lock',{})\n if cpu and cpu.get('purpose')!='Paired foil calm/W01 zero-step CPU1 preparation':raise RuntimeError('Other CPU owner; inspect resources first')"),
('Fresh no-foil GPU pilot after the audited outlet-boundary correction. Never reuses failed flow.','Continue only the reviewed stable R4 checkpoint to4s; no source modification or reinitialization.'),
('no-foil GPU pilot r4','no-foil GPU continuation r5'),
("prior_failed_attempt='W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3'","prior_failed_attempt='W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3',restart_from='reviewed r4 t1.2 checkpoint'"),
("change='Outlet backflow pressure STATIC to ENVIRONMENTAL plus bottom symmetry to slip wall. Flat outlet pressure/phase and damping remain; top unchanged. Two documented changes, not isolated causal proof.'","change='No numerical/boundary change; continue reviewed stable R4 t1.2 to4.0s without reinitialization'"),
]:c=c.replace(old,new)
anchor=" if case.exists():raise RuntimeError('Attempt exists; preserve and use new ID')"
checks=r''' prior=e.read(W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'/'controller_result.json',{})
 review=e.read(R/'wave_pilot_r4_review.json',{});sp=e.read(R/'wave_pilot_r4_spatial_diagnostic.json',{})
 if not prior.get('source_unchanged') or prior.get('completed',{}).get('status')!='target_reached' or prior.get('completed',{}).get('steps')!=1200:raise RuntimeError('R4 not completed safely')
 if not review.get('independent_histories_finite') or not sp.get('all_fields_finite'):raise RuntimeError('R4 independent review absent')
 if sp['max_speed']['speed_m_s']>25 or review['BDF2_budget_after_0p2_max_abs_pct_inlet']>.01:raise RuntimeError('R4 spatial/conservation diagnostic requires investigation')
 if max(x['RMS_error_mm'] for x in review['gauges'])>10 or max(x['max_error_mm'] for x in review['gauges'])>20:raise RuntimeError('R4 gauge mismatch too large for longer continuation')
'''
assert c.count(anchor)==1;c=c.replace(anchor,checks+anchor)
b.write_text(c)
print('Bounded R4-to4s continuation prepared; not launched. Scientific checkpoint review required.')
