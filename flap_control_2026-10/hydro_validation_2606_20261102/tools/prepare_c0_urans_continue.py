from pathlib import Path
import sys,json,csv,hashlib,subprocess,re,datetime,shutil,py_compile
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve();checkpoint=sys.argv[2];inner=int(sys.argv[3])
assert run.is_relative_to(h/'cases/SP_C_split0_overset') and inner in [15,40]
assert checkpoint=='checkpoint.sim' or re.fullmatch(r'checkpoint_step_\d+\.sim',checkpoint)
read=lambda p:json.loads(p.read_text(encoding='utf8'))
state=read(h/'NIGHT_QUEUE_STATE.json');assert not state.get('active'),'Do not overlap STAR jobs'
assert not (h.parent/'STOP_OWNED_CFD.json').exists() and not (h.parent/'PAUSED_FOR_HOME.json').exists()
decision=read(run/'work_stage_decision.json');assert decision.get('continuation_approved') is True and decision.get('approved_inner_iterations')==inner
source=run/checkpoint;cache=state['checkpoint_integrity'][str(source)];assert cache['native_save_complete']
digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest();assert digest==cache['sha256'] and source.stat().st_size==cache['bytes']
rows=list(csv.DictReader((run/'history.csv').open()));selected=[r for r in rows if abs(float(r['time_s'])-cache['saved_time_s'])<1e-9];assert len(selected)==1;last=selected[0]
t0=float(last['time_s']);native=int(last['native_iteration'])
assert float(last['p_absolute_min_Pa'])>12339.214766776897 and float(last['mass_imbalance_relative'])<1e-4 and float(last['min_volume_m3'])>0
assert all(float(last[x])==0 for x in ['omega_floor_cells','k_floor_cells','overset_error_cells']) and float(last['max_turbulent_viscosity_ratio'])<99999
name='C0URANSContinueInner'+str(inner);prefix='c0_urans_continue_inner'+str(inner)+'_';macro=h/'macros'/(name+'.java');assert not macro.exists(),'New unique reviewed continuation required'
s=(h/'macros/C0TightURANSV2.java').read_text(encoding='utf8')
s=s.replace('class C0TightURANSV2','class '+name).replace('c0_tight_urans_v2_',prefix)
s=s.replace('cases/SP_C_split0_overset/c0_tight_turbulence_second_20261103_034119/steady_checkpoint.sim',source.relative_to(h).as_posix()).replace('3575fad827e54ce942afada6d6c58a1c5cb5cd580e1da0f6065ff05f43b7fe6b',digest)
s=s.replace('Math.abs(t0)>1e-12','Math.abs(t0-('+str(t0)+'))>1e-9').replace('!=2310','!='+str(native))
s=s.replace('pc.getModelManager().getModel(SteadyModel.class)==null','pc.getModelManager().getModel(ImplicitUnsteadyModel.class)==null').replace('Reviewed steady seed expected','Saved unsteady checkpoint required')
start=s.index('Map<String,Double> sourceReports=');end=s.index('if(((FvRepresentation)',start)
rb='Map<String,Double> sourceReports=new LinkedHashMap<>();StringBuilder loaded=new StringBuilder("time="+t0+" native_iteration="+s.getSimulationIterator().getCurrentIteration()+"\\n");\n'
for key,report in [('Fx_N','HF_Fx_N'),('Fz_N','HF_Fz_N'),('Mh_Nm','HF_Mh_Nm'),('CL_hydro','HF_CL_hydro'),('CD','HF_CD')]:rb+='sourceReports.put("'+report+'",'+format(float(last[key]),'.17g')+');\n'
rb+='for(Map.Entry<String,Double> e:sourceReports.entrySet()){double value=rv(e.getKey());if(!Double.isFinite(value)||Math.abs(value-e.getValue())>1e-6*Math.max(1,Math.abs(e.getValue())))throw new IllegalStateException("Source report mismatch "+e.getKey());loaded.append(e.getKey()+"="+value+"\\n");}Files.writeString(out.resolve("checkpoint_readback.txt"),loaded.toString());\n'
s=s[:start]+rb+s[end:]
start=s.index('steadyResume=true;suspendMotionForSteady();');end=s.index('StringBuilder converted=',start)
block='''savedFlapBounds=flapBounds();Motion currentMotion=s.getRegionManager().getRegion("FlapOverset").getValues().get(MotionSpecification.class).getMotion();
if(!(currentMotion instanceof RotatingMotion)||!(((RotatingMotion)currentMotion).getRotationSpecification() instanceof RotationAngle))throw new IllegalStateException("Stored prescribed rotation missing");
String angleLaw=((RotationAngle)((RotatingMotion)currentMotion).getRotationSpecification()).getRotationAngle().getDefinition();if(Math.abs(Double.parseDouble(angleLaw.replace("<","").replace("deg>","").trim()))>1e-12)throw new IllegalStateException("Only0degree continuation authorized");
ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);if(Math.abs(us.getTimeStep().getValue()-.002)>1e-12||us.getTimeDiscretizationOption().getSelected()!=TimeDiscretizationOption.Type.SECOND_ORDER.getValue())throw new IllegalStateException("Source time settings mismatch");
SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);if(Math.abs(flow.getVelocitySolver().getUrf()-.8)>1e-12||Math.abs(flow.getPressureSolver().getUrf()-.2)>1e-12||flow.getVelocitySolver().getUseDynamicLocalUrf())throw new IllegalStateException("Source B-matched relaxation mismatch");
int sourceInner=-1;for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){if(c instanceof InnerIterationStoppingCriterion){sourceInner=((InnerIterationStoppingCriterion)c).getMaximumNumberInnerIterations();if(!c.getIsUsed())throw new IllegalStateException("Inner stopping criterion disabled");}else c.setIsUsed(false);}
if(sourceInner!=15)throw new IllegalStateException("This reviewed continuation requires source15inner; do not silently change another source");
for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects())if(c instanceof InnerIterationStoppingCriterion)((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(@INNER@);
Files.writeString(out.resolve("inner_iteration_change.txt"),"source_inner="+sourceInner+" target_inner=@INNER@; all physics,mesh,time step,schemes,relaxations and saved fields/history retained; no clearing,conversion or initialization");
checkPose("continuation_initial");if(s.getSolution().getPhysicalTime()!=t0||s.getSimulationIterator().getCurrentIteration()!=@NATIVE@)throw new IllegalStateException("Continuation altered counters");
'''.replace('@INNER@',str(inner)).replace('@NATIVE@',str(native))
s=s[:start]+block+s[end:]
s=s.replace('conversion_readback.txt','continuation_readback.txt').replace('Conversion altered report','Continuation altered report').replace('URANS_ready.sim','continuation_ready.sim').replace('urans_ready','continuation_ready')
i=s.index('Files.writeString(out.resolve("numerical_change.txt"),');j=s.index('\n',i)
desc='Continue exact saved URANS fields at t'+str(t0)+'s,native'+str(native)+'. Source15inner,target'+str(inner)+'. dt0.002s,SECOND_ORDER time/momentum/SST,URF0.8/0.2,DISTANCE,FLUX_CORRECTION,333939cells,0degree geometry unchanged. No conversion,reset,initialization or mesh generation. Strict guards retained. Numerical sensitivity/resume only; no scientific approval.'
s=s[:i]+'Files.writeString(out.resolve("numerical_change.txt"),"'+desc+'");'+s[j:]
s=s.replace('k<=500','k<=150').replace('k>=150','k>=75').replace('URANS_C0_','CONT_C0_')
execute=s.split('public void execute(){',1)[1]
assert all(x not in execute for x in ['initializeSolution','clearSolution','pc.disableModel','pc.enable(','suspendMotionForSteady()'])
macro.write_text(s,encoding='utf8')
res=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert res.returncode==0,res.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for f in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/f,backup/f)
for file,needle,replacement in [('night_native.py','allowed={',"allowed={'"+macro.name+"':8,"),('night_queue.py','ALLOWED={',"ALLOWED={'"+macro.name+"',"),('night_dashboard.py','case={',"case={'"+macro.name+"':'C0 — URANS, "+str(inner)+" iteracji wewnetrznych',")]:
 p=h/'tools'/file;text=p.read_text(encoding='utf8');assert macro.name not in text;text=text.replace(needle,replacement,1)
 if file=='night_queue.py':text=text.replace('prefix={',"prefix={'"+macro.name+"':'"+prefix+"',",1)
 p.write_text(text,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'NIGHT_QUEUE.json';cfg=read(p);job=dict(id='c0_urans_continue_inner'+str(inner),macro=macro.name,input=str(source),initial_time_s=t0,angle_deg=0,approved=True,purpose=desc,runtime_guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_turbulent_viscosity_ratio=99999,maximum_overset_error_cells=0))
assert not any(j['id']==job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(p)
event=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_urans_continuation_prepared',job=job,source_sha256=digest,source_native_iteration=native,source_time_s=t0,scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(event)+'\n')
print(json.dumps(event,indent=2))
