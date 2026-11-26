from pathlib import Path
import subprocess
h=Path(__file__).resolve().parents[1];p=h/'tools/prepare_distance_diagnostic.py';s=p.read_text(encoding='utf8')
needle="target=h/'macros/C0DistanceInterpolationTest.java'"
line='s=s.replace(\'s.getSolution().clearSolutionWithoutMeshReset();initializedHere=true;\',\'throw new IllegalStateException("Original-profile branch prohibited in C0 diagnostic");\')'
assert needle in s;s=s.replace(needle,line+'\n'+needle);p.write_text(s,encoding='utf8')
r=subprocess.run([r'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);print(r.stdout);assert r.returncode==0,r.stderr
target=(h/'macros/C0DistanceInterpolationTest.java').read_text(encoding='utf8')
assert all(x not in target for x in ['initializeSolution();','clearSolution(','clearSolutionWithoutMeshReset();'])
print('Verified no reset/initialization calls; saved fields/time must match source history before any change or solve.')
