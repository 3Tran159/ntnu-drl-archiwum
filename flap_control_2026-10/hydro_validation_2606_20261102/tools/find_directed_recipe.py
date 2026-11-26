from pathlib import Path
roots=[Path('C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/mesh_study_20261030'),Path('E:/ntnu_mesh_optimization_20261030/M13_farfield15_20261031'),Path('F:/ntnu/mesh_screening_20261028')]
count=0
for root in roots:
 for file in root.rglob('*'):
  if not file.is_file() or file.suffix not in ('.java','.py') or file.stat().st_size>300000:continue
  if any(s in str(file) for s in ['site-packages','node_modules','.deps','__pycache__']):continue
  text=file.read_text(encoding='utf8',errors='replace')
  if 'createDirectedMeshOperation' in text:
   at=text.index('createDirectedMeshOperation')
   print('SOURCE',file);print(text[max(0,at-500):at+4500]);count+=1
   if count>=5:raise SystemExit
print('MATCHES',count)
