"""Evidence-based near-wall design note; never controls the solver."""
import html,json
from pathlib import Path
R=Path(__file__).resolve().parent
def html_section():
 review=json.loads((R/'wall_design_review_20261029.json').read_text(encoding='utf-8'))
 measured=json.loads((R/'yplus_summary.json').read_text(encoding='utf-8'))
 rows=[]
 for d in review['analytical_estimate']['designs']:
  y=measured.get(d['mesh'],{})
  def val(key,n=3):return f"{y[key]:.{n}f}" if key in y else 'Pending'
  area=y.get('area_fraction_pct',{}).get('<1')
  pct=f'{area:.2f}%' if area is not None else 'Pending'
  when=f"{y['snapshot_time_s']:.3f} s" if 'snapshot_time_s' in y else 'Awaiting accepted state'
  rows.append(f"<tr><td>{d['mesh']}</td><td>{d['first_um']:.3f}</td><td>{d['layers']}</td><td>{d['equivalent_growth']:.3f}</td><td>{d['total_mm']:.2f}</td><td>{val('area_weighted_p95')}</td><td>{pct}</td><td>{when}</td></tr>")
 note='<div class="card" id="prism-design"><h3>Prism design: guidance and measured check</h3>'
 note+='<p>For this low-y+ family, target <b>y+ below 1</b>. Fluid Mechanics 101 describes the broader wall-law regimes below 5 and above 30; its calculator estimates the first layer and then corrects it using the CFD result. A high maximum at a collapsed trailing-edge layer needs a local mesh check.</p>'
 note+='<p>Parameters for every campaign mesh are compared in the <a href="#mesh-parameters">Mesh parameter table</a>.</p>'
 note+='<p><b>Working design:</b> M06 uses a 2.143 µm first layer, 44 layers and 15.46 mm total thickness. It provides a useful low-y+ starting point; the final mesh choice still requires force agreement and trailing-edge diagnostics. M07 provides the denser check; M08 tests M07 prism settings with M06 surface and outer sizes.</p>'
 note+='<details><summary>Calculation, assumptions and sources</summary><p>At U = 18 m/s, c = 1.19 m, ρ = 1000 kg/m³ and <b>assumed μ = 0.001 Pa·s</b>, the fully turbulent flat-plate estimate gives Re = 2.142 × 10⁷, first full layer = 3.271 µm for y+ = 1 and δ99 = 15.458 mm. Viscosity here is an estimate input, not a verified extraction from the saved material. The measured M04/M06 wall shear indicates about 2.55/2.53 µm for a p95 target of 1; 2.143 µm provides margin.</p>'
 note+='<p>The full first-cell thickness is twice the wall-to-centroid distance used in y+. *Equivalent growth solves T = h1 (rᴺ − 1)/(r − 1); it is not a measurement of local STAR stretching. Check actual layer coverage, velocity profiles and the transition to the outer mesh. The flat-plate thickness is a starting estimate for the foil, not a validated boundary-layer thickness.</p>'
 note+='<p>M04 → M06 refines wall-normal, tangential and outer spacing together. Their force difference cannot be assigned uniquely to y+. Retain local trailing-edge anomalies in diagnostics; do not hide them by quoting only mean y+.</p>'
 note+='<p>Sources: <a href="https://www.fluidmechanics101.com/pdf/calculators.pdf">Fluid Mechanics 101 calculator method, pp. 4–7</a>; <a href="https://static.skillshare.com/uploads/attachment/342580655/6cdf2f84/lectureNotes.pdf">Aidan Wimshurst, wall functions, p. 45</a>; installed STAR-CCM+ 2602 User Guide, Setting up a Wall Treatment.</p></details></div>'
 return note
