from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
s=(R/'ContinueForces.java').read_text()
s=s.replace('class ContinueForces','class ContinueUntilSettled')
s=s.replace('private double dt,target,startTime; private int inner;','private double dt,target,startTime; private int inner;\n  private ArrayList<double[]> samples=new ArrayList<>();private int consecutivePasses=0;')
s=s.replace('double expectedStart=Double.parseDouble(System.getenv("NTNU_STAB_START"));','double expectedStart=Double.parseDouble(System.getenv("NTNU_STAB_START"));\n      boolean initialize="true".equals(System.getenv("NTNU_STAB_INIT"));')
needle='ImplicitUnsteadySolver unsteady=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);'
initial='''if(initialize){
        if(Math.abs(expectedStart)>1e-10)throw new IllegalStateException("Initialization allowed only for new M04 at t=0");
        calm.getCurrent().setComponents(18,0,0);calm.getWind().setComponents(18,0,0);
        VolumeFractionProfile in=fluid.getBoundaryManager().getBoundary("DOMAIN.inlet").getValues().get(VolumeFractionProfile.class);
        FieldFunction water=in.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction();
        VolumeFractionProfile back=fluid.getBoundaryManager().getBoundary("DOMAIN.outlet").getValues().get(VolumeFractionProfile.class);
        back.setMethod(CompositeNMinus1ArrayProfileMethod.class);back.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).setMethod(FunctionScalarProfileMethod.class);
        back.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(water);
        s.getSolution().clearSolutionWithoutMeshReset();s.getSolution().initializeSolution();
        if(fv.getCellCount()!=expectedCells)throw new IllegalStateException("Mesh changed on initialization");
      }
      '''
s=s.replace(needle,initial+needle)
s=s.replace('Math.abs(d)>2000||Math.abs(l)>20000','(t>.02&&Math.abs(d)>2000)||Math.abs(d)>20000||Math.abs(l)>20000')
s=s.replace('if(steps%100==0) {','''samples.add(new double[]{t,d/q,l/q});
          if(samples.size()>2000)samples.remove(0);
          if(steps%500==0) {''')
needle='''        }
      }
      for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof PhysicalTimeStoppingCriterion)'''
s=s.replace(needle,'''          if(steps%Math.max(1,(int)Math.round(.2/dt))==0&&t>=1.0-dt*.1){
            boolean pass=settlingPass();consecutivePasses=pass?consecutivePasses+1:0;
            if(consecutivePasses>=2){state="stabilized";break;}
          }
        }
      }
      for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof PhysicalTimeStoppingCriterion)''')
s=s.replace('exportFields(vf);','''exportFields(vf);
      XyzInternalTable vectors=s.getTableManager().createTable(XyzInternalTable.class);vectors.getParts().setObjects(fluid);vectors.setRepresentation(fv);vectors.setExtractVertexData(false);
      FieldFunction vel=s.getFieldFunctionManager().getFunction("Velocity");
      vectors.setFieldFunctions(List.of(vel.getComponentFunction(0),vel.getComponentFunction(1),vel.getComponentFunction(2),s.getFieldFunctionManager().getFunction("Pressure"),vf,s.getFieldFunctionManager().getFunction("CourantNumber")));
      vectors.extract();vectors.export(out.resolve("velocity_vectors.csv").toString());
      Files.writeString(out.resolve("EXPORT_OK.json"),json(Map.of("time_s",s.getSolution().getPhysicalTime(),"cells",fv.getCellCount(),"status",state)));''')
method='''  private boolean settlingPass()throws Exception{
    int n=(int)Math.round(.2/dt);
    if(samples.size()<2*n)return false;
    int end=samples.size();Map<String,Object> check=new LinkedHashMap<>();boolean pass=true;
    for(int col=1;col<=2;col++){
      double first=0,last=0,rms=0;
      for(int k=end-2*n;k<end-n;k++)first+=samples.get(k)[col]/n;
      for(int k=end-n;k<end;k++)last+=samples.get(k)[col]/n;
      for(int k=end-n;k<end;k++)rms+=Math.pow(samples.get(k)[col]-last,2)/n;
      double shift=100*(last-first)/Math.abs(first),relrms=100*Math.sqrt(rms)/Math.abs(last);
      double drift=100*(samples.get(end-1)[col]-samples.get(end-n)[col])/Math.abs(last);
      boolean ok=Double.isFinite(shift)&&Double.isFinite(relrms)&&Double.isFinite(drift)&&Math.abs(shift)<.5&&relrms<1&&Math.abs(drift)<1;
      pass&=ok;check.put(col==1?"CD":"CL_total",Map.of("previous_mean",first,"latest_mean",last,"mean_change_pct",shift,"rms_pct",relrms,"drift_pct",drift,"pass",ok));
    }
    check.put("time_s",samples.get(end-1)[0]);check.put("pass",pass);check.put("consecutive_passes",pass?consecutivePasses+1:0);
    check.put("criterion","Two non-overlapping 0.2 s windows; |mean change|<0.5%, RMS<1%, endpoint drift<1%; require two consecutive passing evaluations spaced 0.2 s. Force-settling screen, not mesh or time-step validation.");
    Files.writeString(out.resolve("settling_check.json"),json(check));return pass;
  }
'''
s=s.replace('  private ForceReport force(',method+'  private ForceReport force(')
(R/'ContinueUntilSettled.java').write_text(s)
base=(R/'run_queue.py').read_text().split('def main():')[0]
base=base.replace("out=ROOT/j['id'];out.mkdir(exist_ok=False)","""out=ROOT/j['id']
    storage=Path('E:/ntnu/mesh_stabilization_20261029')/j['id']
    storage.parent.mkdir(parents=True,exist_ok=True)
    storage.mkdir(exist_ok=False)
    if out.exists():raise RuntimeError('Output already exists')
    cmd="New-Item -ItemType Junction -Path '"+str(out)+"' -Target '"+str(storage)+"' | Out-Null"
    subprocess.run(['powershell','-NoProfile','-Command',cmd],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    write(out/'storage.json',{'physical_directory':str(storage),'dashboard_link':str(out)})""")
base=base.replace("if not source.is_relative_to(BASE):","if not (source.is_relative_to(BASE) or source.is_relative_to(Path('E:/ntnu/mesh_stabilization_20261029'))):")
base=base.replace('shutil.disk_usage(ROOT)','shutil.disk_usage(out)')
base=base.replace('ContinueForces.java','ContinueUntilSettled.java')
base=base.replace("'BUDGET':j['wall_budget_s']","'BUDGET':j['wall_budget_s'],'INIT':str(j.get('initialize',False)).lower()")
base=base.replace("completed.get('status')=='target_reached'","completed.get('status')=='stabilized'")
(R/'run_until_settled.py').write_text(base)
print('Settling-controlled macro and resource-protected controller prepared.')
