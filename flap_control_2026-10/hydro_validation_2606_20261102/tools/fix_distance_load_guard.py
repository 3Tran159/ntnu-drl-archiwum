from pathlib import Path
import subprocess
h=Path(__file__).resolve().parents[1];p=h/'tools/prepare_distance_diagnostic.py';s=p.read_text(encoding='utf8')
old='if(!s.getSolution().isInitialized())throw new IllegalStateException("Saved control solution must be initialized; no reset allowed");'
assert s.count(old)==1;s=s.replace(old,'verifySavedControl(caseDir);')
method=r"""
void verifySavedControl(Path source)throws Exception{
double time=s.getSolution().getPhysicalTime();boolean flag0=s.getSolution().isInitialized();
List<String> lines=Files.readAllLines(source.resolve("history.csv"));String[] header=lines.get(0).split(",");Map<String,Integer> idx=new HashMap<>();for(int k=0;k<header.length;k++)idx.put(header[k],k);
String[] matched=null;for(int i=1;i<lines.size();i++){String[] row=lines.get(i).split(",");if(Math.abs(Double.parseDouble(row[idx.get("time_s")])-time)<1e-9)matched=row;}if(matched==null)throw new IllegalStateException("Saved physical time absent from source history");
StringBuilder result=new StringBuilder("time="+time+" initialized_before_field_access="+flag0+"\n");
for(String[] pair:new String[][]{{"Fx_N","HF_Fx_N"},{"Fz_N","HF_Fz_N"},{"Mh_Nm","HF_Mh_Nm"},{"CL_hydro","HF_CL_hydro"},{"CD","HF_CD"}}){double expected=Double.parseDouble(matched[idx.get(pair[0])]),actual=rv(pair[1]);result.append(pair[0]+" expected="+expected+" loaded="+actual+"\n");if(!Double.isFinite(actual)||Math.abs(actual-expected)>1e-7*Math.max(1,Math.abs(expected)))throw new IllegalStateException("Saved field verification failed for "+pair[0]);}
result.append("initialized_after_field_access="+s.getSolution().isInitialized()+"\ninitializeSolution_called=false\n");Files.writeString(out.resolve("saved_solution_readback.txt"),result.toString());
captureFields("loaded_control");if(Math.abs(s.getSolution().getPhysicalTime()-time)>1e-12)throw new IllegalStateException("Readback advanced physical time");
}
"""
needle='void captureComparison(String label)throws Exception{'
assert s.count(needle)==1;s=s.replace(needle,method+'\n'+needle)
s=s.replace('s.getSolution().clearSolutionWithoutMeshReset();initializedHere=true;','throw new IllegalStateException("Unreachable original-profile branch prohibited in C0 diagnostic");')
p.write_text(s,encoding='utf8')
r=subprocess.run([r'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);print(r.stdout);assert r.returncode==0,r.stderr
target=(h/'macros/C0DistanceInterpolationTest.java').read_text(encoding='utf8')
assert 'initializeSolution();' not in target and 'clearSolution(' not in target and 'clearSolutionWithoutMeshReset();' not in target
print('Compiled. Uses exact saved-time/force-history readback; no initializeSolution or clearSolution call. Original failed run preserved.')
