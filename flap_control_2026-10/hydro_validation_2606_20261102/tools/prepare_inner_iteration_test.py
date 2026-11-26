from pathlib import Path
import json,os,datetime,subprocess,py_compile
h=Path(__file__).resolve().parents[1]
audit=json.loads((h/'validation/BC_native_diagnosis.json').read_text(encoding='utf8'))
assert sum(x['rows'] for x in audit['full_overset'].values())==361532
assert all(x['finite_status_verified'] and set(x['Overset Error Status'])=={'0'} for x in audit['full_overset'].values())
p=h/'macros/ResumeC0Qualified.java';s=p.read_text(encoding='utf8')
s=s.replace('class ResumeC0Qualified','class C0InnerIterationTest').replace('c0_resume_','c0_inner40_')
s=s.replace('int window=25,minSteps=100,maxSteps=500;','for(SolverStoppingCriterion crit:s.getSolverStoppingCriterionManager().getObjects())if(crit instanceof InnerIterationStoppingCriterion){crit.setIsUsed(true);((InnerIterationStoppingCriterion)crit).setMaximumNumberInnerIterations(40);}\nint window=25,minSteps=100,maxSteps=150;')
s=s.replace('maximum 1 s','maximum 0.3 s').replace('maximum 1 s','maximum 0.3 s')
s=s.replace('URANS force stabilization: dt=0.002 s; minimum 0.2 s, maximum 0.3 s;', 'Diagnostic inner iterations 15 to 40 only: dt=0.002 s; minimum 0.2 s, maximum 0.3 s;')
a=s.index('ElementCountReport oversetErrors=null');b=s.index('for(int k=1;',a)
s=s[:a]+'''ElementCountReport oversetErrors=count("C0 active error diagnostic "+runId,namedField("Overset Error Status","OversetErrorStatus"),.5,100,s.getRepresentationManager().getObject("Volume Mesh"));
ElementCountReport oversetFallback=count("C0 active fallback diagnostic "+runId,namedField("Overset Interpolation Type","OversetInterpolationType"),3.5,6.5,s.getRepresentationManager().getObject("Volume Mesh"));
for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface in=(IndirectRegionInterface)iface;if(in.getTreatErrorAsWarning()||!in.getConditions().get(OversetHoleCuttingOptions.class).getBoolean("ZeroDonorCheckOption"))throw new IllegalStateException("Native strict connectivity checks must remain enabled");}
auditFull("before_resume",cells);
''' +s[b:]
a=s.index('if(k==1){',s.index('for(int k=1;'));b=s.index('if(k<=2)captureFields',a)
s=s[:a]+'if(k==1)auditFull("after_first_step",cells);\n'+s[b:]
s=s.replace('XyzInternalTable pt=s.getTableManager()', 'auditFull("final",cells);\nXyzInternalTable pt=s.getTableManager()')
helper='''void auditFull(String label,long expected)throws Exception{
Representation full=s.getRepresentationManager().getObject("Overset Mesh");long total=0,active=0,inactive=0,acceptor=0,errors=0,fallback=0;double minV=Double.POSITIVE_INFINITY,minQ=Double.POSITIVE_INFINITY,maxRatio=0;Map<Integer,Long> methods=new TreeMap<>();
for(Region r:regions){PlaneSection plane=s.getPartManager().createImplicitPart(List.of(r),List.of(0.,1.,0.),List.of(0.,.02,0.),0,1,new DoubleVector(new double[]{0}));
XyzInternalTable t=s.getTableManager().createTable(XyzInternalTable.class);t.getParts().setObjects(plane);t.setRepresentation(full);t.setExtractVertexData(false);t.setFieldFunctions(List.of(namedField("Overset Cell Status","OversetCellStatus"),namedField("Overset Error Status","OversetErrorStatus"),namedField("Overset Interpolation Type","OversetInterpolationType"),namedField("Overset Interpolation Cell Size Ratio","Overset Interpolation Cell Size Ratio"),s.getFieldFunctionManager().getFunction("Volume"),s.getFieldFunctionManager().getFunction("CellQuality")));t.extract();Path file=out.resolve(r.getPresentationName()+"_"+label+"_full_plane.csv");t.export(file.toString());
try(BufferedReader reader=Files.newBufferedReader(file)){String line=reader.readLine();if(line==null||!line.startsWith("\\\"Overset Cell Status\\\""))throw new IllegalStateException("Unexpected full-plane export schema");while((line=reader.readLine())!=null){if(line.isBlank())continue;String[] a=line.split(",");double status=Double.parseDouble(a[0]),error=Double.parseDouble(a[1]),method=Double.parseDouble(a[2]),ratio=Double.parseDouble(a[3]),v=Double.parseDouble(a[4]),q=Double.parseDouble(a[5]);if(!Double.isFinite(status+error+method+ratio+v+q)||Math.abs(status)>2.001||error<0||error>100||method < -2||method>7||v<=0||v>1||q<=0||q>1.001)throw new IllegalStateException("Invalid full-plane diagnostic values");total++;minV=Math.min(minV,v);minQ=Math.min(minQ,q);if(status==0)active++;else if(status==1)inactive++;else if(status==-2||status==-1){acceptor++;if(ratio<=0)throw new IllegalStateException("Invalid acceptor size ratio");maxRatio=Math.max(maxRatio,ratio);methods.merge((int)method,1L,Long::sum);}else throw new IllegalStateException("Invalid cell status");if(error>0)errors++;if(method>=4&&method<=6)fallback++;}}
}
String msg="time="+s.getSolution().getPhysicalTime()+" total="+total+" active="+active+" inactive="+inactive+" acceptors="+acceptor+" errors="+errors+" difficult_interpolation="+fallback+" min_volume="+minV+" min_quality="+minQ+" max_acceptor_size_ratio="+maxRatio+" methods="+methods+"\\n";
Files.writeString(out.resolve("full_audit_"+label+".txt"),msg);s.println("FULL_OVERSET_AUDIT "+msg);
if(total!=expected||active<1||acceptor<1||errors!=0||fallback!=0)throw new IllegalStateException("Complete Overset connectivity check failed");
}
'''
s=s.replace('public void execute(){',helper+'public void execute(){')
target=h/'macros/C0InnerIterationTest.java';target.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(target)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
lp=h/'tools/night_native.py';a=lp.read_text(encoding='utf8').replace("'InspectHydroComparison.java':1}","'InspectHydroComparison.java':1,'C0InnerIterationTest.java':8}");lp.write_text(a,encoding='utf8');py_compile.compile(str(lp),doraise=True)
qp=h/'tools/night_queue.py';a=qp.read_text(encoding='utf8').replace("'ResumeC0Qualified.java'}","'ResumeC0Qualified.java','C0InnerIterationTest.java'}")
a=a.replace("return H/'cases/SP_C_split0_overset'/('c0_resume_'+receipt['run_id'])","return H/'cases/SP_C_split0_overset'/(('c0_inner40_' if receipt['macro']=='C0InnerIterationTest.java' else 'c0_resume_')+receipt['run_id'])")
qp.write_text(a,encoding='utf8');py_compile.compile(str(qp),doraise=True)
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));cfg['controller_exit_requested']=True
cfg['jobs'].append(dict(id='c0_inner40_sensitivity',macro='C0InnerIterationTest.java',input=str(h/'cases/SP_C_split0_overset/c0_resume_20261102_221053/error_checkpoint.sim'),approved=True,initial_time_s=.3024,angle_deg=0,purpose='Isolate inner-iteration convergence: 15 to 40 iterations only, dt .002, same 361532 mesh, no physics changes; 100-150 steps; scientific hold remains.'))
cfg['technical_connectivity_audit']=dict(passed=True,all_cells=361532,error_cells=0,source=str(h/'validation/BC_native_diagnosis.json'),max_native_size_ratio=9.211892538332323,accuracy_approved=False)
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_approved_bounded_diagnostic',job='c0_inner40_sensitivity',technical_connectivity=cfg['technical_connectivity_audit'],scientific_gate=False))+'\n')
print('C0 inner-iteration diagnostic compiled; queue update requests graceful controller reload. STAR source remains unchanged.')
