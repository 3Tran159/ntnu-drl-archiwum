from pathlib import Path
import subprocess
h=Path(__file__).resolve().parents[1];p=h/'tools/prepare_distance_diagnostic.py';s=p.read_text(encoding='utf8')
old='Files.writeString(out.resolve("forces_"+label+".txt"),force.toString());'
new=r'''Files.writeString(out.resolve("forces_"+label+".txt"),force.toString());
StringBuilder res=new StringBuilder("time="+s.getSolution().getPhysicalTime()+"\n");
for(Monitor mon:s.getMonitorManager().getObjects())if(mon instanceof ResidualMonitor){ResidualMonitor rm=(ResidualMonitor)mon;res.append(rm.getPresentationName()+" enabled="+rm.getEnabled()+" normalized="+rm.isNormalized()+" normalization="+rm.getNormalizationType().getClass().getSimpleName()+" factor="+rm.getNormalizationType().getNormalizationFactor()+" auto_index="+rm.getAutoNormalizeIndex()+"\n");rm.export(out.resolve("residual_"+label+"_"+rm.getPresentationName().replaceAll("[^A-Za-z0-9_-]","_")+".csv").toString());}
Files.writeString(out.resolve("residual_normalization_"+label+".txt"),res.toString());'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s,encoding='utf8')
r=subprocess.run([r'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
print(r.stdout);assert r.returncode==0,r.stderr
