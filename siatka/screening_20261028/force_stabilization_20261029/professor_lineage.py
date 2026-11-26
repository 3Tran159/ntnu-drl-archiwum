"""Experiment lineage for the professor report. Standard-library only.

render_lineage(data) returns a self-contained semantic HTML fragment.
Expected data: temporal (temporal_original_comparison.json), mesh
(mesh_convergence.json), m09 (M09_build_result.json). Optional:
configdecision, conservation, waves. Parent includes LINEAGE_CSS once.
Arrows in the mesh lane describe design changes, never saved-state ancestry.
"""
from html import escape

LINEAGE_CSS = r"""
.lineage{font-size:17px;line-height:1.45;color:#172632}
.lineage p{margin:.45rem 0 .8rem}
.lineage .lin-key{font-size:14px;color:#52606b}
.lineage .lin-lanes{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px;align-items:start}
.lineage .lin-lane{min-width:0;border-top:3px solid #173d59;padding-top:14px}
.lineage .lin-lane h3{font-size:21px;margin:0 0 6px}
.lineage .lin-caption{font-size:14px;color:#52606b;margin:0 0 16px}
.lineage .lin-group{margin:16px 0}
.lineage .lin-group-title{font-size:15px;font-weight:650;margin:0 0 8px}
.lineage .lin-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;list-style:none;padding:0;margin:0}
.lineage .lin-node{min-width:0;padding:12px;border:1px solid #cbd5dd;background:#fff;position:relative}
.lineage .lin-node strong{font-size:18px;display:block;line-height:1.2;margin:0 0 5px}
.lineage .lin-node .lin-detail{font-size:14px;line-height:1.45;display:block}
.lineage .lin-result{font-size:14px;line-height:1.5;margin-top:8px;font-variant-numeric:tabular-nums}
.lineage .lin-state{font-size:12px;font-weight:600;display:block;color:#52606b;margin-top:7px}
.lineage .lin-wall{border-top:3px solid #b75925}
.lineage .lin-low{border-top:3px solid #0072b2}
.lineage .lin-future{border-style:dashed;color:#52606b}
.lineage .lin-arrow{display:flex;align-items:center;justify-content:center;gap:8px;font-size:14px;line-height:1.4;color:#52606b;margin:10px 0;text-align:center}
.lineage .lin-arrow:before{content:"\2193";font-size:21px;color:#173d59}
.lineage .lin-merge{border-left:3px solid #0072b2;background:#f5f8fa;padding:12px 14px}
.lineage .lin-merge .lin-node{margin-top:10px;background:#fff}
.lineage .lin-sources{display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:14px}
.lineage .lin-sources span{display:block}
.lineage .lin-root{border:1px solid #8fa5b6;background:#f5f8fa;padding:14px;margin-top:16px}
.lineage .lin-root strong{font-size:18px;display:block}
.lineage .lin-root small{font-size:14px;display:block;margin-top:5px}
.lineage .lin-fan-label{font-size:14px;text-align:center;color:#52606b;margin:12px 0 8px}
.lineage .lin-fan{display:grid;grid-template-columns:1fr 1fr;gap:12px;list-style:none;margin:0;padding:12px 0 0;position:relative;border-top:1px solid #8fa5b6}
.lineage .lin-fan:before{content:"";height:13px;position:absolute;left:50%;top:-14px;border-left:1px solid #8fa5b6}
.lineage .lin-fan .lin-node{border-top:3px solid #173d59}
.lineage .lin-note{font-size:14px;color:#52606b;margin-top:14px}
.lineage .lin-follow{border-left:3px solid #8fa5b6;margin-top:18px;padding:2px 0 2px 14px}
.lineage .lin-follow strong{font-size:16px}
.lineage .lin-follow p{font-size:14px}
.lineage .lin-gate{margin-top:26px;border-top:1px solid #8fa5b6;padding:18px 0 0}
.lineage .lin-gate-title{font-weight:650;font-size:18px;margin-bottom:10px}
.lineage .lin-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;list-style:none;padding:0;margin:0}
.lineage .lin-steps li{border-top:2px solid #173d59;padding:12px 0 0;min-width:0}
.lineage .lin-steps strong{display:block;font-size:17px;margin-bottom:5px}
.lineage .lin-steps span{display:block;font-size:14px}
.lineage .lin-final-note{font-size:14px;color:#52606b;margin-top:12px}
@media(max-width:1000px){
.lineage .lin-lanes{grid-template-columns:1fr;gap:28px}
.lineage .lin-row{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media(max-width:560px){
.lineage .lin-row{grid-template-columns:1fr}
.lineage .lin-fan{grid-template-columns:1fr}
.lineage .lin-sources,.lineage .lin-steps{grid-template-columns:1fr}
.lineage .lin-fan-label{text-align:left}
.lineage .lin-fan:before{left:18px}
.lineage .lin-node{padding:13px}
.lineage .lin-node strong{font-size:19px}
.lineage .lin-detail,.lineage .lin-result{font-size:15px}
}
@media print{
.lineage{font-size:11pt}
.lineage .lin-lanes{display:block}
.lineage .lin-lane{break-inside:auto;page-break-inside:auto;margin-bottom:20pt}
.lineage .lin-lane h3{break-after:avoid;page-break-after:avoid}
.lineage .lin-node,.lineage .lin-group,.lineage .lin-follow,.lineage .lin-gate{break-inside:avoid;page-break-inside:avoid}
.lineage .lin-row{grid-template-columns:repeat(3,minmax(0,1fr))}
.lineage .lin-fan{grid-template-columns:1fr 1fr}
.lineage .lin-node strong{font-size:12pt}
.lineage .lin-node .lin-detail,.lineage .lin-result,.lineage .lin-state,.lineage .lin-caption,.lineage .lin-note{font-size:10pt}
}
"""

