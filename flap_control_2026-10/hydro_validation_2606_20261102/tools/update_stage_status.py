from pathlib import Path
import datetime,json
R=Path('F:/ntnu/flap_control');H=R/'hydro_validation_2606_20261102'
p=H/'tools/native_launch.py';t=p.read_text().replace("'CheckHydroMotion.java'}","'CheckHydroMotion.java','InitializeHydroControl.java'}").replace("np=1 if macro.name.startswith('Inspect') else 4","np=1 if macro.name.startswith('Inspect') else (8 if macro.name=='InitializeHydroControl.java' else 4)")
p.write_text(t)
p=R/'HOME_RESUME_INSTRUCTIONS.md';t=p.read_text()
notice='> Campaign resumed by explicit user instruction on 2026-11-02. The pause/checkpoint details below are historical. Consult CAMPAIGN_STATUS.json for current work. W04 remains unauthorized for this task.\n\n'
if notice not in t:p.write_text(notice+t,encoding='utf8')
state=dict(status='active_model_build',at=datetime.datetime.now().astimezone().isoformat(),stage='SP_B meshing; SP_A steady initialization prepared',W04_allowed=False,waves_allowed=False,DRL_allowed=False,home_checkpoint_unchanged=True,SP_A='cold-start pressure impulse caught and saved; initialization correction pending',SP_B='mesh building',SP_C='pending',training_approved=False,cpu_processes_meshing=4,cpu_processes_initialization=8,gpu_compute=False)
(R/'CAMPAIGN_STATUS.json').write_text(json.dumps(state,indent=2))
print(json.dumps(state))
