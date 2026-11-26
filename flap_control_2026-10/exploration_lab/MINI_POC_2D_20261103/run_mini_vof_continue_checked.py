from pathlib import Path
import sys,json,datetime,subprocess,csv,statistics,os,time
import day_chain as M
D=M.R/'mini_vof_20261103';M.D=D;M.STATE=D/'STATUS.json';M.deadline=datetime.datetime(2026,11,3,20,50).astimezone().timestamp()
lock=D/'VOF.lock'
with lock.open('x') as f:json.dump(dict(pid=os.getpid(),created=time.time(),scope='bounded_empty_wave_test_not_night_campaign'),f)
try:
 ps="Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'starccm+.exe' -and $_.ExecutablePath -like '*21.02.007-R8*' -and $_.CommandLine -match 'NwarWave.java'} | ForEach-Object {$m=[regex]::Matches($_.CommandLine,'[A-Z]:[^\"\r\n]*?input\.sim');if($m.Count){$m[$m.Count-1].Value}}"
 z=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
 # Resolve W04 history from known live-run command; no command line or license is logged.
 candidates=list(Path(r'E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs').glob('W04_*/history.csv'));hist=max(candidates,key=lambda p:p.stat().st_mtime);rows=list(csv.DictReader(hist.open()));assert len(rows)>=41
 delta=[float(b['wall_s'])-float(a['wall_s']) for a,b in zip(rows[-41:-1],rows[-40:])];base=statistics.median(delta)
 M.atom(D/'W04_RESOURCE_REVIEW.json',dict(at=time.time(),history=str(hist),baseline_median_step_s=base,maximum_slowdown_fraction=.15,own_MPI=1,own_affinity_mask=16,W04_unchanged=True))
 out=D/'EMPTY_A005_CONTINUE_CHECKED';out.mkdir(exist_ok=True);M.launch('MINI_VOF_EMPTY_CONTINUATION','MiniVofAiryContinueChecked.java',out,D/'EMPTY_A005_AIRY_VOF2D/VOF_checkpoint.sim',max_runtime_s=2400)
 M.atom(D/'STATUS.json',dict(solver_state='STOPPED',operation='REVIEW',experiment='EMPTY_A005_CONTINUE_DT002_INNER50',result=json.loads((out/'SOLVE_STATUS.json').read_text()),night_approved=False,next='Independent wave-field review; do not add foil or increase amplitude before PASS'))
except Exception as e:
 M.atom(D/'STATUS.json',dict(solver_state='STOPPED' if M.workers()==0 else 'HOLD',operation='ERROR',error=str(e),night_approved=False));raise
finally:lock.unlink(missing_ok=True)
