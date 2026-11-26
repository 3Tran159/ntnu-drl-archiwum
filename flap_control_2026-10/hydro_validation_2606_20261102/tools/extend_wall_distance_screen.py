from pathlib import Path
h=Path(__file__).resolve().parents[1]
p=h/'tools/screen_native_wall_distance.py';s=p.read_text(encoding='utf8')
needle="  cols=['X (m)'"
assert needle in s
s=s.replace(needle,"  other=selected[selected['geom_main_m'] < .1*selected['geom_flap_m']] if region=='FlapOverset' else selected[selected['geom_flap_m'] < .1*selected['geom_main_m']]\n  case[region]['closer_wall_on_other_region']=dict(count=len(other),ratio_quantiles=other.native_to_geometric_ratio.quantile([0,.01,.5,.99,1]).to_dict() if len(other) else {})\n"+needle)
s=s.replace('print(json.dumps(out,indent=2))',"print(json.dumps({k:{r:{q:v for q,v in a.items() if q not in ['worst_high_ratio']} for r,a in c.items()} for k,c in out['cases'].items()},indent=2))")
p.write_text(s,encoding='utf8')
p=h/'tools/plot_fresh_fields.py';s=p.read_text(encoding='utf8').replace("'C0_fresh_fields_'+label","'C0_fresh_fields_'+run.name+'_'+label").replace("'C0_fresh_Cp_'+label","'C0_fresh_Cp_'+run.name+'_'+label").replace('C0 — czysta inicjalizacja','C0 — rozruch diagnostyczny')
p.write_text(s,encoding='utf8')
print('Updated wall-distance screening and unique scientific figure names.')
