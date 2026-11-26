from pathlib import Path
import subprocess
h=Path(__file__).resolve().parents[1];p=h/'macros/InspectHydroComparison.java';s=p.read_text(encoding='utf8')
old='for(Solver solver:s.getSolverManager().getObjects())b.append("solver="+solver.getPresentationName()+" class="+solver.getClass().getName()+" frozen="+solver.getFrozen()+"\\n");'
new='for(Solver solver:s.getSolverManager().getObjects()){String cn=solver.getClass().getName();b.append("solver="+solver.getPresentationName()+" class="+cn);if(cn.toLowerCase(Locale.ROOT).contains("turb")||cn.contains("SegregatedFlowSolver"))try{b.append(" frozen="+solver.getFrozen());}catch(Exception e){b.append(" UNREAD_FROZEN_STATE="+e);}b.append("\\n");}'
assert old in s;s=s.replace(old,new)
old='b.append("  option="+condition.getClass().getSimpleName()+" selected="+((EnumeratedOption)condition).getSelected()+"\\n");'
new='try{b.append("  option="+condition.getClass().getSimpleName()+" selected="+((EnumeratedOption)condition).getSelected()+"\\n");}catch(Exception e){b.append("  UNREAD_BOUNDARY_OPTION="+condition.getClass().getSimpleName()+" "+e+"\\n");}'
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
print('Compiled; unavailable optional properties are explicitly marked, never fabricated or interpreted as a pass.')
