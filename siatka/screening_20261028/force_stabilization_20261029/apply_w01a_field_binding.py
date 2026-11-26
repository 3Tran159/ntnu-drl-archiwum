from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'plot_wave_side_view.py';s=p.read_text(encoding='utf8')
s=s.replace("not active_case.startswith('W01_W20L4_M10_FS020_')","not active_case.startswith(('W01_W20L4_M10_FS020_','W01a_W20L4_M10_'))")
s=s.replace("assessment=read_json(R/'wave_periodicity_current.json')\n    case=assessment.get('case','W01_W20L4_M10_FS020_cycles_r2')","state=read_json(R/'wave_foil_run_state.json')\n    case=state.get('case','')\n    calm=case.startswith('W01a_W20L4_') and state.get('computation_stage')=='calm_settling'")
s=s.replace("else 'Wave and foil · latest exported calculated field'","else 'W01a · calm startup and foil · calculated field' if calm else 'Wave and foil · latest exported calculated field'")
s=s.replace("fig.text(.065,.905,'W01 · H = 0.50 m, wavelength = 20 m · M10 free-surface grid · field t = '+f'{field_time:.3f}'+' s',fontsize=12,color='#526772')","fig.text(.065,.905,('W01a · calm startup · H = 0 m · no inlet wave yet' if calm else 'W01 · H = 0.50 m, wavelength = 20 m')+' · M10 · field t = '+f'{field_time:.3f}'+' s',fontsize=12,color='#526772')")
s=s.replace("'lineage':'Current continuation field' if source.parent.name==case else", "'lineage':('Fresh calm-start calculated field' if calm else 'Current continuation field') if source.parent.name==case else")
s=s.replace("caption=('Case stopped", "caption=('W01a calm startup; wave height 0 m, inlet wave has not started. ' if calm else '')+('Case stopped")
p.write_text(s,encoding='utf8')
p=R/'wave_side_view_refresh.py';s=p.read_text(encoding='utf8')
s=s.replace("case=read(R/'wave_periodicity_current.json').get('case')","case=read(R/'wave_foil_run_state.json').get('case')")
s=s.replace("not case.startswith('W01_W20L4_M10_FS020_')","not case.startswith(('W01_W20L4_M10_FS020_','W01a_W20L4_M10_'))")
p.write_text(s,encoding='utf8')
for name in ('plot_wave_side_view.py','wave_side_view_refresh.py'):py_compile.compile(str(R/name),doraise=True)
import manual_control_common as c
case=c.safe_case('E:/ntnu/quasi2d_waves_20261029/W01a_W20L4_M10_calm_start_r1')
assert (case/'STOP').parent==case and not (case/'STOP').exists()
for bad in ('E:/ntnu/quasi2d_waves_20261029/HF_012_C003_regular_waves','E:/ntnu/else/W01a_W20L4_wrong','E:/ntnu/quasi2d_waves_20261029/W01a_wrong'):
 try:c.safe_case(bad)
 except ValueError:pass
 else:raise AssertionError(bad)
print('PASS W01a safe_case/STOP validation, without writing STOP; renderer bound to actual active case.')
