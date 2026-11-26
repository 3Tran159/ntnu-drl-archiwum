from pathlib import Path
p=Path(__file__).with_name('native_launch.py');t=p.read_text()
old="assert not any(str(R).lower() in e['CommandLine'].lower() for e in entries),'Owned hydro process already active'"
new='''owned=[e for e in entries if str(R).lower() in e['CommandLine'].lower()]
overlap=None
if owned:
 assert macro.name=='InitializeHydroControl.java' and variant=='SP_A' and len(owned)==1,'Owned hydro process already active'
 receipt=json.loads((R/'audit/launch_BuildHydroMesh.json').read_text())
 assert receipt['pid']==owned[0]['ProcessId'] and receipt['variant']=='SP_B' and receipt['executed_macro'] in owned[0]['CommandLine'],'Only independent SP_A initialization alongside the owned SP_B mesh allowed'
 check=subprocess.run(['powershell','-NoProfile','-Command',"$os=Get-CimInstance Win32_OperatingSystem; $cpu=Get-CimInstance Win32_Processor; @{free_gib=$os.FreePhysicalMemory/1048576; cpu_load=$cpu.LoadPercentage}|ConvertTo-Json -Compress"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
 resources=json.loads(check.stdout);assert resources['free_gib']>=24 and resources['cpu_load']<=35,'Resource headroom insufficient'
 overlap=dict(mesh_pid=receipt['pid'],resources=resources,permission='User authorized additional CPU; independent owned cases, maximum 12 configured CPU ranks, no GPU')
 (R/'audit/bounded_overlap.json').write_text(json.dumps(overlap,indent=2))'''
assert old in t
p.write_text(t.replace(old,new),encoding='utf8')
s=Path(__file__).with_name('status_brief.py');v=s.read_text().replace("r'^(starccm[+]|mpiexec|hydra_service|smpd)'","r'^(star-?ccm[+]|mpiexec|hydra_service|smpd)'");s.write_text(v,encoding='utf8')
print('Narrow resource-gated overlap enabled for SP_A initialization with current SP_B mesh only')
