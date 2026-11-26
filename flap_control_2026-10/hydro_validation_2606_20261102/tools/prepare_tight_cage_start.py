from pathlib import Path
import sys,json,hashlib,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve()
assert run.is_relative_to(h/'cases/SP_C_split0_overset')
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));assert not state.get('active')
review=json.loads((run/'work_tight_cage_review.json').read_text(encoding='utf8'));assert review['technical_screen_pass']
mesh=json.loads((run/'status.json').read_text(encoding='utf8'));assert mesh['solver_steps']==0
source=run/'SP_C_mesh_ready.sim';cells=mesh['cells'];cache=state['checkpoint_integrity'][str(source)]
digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
assert cache['native_save_complete'] and cache['sha256']==digest and source.stat().st_size==cache['bytes']
s=(h/'macros/FreshC0RelaxedInit.java').read_text(encoding='utf8')
s=s.replace('class FreshC0RelaxedInit','class FreshC0TightInit').replace('c0_relaxed_init_','c0_tight_firstorder_')
s=s.replace('cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim',source.relative_to(h).as_posix()).replace('35b44cb5cd54d35cf7e7b849140524b9f2be5d4ffc8b583da44495db5ba88865',digest).replace('579468',str(cells))
s=s.replace('Files.createDirectories(out);guard();','if(Files.exists(out))throw new IllegalStateException("Unique output required");Files.createDirectories(out);guard();if(s.getSimulationIterator().getCurrentIteration()!=0)throw new IllegalStateException("Only zero-step mesh source allowed; never reset resolved flow");',1)
s=s.replace('OversetConservationOption.Type.NONE','OversetConservationOption.Type.FLUX_CORRECTION')
s=s.replace('flow.setContinuityInitialization(true);','flow.setContinuityInitialization(false);')
needle='s.getSolution().initializeSolution();';assert s.count(needle)==1
s=s.replace(needle,'''pc.getModelManager().getModel(SegregatedFlowModel.class).getUpwindOption().setSelected(FlowUpwindOption.Type.FIRST_ORDER);
pc.getModelManager().getModel(SstKwTurbModel.class).getUpwindOption().setSelected(UpwindOption.Type.FIRST_ORDER);
'''+needle)
start=s.index('Files.writeString(out.resolve("numerical_change.txt"),');end=s.index('\n',start)
description=f'Technical numerical startup on new tight-cage mesh ({cells} cells), not a resume of the retained1850-iteration solution. Physical geometry and boundary conditions unchanged; background cell coordinates/volumes verified identical. Flow and SST FIRST_ORDER, DISTANCE, FLUX_CORRECTION, velocity/pressureURF0.3/0.1, continuity preinitialization disabled. Source nativeiteration0 only. True active volume-cell containment checked before first PDE step. Strict pressure12339.2148Pa,mass1e-4,zero turbulence floor/overset error gates from first block. No hydrodynamic approval until matched second-order URANS comparisons.'
s=s[:start]+'Files.writeString(out.resolve("numerical_change.txt"),"'+description+'");'+s[end:]
needle='if(!Double.isFinite(oe+omega+kfloor+visc)||oe>0)throw new IllegalStateException("Overset or field diagnostic invalid");';assert needle in s
s=s.replace(needle,needle+'\nif(p<=12339.214766776897||bal>=1e-4||omega>0||kfloor>0||visc>=99999)throw new IllegalStateException("Strict pressure/mass/turbulence gate violated");')
helper=r'''
List<double[]> nativePolygon(Path p)throws Exception{List<double[]> a=new ArrayList<>();try(BufferedReader r=Files.newBufferedReader(p)){String line=r.readLine();if(!"x_m,z_m".equals(line))throw new IllegalStateException("Unexpected native contour schema");while((line=r.readLine())!=null){String[] q=line.split(",");a.add(new double[]{Double.parseDouble(q[0]),Double.parseDouble(q[1])});}}if(a.size()<100)throw new IllegalStateException("Native contour incomplete");return a;}
boolean insideSolid(double x,double z,List<double[]> poly){
double xmin=Double.POSITIVE_INFINITY,xmax=-xmin,zmin=xmin,zmax=-xmin;for(double[] v:poly){xmin=Math.min(xmin,v[0]);xmax=Math.max(xmax,v[0]);zmin=Math.min(zmin,v[1]);zmax=Math.max(zmax,v[1]);}
if(x<xmin||x>xmax||z<zmin||z>zmax)return false;
boolean inside=false;double dist2=Double.POSITIVE_INFINITY;
for(int i=0,j=poly.size()-1;i<poly.size();j=i++){
 double[] a=poly.get(i),b=poly.get(j);
 if((a[1]>z)!=(b[1]>z)&&x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])inside=!inside;
 double dx=b[0]-a[0],dz=b[1]-a[1],len=dx*dx+dz*dz;if(len>0){double t=Math.max(0,Math.min(1,((x-a[0])*dx+(z-a[1])*dz)/len));double ex=x-a[0]-t*dx,ez=z-a[1]-t*dz;dist2=Math.min(dist2,ex*ex+ez*ez);}
}return inside&&dist2>1e-18;
}
void verifyInitialVolumeContainment(Path base)throws Exception{
List<double[]> main=nativePolygon(base.resolve("main_native_polygon.csv")),flapPoly=nativePolygon(base.resolve("flap_native_polygon.csv"));long active=0,inside=0;
for(String name:List.of("main","flap"))Files.copy(base.resolve(name+"_native_polygon.csv"),out.resolve(name+"_native_polygon.csv"));
for(Region region:regions)try(BufferedReader r=Files.newBufferedReader(out.resolve(region.getPresentationName()+"_fresh_initialized_volume.csv"))){
 String[] headers=r.readLine().split(",");Map<String,Integer> col=new HashMap<>();for(int i=0;i<headers.length;i++)col.put(headers[i].replace("\"","").strip(),i);
 for(String req:List.of("X (m)","Z (m)","Overset Cell Status"))if(!col.containsKey(req))throw new IllegalStateException("Missing volume export column "+req);
 String line;while((line=r.readLine())!=null){if(line.isBlank())continue;String[] a=line.split(",");double state=Double.parseDouble(a[col.get("Overset Cell Status")]);if(state!=0)continue;active++;double x=Double.parseDouble(a[col.get("X (m)")]),z=Double.parseDouble(a[col.get("Z (m)")]);if(!Double.isFinite(x+z))throw new IllegalStateException("Invalid active volume centroid");if(insideSolid(x,z,main)||insideSolid(x,z,flapPoly))inside++;}
}
Files.writeString(out.resolve("initial_native_volume_containment.json"),"{\"active_centers\":"+active+",\"inside_solids_over_1nm\":"+inside+",\"native_iteration\":"+s.getSimulationIterator().getCurrentIteration()+",\"physical_time_s\":"+s.getSolution().getPhysicalTime()+"}");
if(active<1||inside!=0||s.getSimulationIterator().getCurrentIteration()!=0||Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Initial native active-volume geometry guard failed");
}
'''
# Avoid a per-point repeated bounding-box loop in large far-field grids.
helper=helper.replace('List<double[]> nativePolygon','List<double[]> nativePolygon') 
s=s.replace('public void execute()',helper+'\npublic void execute()',1)
needle='captureComparison("fresh_initialized");';assert s.count(needle)==1
s=s.replace(needle,needle+'verifyInitialVolumeContainment(base);')
s=s.replace('max_absolute_pressure_Pa\\n','max_absolute_pressure_Pa,native_iteration\\n').replace('"," +umax','"," +umax')
needle='","+umax+","+pmax+"\\n"';assert needle in s;s=s.replace(needle,'","+umax+","+pmax+","+s.getSimulationIterator().getCurrentIteration()+"\\n"')
macro=h/'macros/FreshC0TightInit.java';assert not macro.exists() or macro.read_text(encoding='utf8')==s;macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':8,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_tight_firstorder_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — rozruch na siatce ograniczonej do klapki, pierwszy rząd',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_turbulent_viscosity_ratio=99999,maximum_overset_error_cells=0)
job=dict(id='c0_tight_firstorder_initialization',macro=macro.name,input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose=description,runtime_guards=guards)
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_tight_cage_firstorder_diagnostic',job=job,input_sha256=digest,cells=cells,scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
print(json.dumps(ev,indent=2))
