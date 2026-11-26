from pathlib import Path
import json,shutil,py_compile
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf-8')
p=R/'overnight_plan_20261029.json';j=load(p);j['wave_model']='FifthOrderVofWave';j['wave_model_authorization']='User explicitly confirmed fifth-order waves; keep second-order time integration as a separate numerical setting.'
for w in j['wave_cases'].values():w['wave_model']='FifthOrderVofWave'
save(p,j)
p=R/'wave_extension_plan.json';j=load(p);j['shared_controls']['wave_model']='FifthOrderVofWave'
for w in j['cases']:w['wave_model']='FifthOrderVofWave'
save(p,j)
p=Path('E:/ntnu/quasi2d_waves_20261029/ACTIVE_WAVE_SCOPE.json');j=load(p);j['wave_model']='FifthOrderVofWave';j['time_integration']='SECOND_ORDER with tested dt';save(p,j)
p=R/'mesh_selection_plan.json';j=load(p);j['wave_model']='FifthOrderVofWave';save(p,j)
p=R/'build_dashboard_en.py';b=R/'build_dashboard_before_24m_wave_scope.py'
if not b.exists():shutil.copy2(p,b)
s=p.read_text(encoding='utf-8')
s=s.replace("templates={","templates={\n'@@WAVE_PLAN@@':__import__('wave_scope_panel').panel(),",1)
lines=s.splitlines()
matched=[i for i,line in enumerate(lines) if '<h3>Before the wave campaign</h3>' in line]
assert len(matched)==1
lines[matched[0]]='@@WAVE_PLAN@@</div>'
s='\n'.join(lines)+'\n'
s=s.replace("'active_tests':active_tests,","'wave_scope':read(R/'wave_extension_plan.json',{}),'active_tests':active_tests,",1)
p.write_text(s,encoding='utf-8');py_compile.compile(str(p),doraise=True);py_compile.compile(str(R/'wave_scope_panel.py'),doraise=True)
p=R/'RESUME_AT_HOME.txt';old=p.read_text(encoding='utf-8')
p.write_text('WAVE MODEL CONFIRMED BY USER: FifthOrderVofWave for W01/W02 and all extra waves. SECOND_ORDER time integration is independent and remains the intended solver setting with tested dt.\n'+old,encoding='utf-8')
for p in [R/'overnight_plan_20261029.json',R/'wave_extension_plan.json']:
 j=load(p);cases=j.get('wave_cases',j.get('cases'));cases=list(cases.values()) if isinstance(cases,dict) else cases
 assert all(w['depth_m']==24 and w['bottom_z_m']==-22 and w['top_z_m']==8 and w['wave_model']=='FifthOrderVofWave' for w in cases)
print('Primary and extra wave plans validated:24m,unchanged vertical bounds,FifthOrderVofWave. No simulation modified or launched.')
