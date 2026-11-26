from pathlib import Path
import json,re,datetime
h=Path(__file__).resolve().parents[1]
paths={'B0':h/'audit/comparison_SP_B_20261102_234628/diagnostic.txt','old_C0':h/'audit/comparison_SP_C_20261102_223230/diagnostic.txt','new_C0_steady_second_order':h/'cases/SP_C_split0_overset/c0_tight_turbulence_second_20261103_034119/forces_final.txt'}
out=dict(at=datetime.datetime.now().astimezone().isoformat(),scientific_approved=False,comparison_limit='Instantaneous native force readbacks; new C0 is still STEADY while B/oldC are URANS. Do not interpret the remaining difference as a clean Overset discretization error.',cases={})
for key,p in paths.items():
 text=p.read_text(encoding='utf8');d=dict(source=str(p),forces={})
 for group in ['main','flap']:
  for mode in ['pressure','shear','total']:
   name=group+'_'+mode+'_force';m=re.search(re.escape(name)+r'=\[([^\]]+)\]',text);assert m,name
   d['forces'][name]=[float(x.strip()) for x in m.group(1).split(',')]
 d['Fx_N']=sum(d['forces'][g+'_total_force'][0] for g in ['main','flap']);d['Fz_N']=sum(d['forces'][g+'_total_force'][2] for g in ['main','flap'])
 out['cases'][key]=d
for key in ['old_C0','new_C0_steady_second_order']:
 d=out['cases'][key];b=out['cases']['B0']
 d['differences_from_B']={name:[v-b['forces'][name][i] for i,v in enumerate(vector)] for name,vector in d['forces'].items()}
 d['Fx_difference_N']=d['Fx_N']-b['Fx_N'];d['Fz_difference_N']=d['Fz_N']-b['Fz_N']
p=h/'validation/C0_tight_force_decomposition.json';p.write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(dict(path=str(p),comparison_limit=out['comparison_limit'],forces={key:{k:v for k,v in d.items() if k in ['Fx_N','Fz_N','Fx_difference_N','Fz_difference_N','differences_from_B']} for key,d in out['cases'].items()}),indent=2))
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v['at']=out['at'];v['summary']='Original C/B bias CL+14.6869%,CD-9.5692% was associated with spurious near-wall pressure/velocity/turbulence fields; about94% excess lift was on the fixed main foil. Increasing inner iterations15to40 or interpolation change alone did not remove it. On the old rectangle, momentum-second-order recreated pressure/head spikes even with SSTfirst-order and no clipping. Moving the numerical cage to the hinge gap while preserving physical STLs and every background cell removed those spikes; momentum2 and then SST2 passed strict guards. Latest full-second-order steady values CL0.319132763345,CD0.0074579457186,Mh-12.3599041086,pabs31019.3Pa. This is not yet a matched URANS comparison; residual/far-field issues remain. No scientific approval or nonzero angles.'
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2),encoding='utf8');tmp.replace(p)
