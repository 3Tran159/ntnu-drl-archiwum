from pathlib import Path
R=Path(__file__).resolve().parents[1];p=R/'macros/InspectMeshFailure.java';p.write_text(p.read_text().replace('mi.setParts(rs);','mi.getParts().setObjects(rs);'),encoding='utf8')
p=R/'tools/native_launch.py';t=p.read_text().replace("'InitializeHydroControl.java'}","'InitializeHydroControl.java','InspectMeshFailure.java'}")
a=t.index('if owned:\n');b=t.index("\np=subprocess.run(['C:/Program Files/Eclipse",a)
t=t[:a]+'''if owned:
 assert len(owned)==1,'Only one owned calculation can accompany a diagnostic'
 if macro.name=='InspectMeshFailure.java':
  assert any(n in owned[0]['CommandLine'] for n in ['InitializeHydroControl.java','BuildHydroMesh.java']),'Diagnostic cannot overlap a transient or motion test'
  reason='Read-only mesh/field export, one CPU rank; no solve and no simulation save'
 else:
  assert macro.name=='InitializeHydroControl.java' and variant=='SP_A','Owned hydro process already active'
  receipt=json.loads((R/'audit/launch_BuildHydroMesh.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['variant']=='SP_B' and receipt['executed_macro'] in owned[0]['CommandLine'],'Only independent SP_A initialization alongside owned SP_B mesh allowed'
  reason='User authorized additional CPU; independent owned SP_A initialization and SP_B mesh'
 check=subprocess.run(['powershell','-NoProfile','-Command',"$os=Get-CimInstance Win32_OperatingSystem; $cpu=Get-CimInstance Win32_Processor; @{free_gib=$os.FreePhysicalMemory/1048576; cpu_load=$cpu.LoadPercentage}|ConvertTo-Json -Compress"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
 resources=json.loads(check.stdout);assert resources['free_gib']>=24 and resources['cpu_load']<=50,'Resource headroom insufficient'
 overlap=dict(other_owned_pid=owned[0]['ProcessId'],resources=resources,reason=reason)
 (R/'audit'/('bounded_overlap_'+macro.stem+'.json')).write_text(json.dumps(overlap,indent=2))
'''+t[b:]
p.write_text(t,encoding='utf8');print('Read-only mesh diagnostic added with one-rank/resource guards')
