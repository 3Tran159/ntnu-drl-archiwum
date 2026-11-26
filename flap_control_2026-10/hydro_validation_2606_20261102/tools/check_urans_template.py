from pathlib import Path
import re,py_compile,json
h=Path(__file__).resolve().parents[1]
py_compile.compile(str(h/'tools/prepare_tight_urans.py'),doraise=True)
s=(h/'tools/tight_urans_execute.template.txt').read_text(encoding='utf8')
header=re.search(r'w.write\("step,([^"]+)"\)',s).group(1)
line=next(x for x in s.splitlines() if 'w.write(String.format' in x)
fmt=re.search(r'Locale.ROOT,"([^"]+)"',line).group(1)
assert len(('step,'+header).replace('\\n','').split(','))==28
assert len(fmt.replace('\\n','').split(','))==28
assert len(re.findall(r'%[.0-9]*[dgf]',fmt))==26
print(json.dumps(dict(template_columns=28,format_arguments=26,python_compile='passed',native_compile='pending exact B parameters',solver_started=False)))
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'))
v['reviewed_recovery_checkpoint']['flow_convection']='SECOND_ORDER'
v['reviewed_recovery_checkpoint']['sst_convection']='SECOND_ORDER'
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2),encoding='utf8');tmp.replace(p)
p=h/'tools/write_current_home_resume_v2.py';s=p.read_text(encoding='utf8')
s=s.replace('Tight warm recovery: FIRST_ORDER momentum/SST, DISTANCE Overset','Latest reviewed steady recovery: SECOND_ORDER momentum/SST, DISTANCE Overset')
s=s.replace('Completed numerical work: new tight Overset cage mesh; native connectivity/geometry audit; mapped healthy fields; guarded first-order warm continuation1050iterations.','Completed numerical work: new tight Overset cage mesh; native connectivity/geometry audit; mapped healthy fields; first-order1050iterations; momentum-second-order540additional; SST-second-order720additional. Latest native iteration2310.')
p.write_text(s,encoding='utf8')
