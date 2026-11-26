from pathlib import Path
import json,shutil,datetime,hashlib
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');old=W/'W20_H24_X4_Q2D_r1';new=W/'W20_H24_X4_Q2D_r2'
assert not (W/'preparation.lock').exists()
result=json.loads((old/'build_result.json').read_text());assert result['source_unchanged'] and not result['built_sim_exists']
new.mkdir(exist_ok=False)
identity=json.loads((old/'source_identity.json').read_text());source=Path(identity['source']);digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copy2(source,new/'baseline_copy.sim');assert digest(source)==digest(new/'baseline_copy.sim')==identity['source_sha256']
job=json.loads((old/'job.json').read_text());job['id']=new.name;job['recovery_from']=old.name;job['change']='Correct STAR2602 time-discretization setter API; same physical/numerical design'
(new/'job.json').write_text(json.dumps(job,indent=2))
s=(old/'WaveTankBuild24m.java').read_text();assert s.count('getTimeDiscretization().setSelected(')==1
s=s.replace('getTimeDiscretization().setSelected(','getTimeDiscretizationOption().setSelected(')
(new/'WaveTankBuild24m.java').write_text(s)
identity.update({'created_at':datetime.datetime.now().astimezone().isoformat(),'macro_sha256':digest(new/'WaveTankBuild24m.java'),'recovery_from':str(old),'status':'prepared_r2_after_compile_failure'})
(new/'source_identity.json').write_text(json.dumps(identity,indent=2))
runner=(R/'run_wave24m_preparation.py').read_text().replace("case=W/'W20_H24_X4_Q2D_r1'","case=W/'W20_H24_X4_Q2D_r2'")
(R/'run_wave24m_preparation_r2.py').write_text(runner)
(R/'wave_preparation_r1_failure.json').write_text(json.dumps({'reason':'Compiler rejected getTimeDiscretization().setSelected; actual compiled campaign API uses getTimeDiscretizationOption().setSelected','source_unchanged':True,'new_attempt':new.name,'source_evidence':'ContinueUntilSettled.java line62','all_r1_files_preserved':True},indent=2))
print(json.dumps({'status':'prepared_new_attempt','id':new.name,'source_unchanged':True}))
