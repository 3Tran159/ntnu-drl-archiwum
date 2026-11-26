from pathlib import Path
import json,datetime,hashlib,subprocess,shutil,py_compile,difflib
h=Path(__file__).resolve().parents[1];read=lambda p:json.loads(p.read_text(encoding='utf8'))
state=read(h/'NIGHT_QUEUE_STATE.json');assert not state.get('active'),'Wait for owned inspection to finish'
decision=read(h/'audit/C0_top_backflow_test_decision.json');assert decision['diagnostic_approved'] and not decision['scientific_approved']
assert not (h.parent/'STOP_OWNED_CFD.json').exists() and not (h.parent/'PAUSED_FOR_HOME.json').exists()
name='C0URANSTopDirection';prefix='c0_top_direction_';macro=h/'macros'/(name+'.java');assert not macro.exists()
source=h/'cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433/checkpoint.sim'
with source.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest=='8b6162b9baa27a5e04c38048dbab3c801cdd99266200a320231390d1f3f8feed'
original=(h/'macros/C0URANSPressureUrf01.java').read_text(encoding='utf8');s=original.replace('class C0URANSPressureUrf01','class '+name).replace('c0_urans_pressure_urf01_',prefix).replace('PR01_C0_','TOPDIR_C0_')
i=s.index('flow.getPressureSolver().setUrf(.1);');j=s.index('\ncheckPose("continuation_initial")',i)
block='''Boundary top=null;for(Boundary wall:s.getRegionManager().getRegion("Background").getBoundaryManager().getBoundaries())if(wall.getPresentationName().endsWith(".top")){if(top!=null)throw new IllegalStateException("Ambiguous top boundary");top=wall;}
if(top==null||!(top.getBoundaryType() instanceof PressureBoundary))throw new IllegalStateException("Expected pressure top boundary");
BackflowSpecification back=top.getConditions().get(BackflowSpecification.class);
if(back.getBackflowVelocityDirectionOption().getSelected()!=BackflowVelocityDirectionOption.Type.BOUNDARY_NORMAL.getValue()||back.getReversedFlowPressureOption().getSelected()!=ReversedFlowPressureOption.Type.ENVIRONMENTAL.getValue())throw new IllegalStateException("Top backflow source differs from native audit");
ScalarProfile tp=top.getValues().get(StaticPressureProfile.class);if(!(tp.getMethod() instanceof FunctionScalarProfileMethod))throw new IllegalStateException("Top pressure method differs");
FieldFunction tpf=tp.getMethod(FunctionScalarProfileMethod.class).getFieldFunction();if(!(tpf instanceof UserFieldFunction)||!((UserFieldFunction)tpf).getDefinition().equals("<0 Pa>"))throw new IllegalStateException("Top pressure definition differs");
int pressureOption=back.getReversedFlowPressureOption().getSelected(),scalarOption=back.getReversedFlowScalarOption().getSelected();
back.getBackflowVelocityDirectionOption().setSelected(BackflowVelocityDirectionOption.Type.EXTRAPOLATED);
if(back.getBackflowVelocityDirectionOption().getSelected()!=BackflowVelocityDirectionOption.Type.EXTRAPOLATED.getValue()||back.getReversedFlowPressureOption().getSelected()!=pressureOption||back.getReversedFlowScalarOption().getSelected()!=scalarOption)throw new IllegalStateException("Unexpected backflow change");
Files.writeString(out.resolve("top_backflow_change.txt"),"Only top backflow direction BOUNDARY_NORMAL -> EXTRAPOLATED. Environmental backflow pressure,scalar specification,piezometric0Pa and downstream outlet unchanged. URFvelocity0.8/pressure0.2,40inner,dt0.002 unchanged. Physical geometry,fields,time/history retained. Separate boundary diagnostic; oldB is not a matched new-boundary reference.");
'''
s=s[:i]+block+s[j:]
i=s.index('Files.writeString(out.resolve("numerical_change.txt"),');j=s.index('\n',i)
desc='Controlled0degree branch from C40t0.45s,native7560. Only boundary change: TOP backflow direction BOUNDARY_NORMAL to EXTRAPOLATED, following installed manual for flow parallel to pressure boundary. Preserve environmental pressure/scalars,downstream boundary,URF0.8/0.2,40inner,dt0.002s,SECOND_ORDER all,DISTANCE,FLUX_CORRECTION,333939cells,geometry,fields and saved time. No initialization,reset or remesh. Added far-top velocity metrics. Minimum100,maximum250timesteps. Not yet comparable as pureOverset effect against oldB; matched baseline follow-up required. Strict guards unchanged; no nonzero angles.'
s=s[:i]+'Files.writeString(out.resolve("numerical_change.txt"),"'+desc+'");'+s[j:]
s=s.replace('k<=150','k<=250').replace('k>=75&&','k>=100&&')
needle='List<double[]> samples=new ArrayList<>();note("Matched0degree URANS diagnostic started from retained fields");'
assert s.count(needle)==1
far='''UserFieldFunction farMask=field("TOPDIR_FarMask","($$Position[0] > <10 m> && $$Position[0] < <43 m> && $$Position[2] > <7 m> && $$Position[2] < <8 m>) ? 1 : 0",new Dimensions());
ThresholdPart farPart=s.getPartManager().createThresholdPart();farPart.setPresentationName("Top boundary diagnostic band");farPart.getInputParts().setObjects(List.of(s.getRegionManager().getRegion("Background")));farPart.setFieldFunction(farMask);farPart.setRange(new DoubleVector(new double[]{.5,1.5}));farPart.setMode(ThresholdMode.BETWEEN_TAG);
FieldFunction vx=s.getFieldFunctionManager().getFunction("Velocity").getComponentFunction(0),vz=s.getFieldFunctionManager().getFunction("Velocity").getComponentFunction(2);
VolumeAverageReport farVxMean=s.getReportManager().createReport(VolumeAverageReport.class);farVxMean.getParts().setObjects(farPart);farVxMean.setFieldFunction(vx);
MinReport farVxMin=s.getReportManager().createReport(MinReport.class),farVzMin=s.getReportManager().createReport(MinReport.class);
MaxReport farVxMax=s.getReportManager().createReport(MaxReport.class),farVzMax=s.getReportManager().createReport(MaxReport.class);
farVxMin.getParts().setObjects(farPart);farVxMin.setFieldFunction(vx);farVxMax.getParts().setObjects(farPart);farVxMax.setFieldFunction(vx);farVzMin.getParts().setObjects(farPart);farVzMin.setFieldFunction(vz);farVzMax.getParts().setObjects(farPart);farVzMax.setFieldFunction(vz);
'''
s=s.replace(needle,far+needle.replace('Matched0degree','Top-backflow0degree'))
needle='BufferedWriter zw=Files.newBufferedWriter(out.resolve("pressure_zones.csv"))){'
assert s.count(needle)==1
s=s.replace(needle,'BufferedWriter zw=Files.newBufferedWriter(out.resolve("pressure_zones.csv"));BufferedWriter fw=Files.newBufferedWriter(out.resolve("far_top_metrics.csv"))){fw.write("step,time_s,vx_volume_mean_m_s,vx_min_m_s,vx_max_m_s,vz_min_m_s,vz_max_m_s\\n");fw.flush();')
needle='double net=mass.getReportMonitorValue()'
assert s.count(needle)==1
farline='double fvxm=farVxMean.getReportMonitorValue(),fvxn=farVxMin.getReportMonitorValue(),fvxx=farVxMax.getReportMonitorValue(),fvzn=farVzMin.getReportMonitorValue(),fvzx=farVzMax.getReportMonitorValue();if(!Double.isFinite(fvxm+fvxn+fvxx+fvzn+fvzx))throw new IllegalStateException("Invalid far-top velocity metrics");fw.write(String.format(Locale.ROOT,"%d,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\\n",k,t,fvxm,fvxn,fvxx,fvzn,fvzx));fw.flush();\n'
s=s.replace(needle,farline+needle)
execute=s.split('public void execute(){',1)[1];assert all(x not in execute for x in ['initializeSolution','clearSolution','pc.disableModel','pc.enable(','setUrf('])
assert execute.count('getBackflowVelocityDirectionOption().setSelected(')==1 and 'k>=100&&' in execute and 'k<=250' in execute
macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
(h/'audit/pressure_trial_to_top_direction.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='C0URANSPressureUrf01.java',tofile=macro.name)),encoding='utf8')
backup=h/'runs/controller_snapshots'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
for f in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/f,backup/f)
for file,needle,replacement in [('night_native.py','allowed={',"allowed={'"+macro.name+"':8,"),('night_queue.py','ALLOWED={',"ALLOWED={'"+macro.name+"',"),('night_dashboard.py','case={',"case={'"+macro.name+"':'C0 — kontrola kierunku przepływu na górnej granicy',")]:
 p=h/'tools'/file;t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace(needle,replacement,1)
 if file=='night_queue.py':t=t.replace('prefix={',"prefix={'"+macro.name+"':'"+prefix+"',",1)
 p.write_text(t,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'NIGHT_QUEUE.json';cfg=read(p);job=dict(id='c0_top_backflow_extrapolated',macro=macro.name,input=str(source),initial_time_s=.45,angle_deg=0,approved=True,purpose=desc,runtime_guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_turbulent_viscosity_ratio=99999,maximum_overset_error_cells=0))
assert not cfg['scientific_gates']['C0_bias_explained_and_approved'];assert not any(j['id']==job['id'] for j in cfg['jobs'])
cfg['jobs'].append(job);cfg['controller_exit_requested']=True;tmp=p.with_suffix('.work_tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(p)
event=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_top_boundary_direction_diagnostic_prepared',job=job,source_sha256=digest,macro_sha256=hashlib.sha256(s.encode('utf8')).hexdigest(),source_time_s=.45,source_native_iteration=7560,scientific_approved=False,matched_baseline_update_required=True)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(event)+'\n')
print(json.dumps(event,indent=2))
