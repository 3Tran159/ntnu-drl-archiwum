from pathlib import Path
import json,hashlib,py_compile
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=R/'M04_until_settled_r2/final.sim';copy=Path('E:/ntnu/temporal_conservation_20261029/r1/M04_start.sim')
assert sha(source)==sha(copy)
Path('E:/ntnu/temporal_conservation_20261029/r1/source_preservation_check.json').write_text(json.dumps({'source_unchanged_compared_to_copy':True,'sha256':sha(source),'failure':'isInitialized flag false on CPU load; no initialization or solving attempted'}),encoding='utf-8')
p=R/'AuditTemporalMassR2.java'
if p.exists():raise RuntimeError('R2 already prepared')
s=(R/'AuditTemporalMassR1.java').read_text().replace('AuditTemporalMassR1','AuditTemporalMassR2').replace('20261029/r1','20261029/r2')
s=s.replace('if(!s.getSolution().isInitialized())throw new IllegalStateException("No initialized saved solution");','boolean initializedFlag=s.getSolution().isInitialized();')
s=s.replace('d.put("gpu_count",s.getNumberOfGpgpus());','d.put("gpu_count",s.getNumberOfGpgpus());d.put("initialized_flag_on_load",initializedFlag);\n  Boundary foil=r.getBoundaryManager().getBoundary("HF_012_wall");\n  ForceReport force=s.getReportManager().createReport(ForceReport.class);force.getParts().setObjects(foil);force.setRepresentation(fv);force.getForceOption().setSelected(ForceReportForceOption.Type.PRESSURE_AND_SHEAR);force.getDirection().setComponents(1,0,0);d.put("saved_Fx_N",force.getReportMonitorValue());force.getDirection().setComponents(0,0,1);d.put("saved_Fz_N",force.getReportMonitorValue());')
s=s.replace('if(o instanceof Number||o instanceof Boolean)return o.toString();','if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";if(o instanceof Boolean)return o.toString();')
p.write_text(s,encoding='utf-8')
s=(R/'audit_temporal_mass_copies_r1.py').read_text().replace('20261029/r1','20261029/r2').replace('AuditTemporalMassR1','AuditTemporalMassR2')
s=s.replace("outputs.append({'name':name", """audit=json.loads(result.read_text());expected=json.loads((src.parent/'progress.json').read_text())
  checks={'Fx':abs(audit['saved_Fx_N']/(expected['CD']*3855.6)-1),'Fz':abs(audit['saved_Fz_N']/(expected['CL_total']*3855.6)-1),'time_s':abs(audit['time_s']-expected['time_s'])}
  write(A/(name+'_field_crosscheck.json'),checks)
  if checks['Fx']>1e-5 or checks['Fz']>1e-5 or checks['time_s']>1e-9:raise RuntimeError(name+': loaded field does not match saved independent reports')
  outputs.append({'name':name""")
s=s.replace("str(A),'cases':[x['name'] for x in outputs]","str(A),'field_force_crosschecks_passed':True,'cases':[x['name'] for x in outputs]")
p=R/'audit_temporal_mass_copies_r2.py';p.write_text(s,encoding='utf-8');py_compile.compile(str(p),doraise=True)
print('R1 preserved; R2 uses exact physical-time and independent saved-force crosschecks without initialization.')