def _e(value):
    return escape(str(value), quote=True)

def _number(value, places=6):
    try:
        return format(float(value), "." + str(places) + "f")
    except (ValueError, TypeError):
        return "—"

def _means_node(identifier, detail, result, kind="lin-low", status=None):
    """Force values are only from accepted settled_results or completed tests."""
    result = result or {}
    parts = ['<li class="lin-node '+kind+'" data-case="'+_e(identifier)+'">',
             '<strong>'+_e(identifier)+'</strong>',
             '<span class="lin-detail">'+_e(detail)+'</span>']
    if result.get("cells") is not None:
        parts.append('<span class="lin-detail">'+format(int(result["cells"]), ",")+' cells</span>')
    if result.get("CD") is not None and result.get("CL_total") is not None:
        parts.append('<div class="lin-result">C<sub>D</sub> '+_number(result["CD"])+
                     '<br>C<sub>L</sub> '+_number(result["CL_total"])+'</div>')
        status = status or "Settled mean"
    if status:
        parts.append('<span class="lin-state">'+_e(status)+'</span>')
    parts.append('</li>')
    return "".join(parts)

def _single_node(identifier, detail, result=None, kind="lin-low", status=None):
    return '<ul class="lin-row" style="grid-template-columns:1fr">'+_means_node(identifier,detail,result,kind,status)+'</ul>'

def _configuration_status(decision):
    status = str(decision.get("status", "")).lower()
    if status in ("accepted", "supported", "configuration_selected", "validated", "passed"):
        return "Decision recorded; see numerical checks."
    if status:
        return "Checks and decision: " + status.replace("_", " ") + "."
    return "Force-sensitivity tests complete; configuration decision requires diagnostic review."

