from pathlib import Path
import json,datetime,shutil,os
h=Path(__file__).resolve().parents[1];now=datetime.datetime.now().astimezone().isoformat()
run=h/'cases/SP_C_split0_overset/c0_tight_warm_20261103_031654'
r=json.loads((run/'work_review.json').read_text(encoding='utf8'))
st=json.loads((run/'status.json').read_text(encoding='utf8'))
assert st['status']=='steady_diagnostic_ready'
last=r['last'];f=r['field_exports']['final']
assert last['p_absolute_min_Pa']>12339.214766776897 and last['mass_imbalance_relative']<1e-4
assert f['omega_floor_cells']==f['k_floor_cells']==f['viscosity_ratio_cap_cells']==0
p=h/'WORK_CURRENT_REVIEW.json';old=json.loads(p.read_text(encoding='utf8'))
shutil.copy2(p,h/'audit'/('WORK_REVIEW_before_warm_final_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.json'))
old.update(at=now,decision='HOLD: C0 hydrodynamic results remain unapproved; all nonzero angles blocked.',
summary='Original C/B discrepancy: CL+14.6869%, CD-9.5692%; about94% of excess lift was on the fixed main foil. More inner iterations and changing interpolation alone did not resolve it. On the old rectangular cage, momentum-second-order alone recreated near-interface pressure/head spikes even without k/omega clipping. The new hinge-following cage removes the upstream near-wall interface while preserving all background cells and physical foil geometry. Its first-order mapped continuation passed strict guards through1050 iterations. The full CL/CD bias is not yet quantitatively explained; matched second-order flow is required.',
mesh='333939cells:304810Background+29129Overset;1481acceptors,0errors,0difficult stencils; minV9.128750119e-12m3,minQ0.061048186,maxacceptor ratio1.685069. All background cells unchanged to roundoff. No acceptors/inactive background upstream x0.90m. Physical STLs unchanged; nominal hinge gap2.5mm.',
next='Review momentum-second-order continuation from native1050/time0. If strict field/mesh/force gates pass, separately restore SST-second-order. Only then prepare a no-reset matched URANS comparison. No nonzero angle before positive C0 scientific audit.',
obstacle='Original force bias remains unapproved. First-order warm stage has declining but nonzero residual/force drift; window criterion permits numerical continuation only. No qualified second-order URANS on the new cage yet.',
reviewed_recovery_checkpoint=dict(path=str(run/'steady_checkpoint.sim'),sha256='d8fd31ab9fb0685c212743a466c8abca2bfb115f2f630b1912d6826e471aef48',bytes=599052165,native_iteration=1050,physical_time_s=0,CL=last['CL_hydro'],CD=last['CD'],Mh_Nm=last['Mh_Nm'],pabs_min_Pa=last['p_absolute_min_Pa'],native_reopen_verified=False,scientific_approved=False,note='Numerically healthy FIRST_ORDER steady checkpoint. Native reopen/readback pending in momentum2 continuation; not an approved hydrodynamic result.'),
latest_field_review=dict(iteration=1050,meanflow_p0_max_near_Pa=f['meanflow_p0_max_near_Pa'],meanflow_p0_p99_near_Pa=f['meanflow_p0_p99_near_Pa'],zero_omega_and_k_floor=True,mesh_errors=0,mesh_difficult_stencils=0,interpretation='No old upstream interface spikes under first order; cage and scheme effects still require separation.'))
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(old,indent=2,ensure_ascii=False),encoding='utf8');os.replace(tmp,p)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(dict(at=now,kind='work_tight_warm_final_review',run=str(run),numerical_continuation_approved=True,scientific_approved=False,checkpoint=old['reviewed_recovery_checkpoint'],field_review=old['latest_field_review']))+'\n')
print(json.dumps(dict(at=now,numerical_continuation_approved=True,scientific_approved=False,iteration=1050,CL=last['CL_hydro'],CD=last['CD'],pabs=last['p_absolute_min_Pa'],mass=last['mass_imbalance_relative']),indent=2))
