from pathlib import Path
import json,hashlib,subprocess,csv
R=Path(__file__).resolve().parent;A=Path('E:/ntnu/quasi2d_waves_20261029/C01_W20L4_M10_calm_settle_r2')
s=(R/'LocalCalmWave.java').read_text()
def rep(a,b):
 global s
 if s.count(a)!=1:raise RuntimeError('Unexpected anchor '+a[:70])
 s=s.replace(a,b)
rep('public class LocalCalmWave','public class C01HalfDtProbeR3')
rep('if(Math.abs(dt-.001)>1e-12||steps<30||steps>50000)throw new IllegalStateException("Manual run requires 1 ms and a bounded target");','if(Math.abs(dt-.0005)>1e-12||steps!=2126||Math.abs(sourceTime-1.837)>1e-9||!mode.equals("calm"))throw new IllegalStateException("Bounded C01 half-dt diagnostic only");')
rep('if(Math.abs(us.getTimeStep().getValue()-dt)>1e-12||!String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()).equals("SECOND_ORDER"))throw new IllegalStateException("Inspect must retain checkpoint SO 1 ms settings");','if(Math.abs(us.getTimeStep().getValue()-.001)>1e-12||!String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()).equals("SECOND_ORDER"))throw new IllegalStateException("Source must retain SO1ms settings");us.getTimeStep().setValue(dt);if(Math.abs(us.getTimeStep().getValue()-.0005)>1e-12)throw new IllegalStateException("Halfdt getter failed");Files.writeString(out.resolve("timestep_change.json"),json(Map.of("old_dt_s",.001,"new_dt_s",dt,"source_time_s",sourceTime,"target_time_s",2.9,"inner",10,"wave_active",false,"only_numerical_change","global_dt","first_step_external_BDF2","unavailable mixed spacing; native after-step report retained","constant_BDF2_from_s",1.838)));')
rep('if(step>0&&step%250==0){String cp=','if(step>0&&step%100==0){String cp=')
rep('Map.of("file",out.resolve(cp).toString(),"time_s",t,"completed_save",true)','Map.of("file",out.resolve(cp).toString(),"time_s",t,"completed_save",true,"guard_checked",true,"max_speed_m_s",v,"alpha_min",mn,"alpha_max",mx,"kind","diagnostic_checkpoint_not_settled")')
rep('if(step>0 && (step%250==0 || ((100*','if(step>0 && (step%250==0 || step==380 || step==1880 || ((100*')
needle='     if(!Double.isFinite(mn)||'
pos=s.index(needle)
insert='''     if(step==0){
      double[] f=forces();double[] actualFp={v,m,w,f[0],f[1],f[2],f[3]};String[] names={"speed","mass","water_volume","Fx","Fz","pressure_drag","viscous_drag"};Map<String,Object> check=new LinkedHashMap<>();
      for(int k=0;k<names.length;k++){double expected=Double.parseDouble(System.getenv("NTNU_FP_"+names[k]));if(!Double.isFinite(actualFp[k])||Math.abs(actualFp[k]-expected)>1e-8*Math.max(1,Math.abs(expected)))throw new IllegalStateException("Source field fingerprint mismatch "+names[k]);check.put(names[k],actualFp[k]);}
      check.put("time_s",t);check.put("reinitialized",false);check.put("relative_tolerance",1e-8);Files.writeString(out.resolve("source_field_fingerprint.json"),json(check));
     }
'''
s=s[:pos]+insert+s[pos:]
s=s.replace('Only numericalchange pressure relativeAMGtolerance0.1to0.01; VOFtol0.1, allothercontrols unchanged; everyinnernative and LOWtrace retained','Only numerical change global dt1ms to0.5ms;10inner, pressuretol.01,VOFtol.1 unchanged. No generated wave.')
s=s.replace('User-selected exploratory case: see request and requested_wave_audit. Guarded startup0.5ms50inner40steps then SO1ms10inner; pressuretol0.01. User accepts prior observed mass deviation for exploration; original0.01percent remains a diagnostic flag.','C01 diagnostic from1.837 to2.900; onlydt1ms to0.5ms; noinit/noincidentwave;10inner pressuretol.01 retained; no automaticcalm/waveadmission.')
assert 'initializeSolution(' not in s and 'clearSolution(' not in s and 'v>50' in s
p=R/'C01HalfDtProbeR3.java'
if p.exists():raise RuntimeError('Unique diagnostic macro exists; inspect before rebuilding')
p.write_text(s,encoding='utf8')
base='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java'
cp=';'.join(base+'/'+x for x in ['platform/modules/ext/*','platform/modules/*','platform/core/*'])
out=R/'c01_halfdt_probe_r3_classes';out.mkdir(exist_ok=True)
proc=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','--release','17','-cp',cp,'-d',str(out),str(p)],capture_output=True,text=True)
(R/'c01_halfdt_probe_r3_compile.log').write_text(proc.stdout+proc.stderr)
receipt=dict(status='javac_passed' if proc.returncode==0 else 'failed',macro_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),dt_s=.0005,steps=2126,source_time_s=1.837,target_time_s=2.9,checkpoint_interval_s=.05,wave_active=False,no_reinitialization=True)
(R/'c01_halfdt_probe_r3_build_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
if proc.returncode:print(proc.stderr)
raise SystemExit(proc.returncode)
