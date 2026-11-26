from pathlib import Path
import sys,json,csv,hashlib,subprocess,datetime,shutil,py_compile,difflib
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve()
assert run.is_relative_to(h/'cases/SP_C_split0_overset') and run.name=='c0_urans_continue_inner40_20261103_041433'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
state=read(h/'NIGHT_QUEUE_STATE.json');assert not state.get('active'),'Never overlap native jobs'
assert not (h.parent/'STOP_OWNED_CFD.json').exists() and not (h.parent/'PAUSED_FOR_HOME.json').exists()
decision=read(run/'work_stage_decision.json');assert decision.get('approved_next_diagnostic')=='pressure_urf_0p1'
source=run/'checkpoint.sim';cp=state['checkpoint_integrity'][str(source)];assert cp['native_save_complete']
with source.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest==cp['sha256'] and source.stat().st_size==cp['bytes']
last=list(csv.DictReader((run/'history.csv').open(encoding='utf8')))[-1]
t0=float(last['time_s']);native=int(last['native_iteration']);assert abs(t0-cp['saved_time_s'])<1e-9
assert float(last['p_absolute_min_Pa'])>12339.214766776897 and float(last['mass_imbalance_relative'])<1e-4
assert all(float(last[k])==0 for k in ['omega_floor_cells','k_floor_cells','overset_error_cells'])
name='C0URANSPressureUrf01';prefix='c0_urans_pressure_urf01_';macro=h/'macros'/(name+'.java');assert not macro.exists()
original=(h/'macros/C0URANSContinueInner40.java').read_text(encoding='utf8');s=original
s=s.replace('class C0URANSContinueInner40','class '+name).replace('c0_urans_continue_inner40_',prefix)
s=s.replace('cases/SP_C_split0_overset/c0_tight_urans_v2_20261103_035710/checkpoint.sim',source.relative_to(h).as_posix()).replace('d4b0c8eca2ff355739b2c1cfda79def31b56e48434c475976c157bce2bbfba55',digest)
s=s.replace('Math.abs(t0-(0.3))','Math.abs(t0-('+str(t0)+'))').replace('!=4560','!='+str(native))
start=s.index('Map<String,Double> sourceReports=');end=s.index('if(((FvRepresentation)',start)
rb='Map<String,Double> sourceReports=new LinkedHashMap<>();StringBuilder loaded=new StringBuilder("time="+t0+" native_iteration="+s.getSimulationIterator().getCurrentIteration()+"\\n");\n'
for key,report in [('Fx_N','HF_Fx_N'),('Fz_N','HF_Fz_N'),('Mh_Nm','HF_Mh_Nm'),('CL_hydro','HF_CL_hydro'),('CD','HF_CD')]:rb+='sourceReports.put("'+report+'",'+format(float(last[key]),'.17g')+');\n'
rb+='for(Map.Entry<String,Double> e:sourceReports.entrySet()){double value=rv(e.getKey());if(!Double.isFinite(value)||Math.abs(value-e.getValue())>1e-6*Math.max(1,Math.abs(e.getValue())))throw new IllegalStateException("Source report mismatch "+e.getKey());loaded.append(e.getKey()+"="+value+"\\n");}Files.writeString(out.resolve("checkpoint_readback.txt"),loaded.toString());\n'
s=s[:start]+rb+s[end:]
assert 'if(sourceInner!=15)' in s;s=s.replace('if(sourceInner!=15)','if(sourceInner!=40)').replace('requires source15inner','requires source40inner')
i=s.index('Files.writeString(out.resolve("inner_iteration_change.txt"),');j=s.index('\n',i)
block='flow.getPressureSolver().setUrf(.1);if(Math.abs(flow.getPressureSolver().getUrf()-.1)>1e-12)throw new IllegalStateException("Pressure relaxation change failed");\nFiles.writeString(out.resolve("pressure_relaxation_change.txt"),"pressure_urf=0.2 -> 0.1; velocity_urf=0.8 unchanged;40inner,dt0.002s,physics,geometry,mesh,schemes and saved fields/history retained. Added per-zone pressure location logging; no reset.");'
s=s[:i]+block+s[j:]
i=s.index('Files.writeString(out.resolve("numerical_change.txt"),');j=s.index('\n',i)
desc='Controlled0degree continuation from t'+str(t0)+'s,native'+str(native)+'. Only numerical change: pressureURF0.2to0.1. VelocityURF0.8,40inner,dt0.002s,SECOND_ORDER time/momentum/SST,DISTANCE,FLUX_CORRECTION,333939cells and physical geometry/conditions unchanged. Diagnose residual plateau and remote-top pressure oscillations. Added pressure-zone minimum coordinates each step. No reset,initialization or remesh. Maximum150steps,minimum75; strict guards unchanged; no nonzero angles or scientific approval.'
s=s[:i]+'Files.writeString(out.resolve("numerical_change.txt"),"'+desc+'");'+s[j:]
s=s.replace('CONT_C0_','PR01_C0_')
needle='try(BufferedWriter w=Files.newBufferedWriter(out.resolve("history.csv"))){'
assert s.count(needle)==1
replacement='try(BufferedWriter w=Files.newBufferedWriter(out.resolve("history.csv"));BufferedWriter zw=Files.newBufferedWriter(out.resolve("pressure_zones.csv"))){zw.write("step,time_s,zone,pabs_Pa,x_m,y_m,z_m\\n");zw.flush();'
s=s.replace(needle,replacement)
needle='double net=mass.getReportMonitorValue()'
assert s.count(needle)==1
zoneblock='for(String zone:zones){MinReport pr=(MinReport)s.getReportManager().getReport("HF_pabs_"+zone);double pv=pr.getReportMonitorValue();double[] pos=new double[3];for(int j=0;j<3;j++)pos[j]=pr.getCollocatedValue(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j));if(!Double.isFinite(pv+pos[0]+pos[1]+pos[2]))throw new IllegalStateException("Invalid pressure location");zw.write(String.format(Locale.ROOT,"%d,%.12g,%s,%.12g,%.12g,%.12g,%.12g\\n",k,t,zone,pv,pos[0],pos[1],pos[2]));}zw.flush();\n'
s=s.replace(needle,zoneblock+needle)
execute=s.split('public void execute(){',1)[1]
assert all(x not in execute for x in ['initializeSolution','clearSolution','pc.disableModel','pc.enable(','suspendMotionForSteady()'])
assert execute.count('setUrf(')==1 and 'setUrf(.1)' in execute
macro.write_text(s,encoding='utf8')
javac='C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe'
cpjava='E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*'
res=subprocess.run([javac,'-encoding','UTF-8','-cp',cpjava,'-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert res.returncode==0,res.stderr
(h/'audit/inner40_to_pressure_urf01.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='C0URANSContinueInner40.java',tofile=macro.name)),encoding='utf8')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for f in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/f,backup/f)
for file,needle,replacement in [('night_native.py','allowed={',"allowed={'"+macro.name+"':8,"),('night_queue.py','ALLOWED={',"ALLOWED={'"+macro.name+"',"),('night_dashboard.py','case={',"case={'"+macro.name+"':'C0 — kontrola relaksacji ciśnienia 0.1',")]:
 p=h/'tools'/file;text=p.read_text(encoding='utf8');assert macro.name not in text;text=text.replace(needle,replacement,1)
 if file=='night_queue.py':text=text.replace('prefix={',"prefix={'"+macro.name+"':'"+prefix+"',",1)
 p.write_text(text,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'NIGHT_QUEUE.json';cfg=read(p);job=dict(id='c0_urans_pressure_urf01',macro=macro.name,input=str(source),initial_time_s=t0,angle_deg=0,approved=True,purpose=desc,runtime_guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_turbulent_viscosity_ratio=99999,maximum_overset_error_cells=0))
assert cfg['scientific_gates']['C0_bias_explained_and_approved'] is False
assert not any(j['id']==job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=p.with_suffix('.work_tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(p)
event=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_pressure_relaxation_diagnostic_prepared',job=job,source_sha256=digest,source_native_iteration=native,source_time_s=t0,macro_sha256=hashlib.sha256(s.encode('utf8')).hexdigest(),scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(event)+'\n')
print(json.dumps(event,indent=2))
