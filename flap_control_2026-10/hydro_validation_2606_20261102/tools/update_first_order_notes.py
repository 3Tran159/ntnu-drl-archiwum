from pathlib import Path
import json,datetime
h=Path(__file__).resolve().parents[1];now=datetime.datetime.now().astimezone().isoformat()
p=h.parent/'HOME_RESUME_INSTRUCTIONS.md';s=p.read_text(encoding='utf8')
i=s.index('## Current experiment');j=s.index('\nVerified zero-step source:',i)
s=s[:i]+'''## Current experiment — first-order diagnostic continuation
ContinueC0FirstOrder.java continues the saved steady fields from430 iterations without initialization, solution reset or remeshing. Physical time remains0. Read NIGHT_STATUS/NIGHT_QUEUE_STATE for live progress and the active run folder.
Input:
F:\\ntnu\\flap_control\\hydro_validation_2606_20261102\\cases\\SP_C_split0_overset\\c0_relaxed_init_20261103_005648\\steady_checkpoint.sim
847104592 bytes; SHA256945353bf97a01ea6b57148c99c073db548cdbf24c9aa33ccd5130ecaf684c09a.
The macro verifies saved Fx/Fz/Mh/CL/CD before continuing; checkpoint_readback.txt is the native-readback evidence once it succeeds.
Only flow/SST convection changes from second order to first order for startup recovery; URF0.3/0.1,DISTANCE,NONE conservation,mesh/physical conditions retained.
CSV iteration means additional iterations; native_iteration =430+iteration. Maximum1500 additional iterations, complete checkpoints250 apart.
First-order results cannot be accepted. Restore second-order convection, FLUX_CORRECTION and matched URANS, then re-audit fields/forces before any deflection.
Previous relaxed trial was deliberately paused at430:834 omega-floor,5k-floor,max viscosity ratio100000; no Overset errors. This is an unapproved partial solution, not an accepted initialization.
'''+s[j:]
s=s.replace('Current startup: steady mode, physical time0, DISTANCE, conservation NONE, continuity initialization enabled100 iterations.','Fresh precursor used steady mode, physical time0, DISTANCE, conservation NONE and continuity initialization100 iterations. The current continuation does not invoke continuity initialization or reset fields.')
s=s.replace('Current flap launcher PID31000 uses2606,8CPU, no GPU.','Flap launcher PID31000 was the relaxed precursor and has exited. The current first-order launch is recorded in audit/night_launch_latest.json and uses2606,8CPU,no GPU.')
s=s.replace('lower-relaxation trial','lower-relaxation precursor')
p.write_text(s,encoding='utf8')
p=h/'validation/BC_native_wall_distance_screen.json';o=json.loads(p.read_text())
for name,case in o['cases'].items():
 for region,item in case.items():
  if 'closer_wall_on_other_region' in item:
   item['closer_other_foil_component']=item.pop('closer_wall_on_other_region')
o['component_test_note']='Background test selects closer flap than main; in B both components share the same region. FlapOverset test selects main much closer than flap, directly checking cross-region wall-distance handling.'
o['work_conclusion']='No support for global omission of the main foil from Overset wall distance. In C40,768 active OV cells with main distance<0.1*flap distance have median native/geometric distance ratio0.99999928 and99th percentile1.000735. Clipped omega cells mostly also have correct distance. Small chordal/mesh differences remain near corners; this is a screen, not complete validation.'
p.write_text(json.dumps(o,indent=2),encoding='utf8')
p=h/'tools/screen_native_wall_distance.py';ss=p.read_text(encoding='utf8').replace("'closer_wall_on_other_region'","'closer_other_foil_component'");p.write_text(ss,encoding='utf8')
p=h/'validation/C0_causal_audit_status.json';o=json.loads(p.read_text());o['at']=now
o['observations'].append(dict(hypothesis='Wall distance ignores main foil in moving region',finding='Geometric screen contradicts global omission:768 OV cells much closer to main wall have median native/geometric ratio0.99999928,99th1.000735. Clipped omega also mostly has correct distance.',evidence='validation/BC_native_wall_distance_screen.json'))
o['current_experiment']='Continue430-iteration refined relaxed fields with first-order flow/SST convection; no reset, no acceptance. Require return to second order/FLUX/URANS after recovery.'
p.write_text(json.dumps(o,indent=2),encoding='utf8')
ev=dict(at=now,kind='work_wall_distance_review',conclusion='Cross-region wall-distance omission not supported by measured fields',evidence=str(h/'validation/BC_native_wall_distance_screen.json'),scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
print(json.dumps(ev,indent=2))
