from pathlib import Path
import shutil,datetime,py_compile
h=Path(__file__).resolve().parents[1];p=h/'tools/review_c0_diagnostic.py';s=p.read_text(encoding='utf8')
needle="labels=sorted(set(re.match(r'Background_(.+)_volume.csv',p.name).group(1) for p in run.glob('Background_*_volume.csv')))"
replacement=needle+"\nlabels=[label for label in labels if (run/('residual_normalization_'+label+'.txt')).exists()] # captureComparison writes this completion marker after all field exports"
assert needle in s and replacement not in s
shutil.copy2(p,h/'audit'/('review_c0_before_export_guard_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.py'))
s=s.replace(needle,replacement)
needle="o['window_results']=[]"
extra="""o['last']=d.iloc[-1].to_dict()
o['whole_run_guards']['mass']=bool((d.mass_imbalance_relative<1e-4).all())
for column in ['omega_floor_cells','k_floor_cells']:
 if column in d:o['whole_run_guards'][column]=bool((d[column]==0).all())
if 'max_turbulent_viscosity_ratio' in d:o['whole_run_guards']['viscosity_ratio']=bool((d.max_turbulent_viscosity_ratio<99999).all())
o['whole_run_guards']['finite_history']=bool(np.isfinite(d.select_dtypes(include=[np.number]).to_numpy()).all())
"""
assert needle in s;s=s.replace(needle,extra+needle)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True);print('Review now skips incomplete field exports and checks all recorded strict guards; no queue or solver changes.')
