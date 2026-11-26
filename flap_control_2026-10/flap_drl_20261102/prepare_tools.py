from pathlib import Path
import subprocess,json,re,datetime
ROOT=Path(__file__).resolve().parent
INSTALL=Path('E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8')
JDK=Path('C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin')
CP=str(INSTALL/'star/lib/java/platform/modules/ext/*')
macro=ROOT/'05_macros/InspectFlapSeed.java'
out=ROOT/'05_macros/compiled';out.mkdir(exist_ok=True)
p=subprocess.run([str(JDK/'javac.exe'),'-cp',CP,'-d',str(out),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
receipt={'ok':p.returncode==0,'messages':p.stdout+p.stderr,'at':datetime.datetime.now().astimezone().isoformat()}
(ROOT/'00_audit/compile_inspector.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('COMPILE',json.dumps(receipt))
assert p.returncode==0
# Use the current licensed configuration without persisting or printing its key.
ps="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'starccm+.exe' -and $_.CommandLine -match ' -batch ' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
q=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=20)
entries=json.loads(q.stdout) if q.stdout.strip() else []
if isinstance(entries,dict):entries=[entries]
active=next((e for e in entries if 'PRE_W04_20261102' in e['CommandLine']),None)
assert active,'Expected active campaign not identified; inspect launch deferred'
args=[str(INSTALL/'star/lib/win64/clang20.1vc14.2-r8/lib/starccm+.exe'),'-power']
for key in ['-podkey','-licpath']:
 m=re.search(re.escape(key)+r'\s+("[^"]+"|\S+)',active['CommandLine'])
 assert m,'Licensing configuration unavailable'
 args.extend([key,m.group(1).strip('"')])
args.extend(['-np','1','-cpubind','off','-batch',str(macro),str(ROOT/'04_cases/calm/FLAP_C00_seed.sim')])
log=ROOT/'00_audit/seed_inspection.star.log'
with log.open('w',encoding='utf8') as f:
 proc=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,cwd=str(ROOT),creationflags=subprocess.CREATE_NO_WINDOW)
receipt={'pid':proc.pid,'at':datetime.datetime.now().astimezone().isoformat(),'mode':'CPU one process; read-only inspection macro; zero time steps; no save','active_campaign_pid_untouched':active['ProcessId'],'log':str(log)}
(ROOT/'00_audit/inspection_launch.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('INSPECTION_LAUNCHED',json.dumps(receipt))
# Targeted API lookup for future exports and motion, no solver.
for cls in ['star.meshing.PartExportManager','star.meshing.PartImportManager','star.meshing.MeshPart','star.motion.RotationMotion','star.common.SimulationIterator','star.flow.ForceAndMomentBaseReport']:
 p=subprocess.run([str(JDK/'javap.exe'),'-classpath',CP,cls],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
 (ROOT/'00_audit'/('api_'+cls.rsplit('.',1)[-1]+'.txt')).write_text(p.stdout+p.stderr,encoding='utf8')
# Locate the authoritative GPU compatibility sections from the installed guide.
from pypdf import PdfReader
reader=PdfReader(str(INSTALL/'doc/UserGuide_21.02.pdf'))
hits=[]
def walk(items):
 for item in items:
  if isinstance(item,list):walk(item)
  else:
   title=str(item.get('/Title',''))
   if re.search(r'GPU|GPGPU|Graphics Processing',title,re.I):
    try:hits.append({'title':title,'page_index':reader.get_destination_page_number(item)})
    except Exception:pass
walk(reader.outline)
(ROOT/'00_audit/gpu_guide_outline.json').write_text(json.dumps(hits,indent=2),encoding='utf8')
print('GPU_GUIDE_OUTLINE',json.dumps(hits))
