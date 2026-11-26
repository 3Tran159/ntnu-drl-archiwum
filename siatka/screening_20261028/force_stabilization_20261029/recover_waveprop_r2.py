from pathlib import Path
import json,datetime
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
assert not (W/'preparation.lock').exists()
p=R/'WavePropagationCheck.java';s=p.read_text()
a='FieldFunction alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater");'
b='// Fresh zero-time pilot: reinitialize the disposable copy so wave-function caches are evaluated after load.\n   s.getSolution().clearSolutionWithoutMeshReset();s.getSolution().initializeSolution();\n   if(Math.abs(s.getSolution().getPhysicalTime())>1e-10)throw new IllegalStateException("Initialization advanced physical time");\n   '+a
assert s.count(a)==1;s=s.replace(a,b)
a='if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a)>1.5)throw new IllegalStateException("Invalid wave gauge");'
b='if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a)>1.5){Files.writeString(out.resolve("gauge_error.json"),json(Map.of("time_s",t,"x_m",xs[k],"actual_eta_m",a,"analytic_eta_m",b,"actual_error",actual.get(k).getErrorLog(),"analytic_error",analytic.get(k).getErrorLog())));throw new IllegalStateException("Invalid wave gauge at x="+xs[k]+" actual="+a+" analytic="+b);}'
assert s.count(a)==1;s=s.replace(a,b)
p.write_text(s)
s=(R/'run_wave24m_propagation_r1.py').read_text().replace("W20_H24_X4_CPUprop_dt1ms_r1","W20_H24_X4_CPUprop_dt1ms_r2")
(R/'run_wave24m_propagation_r2.py').write_text(s)
(R/'wave_propagation_r1_failure.json').write_text(json.dumps({'updated_at':datetime.datetime.now().astimezone().isoformat(),'status':'zero_step_gauge_guard','physical_steps':0,'preserved_attempt':'W20_H24_X4_CPUprop_dt1ms_r1','evidence':'history has onlyt0 finite independent volume/speed/alpha/CFL; first derived-plane gauge failed before any transientstep. R5zero-step gauges were valid.','recovery':'Newr2 reinitializes disposablezero-timecopy, checksfirstgauges andrecords exactreporterrors iffailure; guardsunchanged. Cause notyetproven.'},indent=2))
print('Prepared new zero-time reinitialization attempt r2; r1 preserved')