def render_lineage(data):
    """Return responsive English experiment lineage HTML; no side effects."""
    data = data or {}
    mesh = data.get("mesh") or {}
    temporal = data.get("temporal") or {}
    m09 = data.get("m09") or {}
    decision = data.get("configdecision") or {}
    conservation = data.get("conservation") or {}
    settled = {v["id"]:v for v in mesh.get("settled_results", []) if v.get("id")}
    tests = {v.get("short", str(v.get("id","")).split("_")[0]):v for v in temporal.get("cases", [])}
    baseline = temporal.get("baseline") or {}
    checkpoint = (baseline.get("window") or [None, None])[-1]
    checkpoint_label = _number(checkpoint,3) if checkpoint is not None else "1.642"
    out = ['<div class="lineage" aria-label="Experiment design and restart lineage">',
           '<p class="lin-key">The left lane records mesh-design changes. The right lane records shared-checkpoint continuations. These are different relationships.</p>',
           '<div class="lin-lanes"><div class="lin-lane"><h3>Mesh design</h3>',
           '<p class="lin-caption">Each result below is a settled force-window mean. Cell count alone does not establish refinement.</p>',
           '<div class="lin-group"><div class="lin-group-title">Wall-function family · resolution series</div><ul class="lin-row">']
    for identifier, detail in [("M02","Coarse surface and bulk"),("M03","Finer surface and bulk"),("M05","Further surface and bulk refinement")]:
        out.append(_means_node(identifier,detail,settled.get(identifier),"lin-wall"))
    out += ['</ul></div><div class="lin-arrow">M03 → M04: near-wall spacing and layer count changed</div>',
            '<div class="lin-group"><div class="lin-group-title">Low-y+ family · successive refinement</div><ul class="lin-row">']
    for identifier, detail in [("M04","First full layer 3.000 µm; 40 layers"),
                               ("M06","First full layer 2.143 µm; 44 layers"),
                               ("M07","First full layer 1.531 µm; 48 layers")]:
        out.append(_means_node(identifier,detail,settled.get(identifier),"lin-low"))
    out += ['</ul><p class="lin-note">M04 → M06 → M07 also refine the surface and bulk controls.</p></div>',
            '<div class="lin-merge"><div class="lin-group-title">M08 combines two design references</div>',
            '<div class="lin-sources"><span><b>M06 →</b> surface and bulk controls</span><span><b>M07 →</b> first-layer height and 48 prisms</span></div>',
            _single_node("M08","Coarser surface/bulk than M07; same prism design",settled.get("M08")),
            '</div><div class="lin-arrow">M08 → M09: coarsen only the remote domain</div>']
    m09_result = settled.get("M09") or {"cells":m09.get("cells")}
    m09_status = None if settled.get("M09") else ("Mesh prepared; force result pending" if m09.get("cells") else "Design / mesh preparation")
    out.append(_single_node("M09","Foil, free-surface and prism controls retained",m09_result,status=m09_status))
    future = [v for k,v in settled.items() if k[1:].isdigit() and int(k[1:])>=10]
    if future:
        out += ['<div class="lin-arrow">Subsequent targeted mesh tests</div><ul class="lin-row">']
        for value in sorted(future,key=lambda x:int(x["id"][1:])):
            out.append(_means_node(value["id"],"See mesh controls for the tested change",value))
        out.append('</ul>')
    else:
        out += ['<div class="lin-follow lin-future"><strong>Next design option · local LE/TE refinement</strong>',
                '<p>M10 concept: finer leading and trailing edges, coarser middle chord. No flow result is implied.</p></div>']
    out += ['</div><div class="lin-lane"><h3>Calculation settings</h3>',
            '<p class="lin-caption">All four tests start independently from the same M04 state. Their final mean windows are matched.</p>',
            '<div class="lin-root"><strong>M04 accepted checkpoint</strong><small>t = '+checkpoint_label+' s · 138,468 cells</small>',
            '<small>Original force window: 1.442–1.642 s</small></div>',
            '<div class="lin-fan-label">Four independent restarts ↓</div><ul class="lin-fan">']
    settings = [("T01","1st-order time · 1 ms · 20 inner"),
                ("T02","2nd-order time · 1 ms · 20 inner"),
                ("T03","2nd-order time · 0.5 ms · 20 inner"),
                ("T04","2nd-order time · 1 ms · 10 inner")]
    for identifier,detail in settings:
        case = tests.get(identifier) or {}
        result = case.get("result") or {}
        completed = result.get("status")=="completed_fixed_horizon" or bool(result.get("source_unchanged") and result.get("settling_check_pass"))
        means = case.get("means") or {}
        if not means:
            means = {k:v.get("mean") for k,v in (result.get("last_window") or {}).items() if isinstance(v,dict)}
        state = "Matched window complete" if completed else "Awaiting completed test"
        out.append(_means_node(identifier,detail,means if completed else {},"",state))
    out += ['</ul><p class="lin-note">Compare T02/T01 for time order, T03/T02 for time step, and T04/T02 for inner iterations. Completed-test means use 2.042–2.242 s.</p>',
            '<div class="lin-follow"><strong>Original M04 → T01: continued force drift</strong>',
            '<p>This compares different physical-time windows. It is separate from the matched-setting tests above.</p></div>',
            '<div class="lin-arrow">T02 final state → matched conservation probes</div>']
    cstatus = "completed" if len(conservation.get("results",[]))==2 else str(conservation.get("status","")).replace("_"," ")
    cnote = "Status: "+cstatus+"." if cstatus else "See the diagnostic results for current status."
    out += ['<div class="lin-root"><strong>20 vs 10 inner iterations</strong><small>Same T02 final state; 40 steps at 1 ms per branch.</small>',
            '<small>Mass accumulation and net boundary flux are evaluated together. '+_e(cnote)+'</small></div>',
            '</div></div><div class="lin-gate"><div class="lin-gate-title">Decision sequence</div><ol class="lin-steps">']
    candidate = mesh.get("recommended_candidate")
    if isinstance(candidate,dict):
        candidate = candidate.get("id") or candidate.get("mesh")
    mesh_status = ("Candidate "+str(candidate)+"; final checks remain explicit." if candidate else
                   "No final mesh selected. Require agreement within 1% in both coefficients with two finer comparable cases.")
    out += ['<li><strong>1 · Calculation settings</strong><span>'+_e(_configuration_status(decision))+'</span></li>',
            '<li><strong>2 · Mesh selection</strong><span>'+_e(mesh_status)+'</span></li>',
            '<li><strong>3 · Calm and waves</strong><span>C01 → W01 (H 0.5 m, λ 20 m) → W02 (H 0.5 m, λ 30 m), with matched references and propagation checks.</span></li>',
            '</ol><p class="lin-final-note">Wave plan: FifthOrderVofWave; water depth 24 m; second-order time integration is a separate setting. W01 includes the 3λ/4λ domain comparison. Additional wave combinations follow the original cases.</p>',
            '</div></div>']
    return "".join(out)
