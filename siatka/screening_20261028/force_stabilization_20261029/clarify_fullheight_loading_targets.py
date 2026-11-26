from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent;p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
s=s.replace(" actual=_n(activation.get('wave_period_s'));height=_n(activation.get('height_m'))", " actual=_n(activation.get('wave_period_s'));height=_n(activation.get('height_m'))\n if actual is not None and actual<=0:actual=None",1)
s=s.replace(" fresh=case=='W01a_W20L4_M10_inlet_fullheight_restart_r3' or start==0", " fresh=case=='W01a_W20L4_M10_inlet_fullheight_restart_r3' or start==0\n verified_runtime=t is not None and start is not None and t>start+1e-12 and actual is not None and height is not None",1)
s=s.replace("elif stage=='inlet_wave_loading':headline='Loading saved startup state · inlet-wave activation pending'", "elif stage=='inlet_wave_loading':headline='Loading fresh zero-time input · full-height inlet from the first step' if fresh else 'Loading saved startup state · inlet-wave activation pending'",1)
old="stats=[(_f(t)+' s','Latest physical time'),(_f(height,6)+' m','Evaluated inlet target H'),(_f(actual,7)+' s','Analytic reference period')"
new="stats=[(_f(t,4 if fresh and t is not None and t<.02 else 3)+' s','Latest physical time'),(_f(height if verified_runtime else .5 if constant else height,6)+' m','Evaluated inlet target H' if verified_runtime else 'Planned inlet H · first step' if constant else 'Inlet target H pending verification'),(_f(actual if verified_runtime else None,7)+' s','Analytic reference period' if verified_runtime else 'Period awaiting runtime verification')"
assert old in s;s=s.replace(old,new,1)
s=s.replace("Numerical startup · full-height inlet wave already active", "Numerical startup · full-height inlet from the first step",1)
s=s.replace("fraction=100 if height is not None and abs(height-.5)<1e-8 else 0", "fraction=100 if verified_runtime and abs(height-.5)<1e-8 else 0",1)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Fresh loading targets planned; zero/stale period is unavailable until verified runtime.')
