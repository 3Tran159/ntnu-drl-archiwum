from pathlib import Path
import json,datetime
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');A=Path(r'E:/ntnu/quasi2d_waves_20261029/W01a_W20L4_M10_calm_start_r1')
s=json.loads((R/'wave_foil_run_state.json').read_text())
if s.get('case')!=A.name or s.get('controller_pid')!=30672 or not s.get('computation_active'):raise RuntimeError('Active W01a ownership changed; inspect before stop')
d=dict(at=datetime.datetime.now().astimezone().isoformat(),instruction='User explicitly requests inlet wave now without waiting for force settling; preserve current flow fields and activate wave ASAP.',current_stage='save_current_calm_fields_for_immediate_wave_activation',no_force_settling_requirement=True,source_case=A.name)
(R/'w01a_immediate_wave_authorization.json').write_text(json.dumps(d,indent=2))
(A/'user_wave_activation_request.json').write_text(json.dumps(d,indent=2));(A/'STOP').touch()
p=R/'wave_startup_policy_current.json';v=json.loads(p.read_text());v.update(updated_at=d['at'],require_calm_force_settling=False,reason='Latest explicit user override: flow expected to settle during wave travel; start inlet wave without waiting for force stabilization.',initial_stage='brief calm startup only',immediate_wave_authorization='w01a_immediate_wave_authorization.json');p.write_text(json.dumps(v,indent=2))
print(json.dumps(d,indent=2))
