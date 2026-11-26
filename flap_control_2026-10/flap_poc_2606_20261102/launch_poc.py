from pathlib import Path
import subprocess,json,re,sys,datetime,hashlib
R=Path(__file__).resolve().parent;I=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8')
assert not (R.parent/'PAUSED_FOR_HOME.json').exists(), 'Project paused for home; explicit user resume required'

macro=(R/'macros'/sys.argv[1]).resolve();new_case=sys.argv[2]=='NEW';sim=(R/sys.argv[2]).resolve()
assert macro.is_relative_to(R) and sim.is_relative_to(R) and macro.exists() and (new_case or sim.exists())
assert macro.name in ['BuildFlapPOC.java','TestFlapPOC.java','RecoverFlapPOC.java']
compiled=R/'macros/compiled';compiled.mkdir(exist_ok=True)
p=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-cp',str(I/'star/lib/java/platform/modules/ext/*'),'-d',str(compiled),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
(R/'audit'/('compile_'+macro.stem+'.json')).write_text(json.dumps(dict(ok=p.returncode==0,messages=p.stdout+p.stderr),indent=2))
assert p.returncode==0,p.stderr
ps="Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^starccm[+][.]exe$' -and $_.CommandLine -match ' -batch ' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
entries=json.loads(p.stdout) if p.stdout.strip() else []
if isinstance(entries,dict):entries=[entries]
assert not any(str(R).lower() in e['CommandLine'].lower() for e in entries),'Another owned POC process is active'
active=next((e for e in entries if '-podkey' in e['CommandLine']),None)
assert active,'Licensed configuration not found'
args=[str(I/'star/lib/win64/clang20.1vc14.2-r8/lib/starccm+.exe'),'-power']
for key in ['-podkey','-licpath']:
 m=re.search(re.escape(key)+r'\s+("[^"]+"|\S+)',active['CommandLine']);assert m
 args.extend([key,m.group(1).strip('"')])
# One CPU process, no GPGPU flag. No existing queue/lock is touched.
args.extend(['-np','4','-cpubind','off']);args.extend(['-new'] if new_case else []);args.extend(['-batch',str(macro)]);args.extend([] if new_case else [str(sim)])
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');log=R/'runs'/(macro.stem+'_'+stamp+'.log')
with log.open('w',encoding='utf8') as f:p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,cwd=R,creationflags=subprocess.CREATE_NO_WINDOW,env={**__import__('os').environ,'NTNU_FLAP_POC_BUILD':'native_profile_poc_2606'})
receipt=dict(pid=p.pid,at=datetime.datetime.now().astimezone().isoformat(),version='2606.0002 / 21.04.009-R8',cpu_processes=4,gpu_compute=False,macro=str(macro),input=str(sim),log=str(log),existing_batch_pids=[e['ProcessId'] for e in entries])
(R/'audit'/('launch_'+macro.stem+'.json')).write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
