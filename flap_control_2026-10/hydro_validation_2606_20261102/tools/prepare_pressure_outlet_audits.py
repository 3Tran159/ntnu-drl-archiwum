from pathlib import Path
import json,datetime,shutil,hashlib,subprocess,py_compile
h=Path(__file__).resolve().parents[1];name='InspectPressureOutlets.java';macro=h/'macros'/name;s=macro.read_text(encoding='utf8')
helper='String fingerprint(Path p)throws Exception{java.security.MessageDigest md=java.security.MessageDigest.getInstance("SHA-256");try(InputStream stream=Files.newInputStream(p)){byte[] chunk=new byte[1048576];int n;while((n=stream.read(chunk))!=-1)md.update(chunk,0,n);}return java.util.HexFormat.of().formatHex(md.digest());}\n'
assert 'String fingerprint' not in s;s=s.replace('public void execute(){',helper+'public void execute(){',1)
needle='double t0=s.getSolution().getPhysicalTime();'
assert needle in s
s=s.replace(needle,'String expected=input.equals(b)?"5f9a86e51f8eb96cc1adb0fd36a61ae48e015600512598517b6ec2f6c9190ff1":"8b6162b9baa27a5e04c38048dbab3c801cdd99266200a320231390d1f3f8feed";if(!fingerprint(input).equals(expected))throw new IllegalStateException("Source fingerprint changed");\n'+needle)
s=s.replace('Files.writeString(out.resolve("pressure_outlet_setup.txt"),text.toString());','if(!fingerprint(input).equals(expected))throw new IllegalStateException("Source changed during inspection");Files.writeString(out.resolve("source_sha256_before_after.txt"),expected+"\\nunchanged=true\\n");\nFiles.writeString(out.resolve("pressure_outlet_setup.txt"),text.toString());')
macro.write_text(s,encoding='utf8')
cmd=['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)]
r=subprocess.run(cmd,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
backup=h/'runs/controller_snapshots'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
for file in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/file,backup/file)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert name not in t;t=t.replace('allowed={',"allowed={'"+name+"':1,",1).replace("['InspectHydroComparison.java','InspectBMatchingNumerics.java']","['InspectPressureOutlets.java','InspectHydroComparison.java','InspectBMatchingNumerics.java']");p.write_text(t,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+name+"',",1);t=t.replace("def output_path(receipt):","def output_path(receipt):\n if receipt['macro']=='InspectPressureOutlets.java':return H/'audit'/('pressure_outlets_'+receipt['variant']+'_'+receipt['run_id'])",1);p.write_text(t,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8');t=t.replace('case={',"case={'"+name+"':'Audyt granic ciśnieniowych — bez kroków solvera',",1);p.write_text(t,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'NIGHT_QUEUE.json';cfg=json.loads(p.read_text(encoding='utf8'))
for tag,source,t0 in [('c',h/'cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433/checkpoint.sim',.45),('b',h/'cases/SP_B_split0_fixed/SP_B_split0_stabilized_2606.sim',.3)]:
 job=dict(id=tag+'0_pressure_outlet_readonly_audit',macro=name,input=str(source),initial_time_s=t0,angle_deg=0,approved=True,purpose='Read-only actual top/downstream outlet backflow direction,pressure/scalar choices and pressure field definition.0solversteps,no.sim save,1CPU,noGPU;source SHA checked before/after. No boundary or physics changes.')
 assert not any(x['id']==job['id'] for x in cfg['jobs']);cfg['jobs'].append(job)
cfg['controller_exit_requested']=True;tmp=p.with_suffix('.work_tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(p)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_pressure_boundary_readonly_audits_queued',jobs=[j['id'] for j in cfg['jobs'][-2:]],macro_sha256=hashlib.sha256(s.encode('utf8')).hexdigest(),purpose='Investigate shared remote-top pressure/residual issue; no boundary changes or scientific approval.'))+'\n')
print(json.dumps(dict(prepared=name,jobs=[j['id'] for j in cfg['jobs'][-2:]],native_cpu_ranks=1,flow_steps=0,source_saves=0),indent=2))
