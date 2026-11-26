"""Current authorized wave scope; all rows remain planned until actual cases exist."""
import json,html
from pathlib import Path
R=Path(__file__).resolve().parent
def panel():
 p=json.loads((R/'overnight_plan_20261029.json').read_text());x=json.loads((R/'wave_extension_plan.json').read_text())
 s='<div class="card" id="wave-campaign-plan"><h3>Wave campaign · planned sequence</h3><p><b>FifthOrderVofWave</b> for regular waves; second-order time integration with a tested step. Preserve <b>24 m water depth</b>: bottom z = −22 m, waterline z = 2 m, top z = 8 m. Fixed foil, 2 m submergence, U = 18 m/s and verified head-wave direction.</p>'
 s+='<p>First: matched calm C01, W01 and W02, then the W01 3λ / 4λ domain check. Additional combinations start after those results pass review. All wave cases below are planned; no validated wave-force result exists yet.</p>'
 s+='<div class="table-wrap"><table><thead><tr><th>Case</th><th>Wave height [m]</th><th>Wavelength [m]</th><th>Purpose</th></tr></thead><tbody>'
 for name in ['W01','W02']:
  w=p['wave_cases'][name];s+='<tr><th>'+name+'</th><td>'+str(w['height_m'])+'</td><td>'+str(w['lambda_m'])+'</td><td>Primary requested case</td></tr>'
 for w in x['cases']:s+='<tr><th>'+w['id']+'</th><td>'+str(w['height_m'])+'</td><td>'+str(w['lambda_m'])+'</td><td>'+html.escape(w['purpose'])+'</td></tr>'
 s+='</tbody></table></div><p class="muted">Use matching calm references and common mesh/time settings within comparisons. Smaller wave heights may require a finer surface band and a repeated 0.5 m baseline. Domain lengths remain 4λ, with the requested W01 3λ sensitivity. Gauge amplitude, phase, reflections and forcing/damping placement must pass before force comparisons.</p><div class="formula">ΔCD = mean(CDwave) − CDcalm</div></div>'
 return s
