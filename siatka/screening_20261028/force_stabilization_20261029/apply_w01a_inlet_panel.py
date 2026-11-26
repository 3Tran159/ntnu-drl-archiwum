from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent;p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
fn=(R/'w01a_inlet_panel_insert.txt').read_text(encoding='utf8')
assert 'def _render_inlet_wave(' not in s
s=s.replace('def _render_calm_start(state):',fn+'def _render_calm_start(state):')
s=s.replace(" if str(state.get('case','')).startswith('W01a_W20L4_')", " if state.get('case')=='W01a_W20L4_M10_inlet_wave_r1':return _render_inlet_wave(state)\n if str(state.get('case','')).startswith('W01a_W20L4_')",1)
# Origin-aware display follows the evaluator's optional origin without changing acceptance.
s=s.replace(" completed=max(0,int(math.floor((times[-1]+1e-10)/period)))", " origin=_n(assessment.get('wave_clock_origin_s')) or 0.\n completed=max(0,int(math.floor((times[-1]-origin+1e-10)/period)))")
s=s.replace("item=method._cycle(number,period,times,series,nominal,bad)", "item=method._cycle(number,period,times,series,nominal,bad,origin)")
s=s.replace("number=completed+1;lo=(number-1)*period", "number=completed+1;lo=origin+(number-1)*period")
s=s.replace("Phase 0–1 uses the absolute wave clock", "Phase 0–1 uses the documented analysis clock")
old="if(data.period)for(let n=Math.max(1,Math.ceil(view.left/T));n<=Math.floor(view.right/T)&&n<=20;n++)html+=marker(n*T,'#d4dee5','2 5',n+' T');"
new="if(data.period){const origin=data.origin||0;for(let n=Math.max(1,Math.ceil((view.left-origin)/T));n<=Math.floor((view.right-origin)/T)&&n<=20;n++)html+=marker(origin+n*T,'#d4dee5','2 5',n+' T after analysis origin');}"
assert old in s;s=s.replace(old,new)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Published separate W01a inlet-wave production branch; no legacy plan/history.')
