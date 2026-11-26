from pathlib import Path
import csv,json,hashlib,subprocess
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');W=Path(r'E:/ntnu/quasi2d_waves_20261029')
parent=W/'W01_W20L4_M10_FS020_cycles_r2';A=W/'W01_W20L4_M10_FS020_dt05_diagnostic_r3'
rows=list(csv.DictReader((parent/'history.csv').open()));row=next(r for r in rows if abs(float(r['time_s'])-.668)<1e-9)
if float(row['max_speed_m_s'])>=50 or float(row['alpha_min'])<0 or float(row['alpha_max'])>1:raise RuntimeError('Source sample guard failed')
s=(R/'W01ResumeCyclesR2.java').read_text()
def rep(a,b,n=1):
 global s
 if s.count(a)!=n:raise RuntimeError('Unexpected anchor '+a[:90]+' count='+str(s.count(a)))
 s=s.replace(a,b)
rep('public class W01ResumeCyclesR2','public class W01HalfDtDiagnosticR3')
s=s.replace('W01_W20L4_M10_FS020_cycles_r2','W01_W20L4_M10_FS020_dt05_diagnostic_r3')
rep('E:/ntnu/quasi2d_waves_20261029/W01_W20L4_M10_FS020_diagnostic_r1/final.sim',A.as_posix()+'/input.sim')
rep('double dt=.001;int steps=16778;','double dt=.0005;int steps=1064;')
rep('Math.abs(dt-.001)>1e-12||steps!=16778','Math.abs(dt-.0005)>1e-12||steps!=1064')
rep('getPhysicalTime()-.168','getPhysicalTime()-.668')
rep('Math.abs(us.getTimeStep().getValue()-dt)','Math.abs(us.getTimeStep().getValue()-.001)')
rep('throw new IllegalStateException("W01 resumed must retain checkpoint SO 1 ms settings");','throw new IllegalStateException("Source must be SO 1 ms before controlled half-dt change");us.getTimeStep().setValue(dt);if(Math.abs(us.getTimeStep().getValue()-.0005)>1e-12)throw new IllegalStateException("Half-dt getter mismatch");')
rep('"target_time_s",16.946','"target_time_s",1.2')
rep('Live saved-state continuation W01: H0.5m L20m H24m M10 FS020; resumes .168s with unchanged SO1ms10inner pressuretol.01; no startup or reinitialization. Evaluate cycle repeatability from10 periods, save/review cap20 periods.','Controlled half-dt diagnostic W01 from valid0.668s checkpoint to1.2s. ONLY physical dt1ms to0.5ms; SO10inner pressuretol.01, BCs and fields unchanged. No startup or reinitialization. Short diagnostic, not cycle acceptance.')
rep('(40.76465590181842)','('+row['Fx_slice_N']+')');rep('(802.7692557120714)','('+row['Fz_slice_N']+')')
s=s.replace('restart_state_t0.168.sim','restart_state_t0.668.sim')
rep('"time_s",.168','"time_s",.668')
rep('wall>50400','wall>7200')
# Keep every step in the terminal guard evidence, including the failing step.
rep('{status="stability_guard";break;}','{Files.writeString(out.resolve("physical_guard.json"),json(Map.of("time_s",t,"speed",v,"max_CFL",co,"interface_CFL",ci,"alpha_min",mn,"alpha_max",mx,"mass_kg",m,"net_mass_kg_s",net)));status="stability_guard";break;}')
s=s.replace('W01 resumed','W01 half-dt diagnostic')
s=s.replace('W01R2_','W01R3_')
(R/'W01HalfDtDiagnosticR3.java').write_text(s,encoding='utf8')
plan=dict(status='prepared_pending_compile_and_launch',case=A.name,source=str(parent/'checkpoint_t0.668.sim'),source_time_s=.668,source_history_sample=row,target_s=1.2,dt_s=.0005,steps=1064,inner=10,changes={'dt_s':[.001,.0005]},reinitialized=False,physical_speed_guard_m_s=50,source_is_guard_failed=False,reason='Air jet51.7866m/s in core at1.064 on1msbranch; wave-specific controlled temporal diagnosis on foil grid, distinct from historical no-foil mass-residual tests.',source_sha256=hashlib.sha256((parent/'checkpoint_t0.668.sim').read_bytes()).hexdigest())
base='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java'
cp=';'.join(base+'/'+x for x in ['platform/modules/ext/*','platform/modules/*','platform/core/*'])
folder=R/'wave_halfdt_r3_classes';folder.mkdir(exist_ok=True)
p=subprocess.run([r'C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','--release','17','-cp',cp,'-d',str(folder),str(R/'W01HalfDtDiagnosticR3.java')],capture_output=True,text=True)
(R/'wave_halfdt_r3_compile.log').write_text(p.stdout+p.stderr);plan['macro_compile_pass']=p.returncode==0;plan['macro_sha256']=hashlib.sha256((R/'W01HalfDtDiagnosticR3.java').read_bytes()).hexdigest()
(R/'wave_halfdt_r3_plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps(plan,indent=2))
if p.returncode:print(p.stderr);raise SystemExit(p.returncode)
