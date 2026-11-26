from pathlib import Path
import json,datetime,os,shutil
h=Path(__file__).resolve().parents[1];read=lambda p:json.loads(p.read_text(encoding='utf8'))
at=datetime.datetime.now().astimezone().isoformat()
reviewpath=h/'WORK_CURRENT_REVIEW.json';v=read(reviewpath)
v['at']=at;v['current_run']=str(h/'cases/SP_C_split0_overset/c0_urans_pressure_urf01_20261103_043547');v['current_mesh_cells']=333939
v['decision']='0-degree pressure-relaxation diagnostic launched; confirm actual native timesteps before calling it RUNNING. Scientific gate remains HOLD.'
v['checkpoint_cadence_steps']=50
tmp=reviewpath.with_suffix('.work_tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8');os.replace(tmp,reviewpath)
src=h/'tools/write_current_home_resume_v3.py';s=src.read_text(encoding='utf8')
s=s.replace("'Changing15to40inner is a documented numerical sensitivity; dt0.002s, all physics, geometry, schemes and URF0.8/0.2 are retained. Zero-degree angle remains constant.',","'Latest completed source:40inner,velocityURF0.8,pressureURF0.2. Current separate diagnostic changes only pressureURF0.2to0.1, retaining dt0.002s and all geometry/physics/schemes. Read numerical_change.txt and pressure_relaxation_change.txt for the actual checkpoint phase. Never silently restore source relaxation values on a progressed diagnostic.',")
start=s.index("'Latest matched URANS mean over the last25steps:")
end=s.index('\n',start)
s=s[:start]+"""'Latest completed40-inner final window: '+json.dumps(review.get('completed_inner40_review',{}),ensure_ascii=False)+'. No scientific approval; pressure-relaxation diagnostic pending.',"""+s[end:]
s=s.replace("'Owned continuation generator: '+str(h/'tools/prepare_c0_urans_continue.py'),","'Previously reviewed continuation generators: '+str(h/'tools/prepare_c0_urans_continue.py')+' and '+str(h/'tools/prepare_c0_pressure_urf_diagnostic.py')+'. Their unique macros already exist; do not rerun the one-shot preparers blindly.',")
s=s.replace("'Changing15to40inner", "'Changing15to40inner")
(h/'tools/write_current_home_resume_v4.py').write_text(s,encoding='utf8')
print(json.dumps(dict(updated_review=True,prepared_resume_writer=str(h/'tools/write_current_home_resume_v4.py')),indent=2))
