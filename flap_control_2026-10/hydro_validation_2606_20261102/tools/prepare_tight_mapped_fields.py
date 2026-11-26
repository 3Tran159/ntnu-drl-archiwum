from pathlib import Path
import json,datetime,subprocess,shutil,py_compile,hashlib
h=Path(__file__).resolve().parents[1]
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));assert not state.get('active')
meta=json.loads((h/'initialization/c0_tight_from_flux1850/mapping_source.json').read_text(encoding='utf8'))
assert meta['source_native_iteration']==1850 and meta['rows']==372961
assert hashlib.file_digest(Path(meta['table']).open('rb'),'sha256').hexdigest()==meta['table_sha256']
s=(h/'macros/FreshC0TightInit.java').read_text(encoding='utf8').replace('class FreshC0TightInit','class PrepareC0TightMappedFields').replace('c0_tight_firstorder_','c0_tight_mapped_')
helper=r'''
void mappedScalar(ScalarProfile profile,Table table,String column){profile.setMethod(XyzTabularScalarProfileMethod.class);XyzTabularScalarProfileMethod method=profile.getMethod(XyzTabularScalarProfileMethod.class);method.setTable(table);method.setData(column);method.setCoordinateSystem(s.getCoordinateSystemManager().getLabCoordinateSystem());}
void installWarmFields(PhysicsContinuum pc)throws Exception{
Path tablePath=root.resolve("initialization/c0_tight_from_flux1850/warm_fields.csv");
java.security.MessageDigest digest=java.security.MessageDigest.getInstance("SHA-256");try(InputStream stream=Files.newInputStream(tablePath)){byte[] b=new byte[1048576];int n;while((n=stream.read(b))!=-1)digest.update(b,0,n);}
if(!java.util.HexFormat.of().formatHex(digest.digest()).equals("0ea7c187f92634a10e57a30ad0b9f0a7c1ff96fb6133850d102a24ccecf621cd"))throw new IllegalStateException("Warm table fingerprint mismatch");
Table table=s.getTableManager().createFromFile(tablePath.toString());table.setPresentationName("C0 retained iteration1850 initial fields");
VelocityProfile velocity=pc.getInitialConditions().get(VelocityProfile.class);velocity.setMethod(XyzTabularVectorProfileMethod.class);XyzTabularVectorProfileMethod method=velocity.getMethod(XyzTabularVectorProfileMethod.class);method.setTable(table);method.setXData("ux");method.setYData("uy");method.setZData("uz");method.setCoordinateSystem(s.getCoordinateSystemManager().getLabCoordinateSystem());
mappedScalar(pc.getInitialConditions().get(InitialPressureProfile.class),table,"pressure");
pc.getInitialConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.K_OMEGA);
mappedScalar(pc.getInitialConditions().get(TurbulentKineticEnergyProfile.class),table,"k");
mappedScalar(pc.getInitialConditions().get(SpecificDissipationRateProfile.class),table,"omega");
Files.copy(root.resolve("initialization/c0_tight_from_flux1850/mapping_source.json"),out.resolve("mapping_source.json"));
}
'''
s=s.replace('public void execute()',helper+'\npublic void execute()',1)
needle='s.getSolution().initializeSolution();';assert s.count(needle)==1
s=s.replace(needle,'''installWarmFields(pc);
if(s.getSimulationIterator().getCurrentIteration()!=0||Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Never clear a progressed checkpoint");
s.getSolution().clearSolution(Solution.Clear.History,Solution.Clear.Fields,Solution.Clear.Mesh);s.getSolution().initializeSolution();''')
i=s.index('Files.writeString(out.resolve("numerical_change.txt"),');j=s.index('\n',i)
description='Zero-PDE-step mapping audit: new tight-cage333939-cell mesh initialized from retained iteration1850 healthy first-order fields. Native supported XYZ-table restart maps piezometric pressure,velocity,k,omega; no clipping/rescaling. Mesh/physical geometry/BCs remain unchanged. Target native counter0/time0 because this is a new-mesh initializer; source history and original checkpoint1850 remain intact. CI disabled,flow/SST firstorder,flux correction,DISTANCE,URF.3/.1. Full mesh and true active-volume containment audited; initial pressure/mass/turbulence gate must pass before saving candidate. Work reviews native mapped fields before any PDE steps. Installed2606 guide GUID-E7FF479A-2CDC-43B6-AC75-34C44E761591.'
s=s[:i]+'Files.writeString(out.resolve("numerical_change.txt"),"'+description+'");'+s[j:]
start=s.index('UserFieldFunction omegaFloor=')
catch=s[s.rindex('}catch(Exception e){try{Files.writeString(out.resolve("initialization_error.txt")'):]
finish=r'''
double pmin=Double.POSITIVE_INFINITY;for(String zone:zones)pmin=Math.min(pmin,rv("HF_pabs_"+zone));
MaxReport speed=s.getReportManager().createReport(MaxReport.class);speed.getParts().setObjects(regions);speed.setFieldFunction(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());
MaxReport visc=s.getReportManager().createReport(MaxReport.class);visc.getParts().setObjects(regions);visc.setFieldFunction(s.getFieldFunctionManager().getFunction("TurbulentViscosityRatio"));
MinReport kval=minimum("Mapped k minimum","TurbulentKineticEnergy",regions,false),omega=minimum("Mapped omega minimum","SpecificDissipationRate",regions,false);
double umax=speed.getReportMonitorValue(),viscmax=visc.getReportMonitorValue(),kmin=kval.getReportMonitorValue(),omin=omega.getReportMonitorValue(),balance=Math.abs(mass.getReportMonitorValue())/10800.;
Files.writeString(out.resolve("mapped_initial_metrics.json"),"{\"pabs_min_Pa\":"+pmin+",\"max_speed_m_s\":"+umax+",\"max_turbulent_viscosity_ratio\":"+viscmax+",\"k_min\":"+kmin+",\"omega_min\":"+omin+",\"mass_imbalance_relative\":"+balance+",\"native_iteration\":"+s.getSimulationIterator().getCurrentIteration()+",\"physical_time_s\":"+s.getSolution().getPhysicalTime()+",\"source_iteration\":1850}");
if(!Double.isFinite(pmin+umax+viscmax+kmin+omin+balance)||pmin<=12339.214766776897||umax>25||umax<18||viscmax>=99999||kmin<=1.0001e-10||omin<=1.0001e-10||balance>=1e-4)throw new IllegalStateException("Mapped initial field safety gate failed");
if(s.getSimulationIterator().getCurrentIteration()!=0||Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Mapping unexpectedly advanced the solution");
s.saveState(out.resolve("warm_mapped_candidate.sim").toString());
Files.writeString(out.resolve("status.json"),"{\"status\":\"mesh_connectivity_prepared\",\"cells\":333939,\"solver_steps\":0,\"saved_time_s\":0,\"native_iteration\":0,\"mapped_source_iteration\":1850,\"mapping_audit_only\":true,\"scientific_approved\":false,\"training_approved\":false}");
note("WARM_FIELDS_MAPPED_ZERO_PDE_STEPS — Work review required before flow");
'''
s=s[:start]+finish+catch
macro=h/'macros/PrepareC0TightMappedFields.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':1,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_tight_mapped_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — przeniesienie zachowanego rozwiązania, bez iteracji przepływu',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_tight_mapped_field_audit',macro=macro.name,input=str(h/'cases/SP_C_split0_overset/c0_tight_cage_v2_20261103_025110/SP_C_mesh_ready.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose=description)
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg['release_failure_hold']['c0_tight_continuity_initialization']='Native CI100 executed but initial pressure was already unphysical before first10PDE iterations. Failed result rejected. Next action only maps preserved healthy1850 fields onto zero-step target, no PDE steps.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
marker=h.parent/'STOP_OWNED_CFD.json';archived=None
if marker.exists():
 m=json.loads(marker.read_text(encoding='utf8'));assert m['source']=='night_queue' and m['reason']=='scientific_runtime_gate' and m['target_job']=='c0_tight_continuity_initialization'
 dest=h/'audit'/('STOP_rejected_CI_before_mapping_'+stamp+'.json');assert marker.resolve()==h.parent.resolve()/'STOP_OWNED_CFD.json' and dest.resolve().is_relative_to((h/'audit').resolve()) and not dest.exists();marker.rename(dest);archived=str(dest)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_mapped_field_preparation',job=job,archived_reviewed_marker=archived,source_checkpoint=meta['source_checkpoint'],source_sha256=meta['source_checkpoint_sha256'],table_sha256=meta['table_sha256'],scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v.update(at=ev['at'],obstacle='Obie próby startu na nowej siatce odrzucono. CI100 rzeczywiście wykonano,ale pabs było ujemne już po inicjalizacji; po10 iteracjach pabs−2,218MPa,Umax110,4m/s przy krawędzi natarcia. Zero błędów Overset,zero ograniczania k/omega. Nie powtarzam takiego rozruchu.',next='Przeniesienie zachowanych zdrowych numerycznie pól z iteracji1850 na nową siatkę przez natywną tabelę XYZ.1CPU,zero iteracji przepływu. Kontrola ciśnienia,prędkości,k/omega,masy,geometrii i pełnej łączności przed uruchomieniem solvera.')
p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(ev,indent=2))
