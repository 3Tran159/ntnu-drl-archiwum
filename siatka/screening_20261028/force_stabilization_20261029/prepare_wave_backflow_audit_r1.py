from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'AuditWaveBackflow.java'; c=R/'run_wave_backflow_audit_r1.py'
if p.exists() or c.exists():raise RuntimeError('Preserve existing audit')
s=(R/'AuditWaveCheckpoint.java').read_text().replace('class AuditWaveCheckpoint','class AuditWaveBackflow')
s=s.replace('getWaveDampingLength";','getWaveDampingLength|getSelectedElement|getReversedFlowPressureOption|getBackflowVelocityDirectionOption|getReversedFlowScalarOption";')
anchor='    item.put("values",values);item.put("conditions",conditions);bc.add(item);'
extra='''    if(b.getBoundaryType() instanceof PressureBoundary){
     BackflowSpecification back=b.getConditions().get(BackflowSpecification.class);
     item.put("backflow_pressure",String.valueOf(back.getReversedFlowPressureOption().getSelectedElement()));
     item.put("backflow_direction",String.valueOf(back.getBackflowVelocityDirectionOption().getSelectedElement()));
     item.put("backflow_scalar",String.valueOf(back.getReversedFlowScalarOption().getSelectedElement()));
    }
'''
assert s.count(anchor)==1;s=s.replace(anchor,extra+anchor);p.write_text(s)
s=(R/'run_wave_checkpoint_audit_r1.py').read_text()
for a,b in [('W20_H24_X4_CPUprop_dt1ms_r2','W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3'),('W20_H24_X4_CPUprop_r2_field_audit_r1','W20_H24_X4_GPUprop_r3_backflow_audit_r1'),('wave_checkpoint_audit.lock','wave_backflow_audit.lock'),('wave_checkpoint_audit_state.json','wave_backflow_audit_state.json'),('AuditWaveCheckpoint','AuditWaveBackflow'),('running(15800) or running(36304)','running(28480)')]:s=s.replace(a,b)
c.write_text(s)
p=R/'WavePropagationForcingOutletR4.java'
s=p.read_text().replace('ArrayList<MassFlowReport> flux=new ArrayList<>();','ArrayList<String> fluxNames=new ArrayList<>();ArrayList<MassFlowReport> flux=new ArrayList<>();').replace('flux.add(r);}','flux.add(r);fluxNames.add(b.getPresentationName());}').replace('reg.getBoundaryManager().getBoundaries().get(k).getPresentationName()','fluxNames.get(k)')
p.write_text(s)
print('Prepared bounded zero-step backflow getter audit; no flow launch.')
