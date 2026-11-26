from pathlib import Path
import json,datetime,py_compile
h=Path(__file__).resolve().parents[1]
p=h/'tools/prepare_tight_controlled_continuation.py';s=p.read_text(encoding='utf8')
old="s=s.replace('579468',str(mesh_total))"
new="s=s.replace('579468',str(mesh_total)).replace('flow.setContinuityInitialization(true);','flow.setContinuityInitialization(false);')"
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'))
v.update(at=datetime.datetime.now().astimezone().isoformat(),obstacle='Rozruch z przeniesionych pól faktycznie postępuje. Do800 iteracji wszystkie ścisłe progi przechodzą:zero ograniczania k/omega i błędów Overset,pabs>32kPa,masa około9e-8. CL i moment nadal dryfują. To nadal pierwszy rząd,więc CL/CD nie są zatwierdzone.',next='Dokończyć stabilizację pierwszego rzędu,ocenić pola i residuals,zapisać checkpoint. Następnie osobna kontynuacja z jedyną zmianą:drugi rząd pędu. Dopiero po jej ocenie drugi rząd SST i URANS. Wszystkie kolejne wychylenia pozostają zablokowane.')
v['latest_field_review']=dict(iteration=500,meanflow_p0_max_near_Pa=179002.35595299728,meanflow_p0_p99_near_Pa=164158.20471808064,zero_omega_and_k_floor=True,mesh_errors=0,mesh_difficult_stencils=0,interpretation='No visible old interface spikes in present FIRST_ORDER diagnostic. This alone does not isolate cage effect from convection-order effect; second-order return is required.',figure=str(h/'reports/C0_fresh_fields_c0_tight_warm_20261103_031654_iter_500.png'))
p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=v['at'],kind='work_tight_warm_800_review',continue_current_case=True,next_order_change_queued=False,scientific_approved=False,field_review=v['latest_field_review']))+'\n')
print('Updated scientific review; future continuation preserves CI off. No new solver launched.')
