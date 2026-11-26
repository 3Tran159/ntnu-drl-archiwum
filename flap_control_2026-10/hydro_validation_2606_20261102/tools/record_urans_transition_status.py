from pathlib import Path
import json,datetime
h=Path(__file__).resolve().parents[1];p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v['at']=datetime.datetime.now().astimezone().isoformat()
v['reviewed_recovery_checkpoint']['native_reopen_verified']=True
v['reviewed_recovery_checkpoint']['native_reopen_evidence']=str(h/'cases/SP_C_split0_overset/c0_tight_urans_20261103_035229/checkpoint_readback.txt')
v['next']='Run the reviewed C0TightURANSV2 transition from exact native2310 source. Verify physical time and history growth, conversion settings, strict guards and unchanged zero-degree mesh pose. All nonzero angles remain blocked.'
v['obstacle']='First URANS transition stopped before any PDE step because a source-relaxation check was placed after changing the time model. Fields,forces,time and protected source were unchanged. V2 checks source settings before conversion, records post-conversion defaults and explicitly matches B0.8/0.2. No scientific approval; residual and original bias review remains pending.'
v['B_matched_numerics']=dict(audit=str(h/'audit/matching_B_20261103_034849'),source_sha256_before_after='5f9a86e51f8eb96cc1adb0fd36a61ae48e015600512598517b6ec2f6c9190ff1',solver_steps=0,source_saved=False,velocity_urf=.8,pressure_urf=.2,dynamic_velocity_urf=False,dt_s=.002,inner_iterations=15,time_order='SECOND_ORDER',flow_order='SECOND_ORDER',SST_order='SECOND_ORDER',native_iteration=2250,physical_time_s=.3)
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2),encoding='utf8');tmp.replace(p)
print(json.dumps(dict(at=v['at'],recovery_reopen_verified=True,all_nonzero_angles_blocked=True)))
