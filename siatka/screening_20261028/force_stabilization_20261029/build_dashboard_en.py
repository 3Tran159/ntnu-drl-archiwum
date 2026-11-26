"""One-file, English-only evidence dashboard. No network dependencies."""
import base64,csv,datetime,html,json,math,os,re
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def read(p,d=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return d
def rows(p):
 try:
  with p.open(encoding='utf-8-sig',newline='') as f:return [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f) if all(v is not None and v!='' for v in r.values())]
 except (OSError,ValueError):return []
def fmt(x,n=4):return '—' if x is None else f'{x:,.{n}f}'
def esc(x):return html.escape(str(x))
def image(name,caption):
 p=R/name
 if not p.exists():return '<div class="pending">Field export / rendering in progress. No synthetic result is substituted.</div>'
 return '<figure><img loading="lazy" alt="'+esc(caption)+'" src="data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'"><figcaption>'+caption+'</figcaption></figure>'
live=read(R/'live_summary.json',{});state=live.get('queue',{});jobs=read(R/'queue.json',[]);yp=read(R/'yplus_summary.json',{});pressure=read(R/'pressure_localization.json',{})
proposal=read(R/'M04_design_proposal.json',{});exports=read(R/'flow_visualization_provenance.json',{});snapshots=read(R/'selected_snapshots.json',{})
snapshot_label='; '.join(m+' '+v.get('status','')+' t = '+fmt(v.get('time_s'),3)+' s' for m,v in snapshots.items())
pilot={m:rows(Q/(m+'_GPU')/'F18_dt1000us_long/history.csv') for m in ['M02','M03']}
latest={m:pilot[m][-1] for m in pilot};histories={m:list(pilot[m]) for m in pilot}
status_rows=[];mesh_rows=[];pilot_rows=[];window_rows=[]
sim_links={}
configured_live=__import__('configured_mesh_panel').snapshot()
def simulation_link(mesh,job):
 folder=R/job['id'] if job else None
 choices=[]
 if folder:
  choices.append(folder/'final.sim')
  checkpoint=read(folder/'latest_checkpoint.json',{})
  for value in checkpoint.values():
   if isinstance(value,str) and value.endswith('.sim'):choices.append(Path(value) if Path(value).is_absolute() else folder/value)
  choices.append(folder/'restart_prepared.sim')
 choices.append(Q/mesh/'mesh.sim')
 path=next((p for p in choices if p.is_file()),None)
 if path is None:return '<span class="muted">Preparing</span>'
 sim_links[mesh]={'path':str(path),'url':path.as_uri(),'file':path.name}
 return '<a class="local-sim-link" data-sim-mesh="'+mesh+'" href="'+esc(path.as_uri())+'" title="'+esc(str(path))+'">'+esc(path.name)+'</a><button type="button" class="copy-sim-path" data-copy-sim="'+esc(str(path))+'" aria-label="Copy '+mesh+' simulation path">Copy path</button>'
brockett=2*math.pi*(1-.83*.12)*(math.radians(0)+2.05*.025)
buoyancy=22.718189111947265/(.5*1000*18**2*.0238)
brockett_rows=[]
for m in [c['id'] for c in read(R/'campaign_registry.json',{}).get('cases',[])]:
 matching=[j for j in jobs if j['id'].startswith(m+'_')]
 histories.setdefault(m,[])
 for j in matching:histories[m]+=rows(R/j['id']/'history.csv')
 if histories[m]:latest[m]=histories[m][-1]
 a=live.get('meshes',{}).get(m,{})
 j=matching[-1] if matching else {}
 result=read(R/j['id']/'controller_result.json',{}) if j else {}
 complete=result.get('completed',{}).get('status')=='stabilized' or bool(j and read(R/j['id']/'acceptance.json',{}).get('status')=='settled')
 status='Settled' if complete else ('Running' if state.get('active')==j.get('id') else ('Review required' if result.get('status')=='needs_review' else 'Queued'))
 if m not in pilot and not j:status='Meshing' if not (Q/m/'measurement.json').exists() else ('Mesh repair' if read(Q/m/'measurement.json',{}).get('metrics',{}).get('NegativeVolumeCells',0)>0 else 'Ready for GPU')
 if state.get('active')==j.get('id') and j and not (R/j['id']/'history.csv').exists():status='Initializing flow' if j.get('initialize') else 'Loading checkpoint'
 last=latest.get(m,{})
 if m=='M09':
  cjobs=[x for x in configured_live.get('jobs',[]) if x.get('mesh')==m]
  active_cfg=next((x for x in cjobs if x['id']==configured_live.get('state',{}).get('active')),None)
  candidate_cfg=next((x for x in cjobs if x.get('result')),None)
  selected_cfg=candidate_cfg or active_cfg
  if selected_cfg:
   pr=selected_cfg.get('progress',{})
   last={'physical_time_s':pr.get('time_s'),'CD':pr.get('CD'),'CL_total':pr.get('CL_total')}
   status=('Guarded startup' if 'startup' in selected_cfg['id'] else selected_cfg['status'])+' · separate SO screen'
   complete=bool(candidate_cfg)
 shifts=a.get('window_mean_shift_pct',{})
 delta=lambda k:fmt(shifts.get(k),3)+'%' if k in shifts else 'Pending'
 metric=read(Q/m/'measurement.json',{}).get('metrics',{});topo=read(Q/m/'topology_audit.json',{})
 status_rows.append('<tr><td><b>'+m+'</b><span class="sub">'+str(metric.get('cell_count',j.get('cells','—')))+' cells</span></td><td>'+status+'</td><td>'+fmt(last.get('physical_time_s'),3)+' s</td><td>'+fmt(last.get('CD'),6)+'</td><td>'+fmt(last.get('CL_total'),6)+'</td><td>'+delta('CD')+'</td><td>'+delta('CL_total')+'</td><td>'+('Pass' if complete else 'In progress')+'</td><td>'+simulation_link(m,j)+'</td></tr>')
 if shifts:window_rows.append('<tr><td>'+m+'</td><td>'+delta('CD')+'</td><td>'+delta('CL_total')+'</td><td>'+('Settled' if complete else 'Continuing')+'</td></tr>')
 if a.get('windows'):
  win=a['windows'][-1];dynamic=win['CL_total']['mean']-buoyancy
  brockett_rows.append('<tr><td>'+m+'</td><td>'+fmt(win['start'],3)+'–'+fmt(win['end'],3)+' s</td><td>'+fmt(dynamic,6)+'</td><td>'+fmt(100*(dynamic/brockett-1),2)+'%</td><td>'+('Settled' if complete else 'Provisional')+'</td></tr>')
 if m in pilot:
  v=pilot[m][-1];y=yp.get(m,{})
  pilot_rows.append('<tr><td><b>'+m+'</b></td><td>'+fmt(v['Fx_slice_N'],3)+'</td><td>'+fmt(v['Fz_slice_N'],3)+'</td><td>'+fmt(v['CD'],6)+'</td><td>'+fmt(v['CL_total'],6)+'</td><td>'+fmt(v.get('foil_mean_yplus'),2)+'</td><td>'+fmt(v.get('foil_max_yplus'),2)+'</td></tr>')
 mesh_rows.append('<tr><td><b>'+m+'</b></td><td>'+str(metric.get('cell_count','—'))+'</td><td>'+fmt(metric.get('min_cell_quality'),4)+'</td><td>'+fmt(metric.get('min_volume_change'),4)+'</td><td>'+fmt(metric.get('max_skewness_angle_deg'),2)+'°</td><td>'+fmt(100*topo.get('area_fraction_at_least_15_quad_layers',0),2)+'%</td><td>'+('Yes' if topo.get('single_layer_topology') else 'Pending')+'</td></tr>')

dif=100*(pilot['M02'][-1]['CD']/pilot['M03'][-1]['CD']-1)
delta_p=pressure.get('M02',{}).get('reconstructed_drag_N',95.34209)-pressure.get('M03',{}).get('reconstructed_drag_N',55.1264)
leadshare=None
if False: # Historic pilot localization is reported separately.
 leadshare=100*sum(pressure['M02']['force_bins'][k]['pressure_drag_N']-pressure['M03']['force_bins'][k]['pressure_drag_N'] for k in ['LE_0_1pct','1_5pct'])/delta_p
stamp=datetime.datetime.now().astimezone().strftime('%d %b %Y · %H:%M:%S CET')
active=state.get('active','No active case') if state.get('status')=='running' else state.get('status','Prepared').replace('_',' ').title()
from live_tests_panel import snapshot as test_snapshot, panel as test_panel
active_tests=test_snapshot()
from campaign_dashboard import sections
mesh_section,settled_table=sections(live)
historical_mesh_section=__import__('mesh_convergence').html_section().replace('<h2>Mesh convergence and selection</h2>','<h2>Historical first-order mesh comparison</h2>')
historical_mesh_section=re.sub(r'<div class="callout">.*?</div>','<div class="callout">Historical first-order results are retained below. <a href="#selected-mesh-time-live">Current calm-template decision and second-order time-step check</a> are reported separately.</div>',historical_mesh_section,count=1,flags=re.S)
templates={
'@@WAVE_PLAN@@':__import__('wave_scope_panel').panel(),
'@@LIVE_TESTS@@':__import__('configured_mesh_panel').panel()+('<details><summary>Completed M04 calculation-setting tests</summary>'+test_panel(active_tests)+'</details>' if (R/'calm_solver_configuration_decision.json').exists() else test_panel(active_tests)),
'@@PAUSE_NOTE@@':'<div class="callout"><b>Paused.</b> Saved states are ready.<details><summary>Resume command · Desktop Commander</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere"><code>Start-Process -FilePath \'C:\\Python315\\python.exe\' -ArgumentList \'F:\\ntnu\\mesh_screening_20261028\\force_stabilization_20261029\\resume_campaign.py\',\'--resume\' -WindowStyle Hidden -PassThru</code></pre></details></div>' if state.get('status')=='paused_for_shutdown' else '',
'@@WALL_DESIGN@@':__import__('wall_design').html_section(),'@@MESH_SELECTION@@':historical_mesh_section,'@@CAMPAIGN_MESH@@':mesh_section,'@@SETTLED_TABLE@@':settled_table,
'@@SCHEMATIC@@':'<svg viewBox="0 0 510 335" role="img" aria-label="NACA 66-012 section, chord 1.19 m, 2 m below calm free surface" xmlns="http://www.w3.org/2000/svg">\n<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#354956"/></marker></defs>\n<rect x="22" y="55" width="465" height="259" fill="#f1f5f7"/><path d="M22 55H487" stroke="#354956" stroke-width="1.5"/>\n<g fill="#263b48" font-family="Arial,sans-serif" font-size="14"><text x="28" y="40">Calm free surface · z = +2.00 m</text><text x="452" y="40">Air</text><text x="433" y="81">Water</text>\n<path d="M266.850,285.000 L266.750,284.990 L266.574,284.969 L266.146,284.913 L265.754,284.855 L265.010,284.735 L264.086,284.570 L263.372,284.433 L262.164,284.187 L261.270,283.994 L259.802,283.663 L258.193,283.282 L257.045,283.002 L255.220,282.545 L253.936,282.217 L251.917,281.691 L249.791,281.130 L248.319,280.738 L246.020,280.164 L244.438,279.752 L241.992,279.127 L239.446,278.507 L237.709,278.108 L235.060,277.527 L233.264,277.152 L230.528,276.611 L227.748,276.096 L225.873,275.768 L223.033,275.301 L221.122,275.012 L218.229,274.620 L215.304,274.288 L213.337,274.104 L210.359,273.877 L208.355,273.755 L205.322,273.608 L202.260,273.501 L200.205,273.450 L197.113,273.405 L195.049,273.395 L191.955,273.409 L188.867,273.457 L186.815,273.509 L183.752,273.614 L181.721,273.702 L178.701,273.861 L175.716,274.051 L173.750,274.194 L170.841,274.432 L168.931,274.607 L166.114,274.892 L163.361,275.203 L161.564,275.424 L158.931,275.776 L157.221,276.022 L154.725,276.409 L152.320,276.816 L150.768,277.097 L148.523,277.534 L147.084,277.834 L145.016,278.295 L143.061,278.765 L141.824,279.081 L140.069,279.560 L138.965,279.883 L137.408,280.370 L135.974,280.863 L135.093,281.189 L133.896,281.667 L133.186,281.972 L132.253,282.409 L131.479,282.834 L131.050,283.120 L130.539,283.560 L130.288,283.859 L130.044,284.305 L129.997,284.451 L129.968,284.594 L129.958,284.734 L129.966,284.871 L130.000,285.000 L130.049,285.124 L130.102,285.247 L130.165,285.368 L130.241,285.485 L130.330,285.600 L130.681,285.926 L130.988,286.123 L131.564,286.383 L132.026,286.533 L132.839,286.735 L133.804,286.925 L134.535,287.055 L135.760,287.256 L136.658,287.392 L138.113,287.593 L139.685,287.785 L140.797,287.910 L142.560,288.092 L143.799,288.211 L145.754,288.385 L147.817,288.554 L149.251,288.662 L151.483,288.816 L153.024,288.913 L155.410,289.050 L157.882,289.178 L159.575,289.258 L162.178,289.369 L163.953,289.437 L166.671,289.531 L169.449,289.613 L171.332,289.661 L174.198,289.723 L176.134,289.758 L179.072,289.799 L182.044,289.829 L184.041,289.841 L187.053,289.847 L189.070,289.844 L192.105,289.827 L195.145,289.795 L197.173,289.765 L200.211,289.708 L202.229,289.660 L205.238,289.574 L208.218,289.470 L210.187,289.387 L213.115,289.236 L215.050,289.114 L217.930,288.893 L220.783,288.632 L222.669,288.443 L225.475,288.145 L227.329,287.942 L230.082,287.636 L232.794,287.330 L234.575,287.129 L237.199,286.834 L238.911,286.648 L241.428,286.395 L243.899,286.168 L245.509,286.029 L247.852,285.805 L249.371,285.689 L251.563,285.526 L253.645,285.377 L254.967,285.289 L256.845,285.173 L258.025,285.107 L259.677,285.027 L261.180,284.970 L262.094,284.944 L263.327,284.922 L264.054,284.918 L264.993,284.924 L265.746,284.942 L266.142,284.957 L266.573,284.980 L266.750,284.992 L266.850,285.000 Z" fill="#1b303e" stroke="#1b303e" stroke-width=".6"/>\n<path d="M32 285H105" stroke="#354956" marker-end="url(#arrow)"/><text x="30" y="270">U = 18 m/s</text>\n<path d="M370 58V282" stroke="#354956" marker-start="url(#arrow)" marker-end="url(#arrow)"/><text x="385" y="177">h = 2.00 m</text>\n<path d="M130 307H267" stroke="#354956" marker-start="url(#arrow)" marker-end="url(#arrow)"/><text x="145" y="328">c = 1.19 m</text><text x="127" y="254">NACA 66-012 · α = 0°</text><text x="127" y="232">a = 0.8 · f/c = 0.025</text>\n<path d="M113 285H350" stroke="#82939c" stroke-dasharray="3 4"/><text x="290" y="302">z = 0</text></g></svg>',
'@@BROCKETT@@':fmt(brockett,6),'@@BROCKETT_ROWS@@':''.join(brockett_rows),'@@STAMP@@':stamp,'@@ACTIVE@@':esc(active),'@@STATUS_ROWS@@':''.join(status_rows),'@@PILOT_ROWS@@':''.join(pilot_rows),'@@MESH_ROWS@@':''.join(mesh_rows),
'@@WINDOW_ROWS@@':''.join(window_rows) or '<tr><td colspan="4">Two complete 0.2 s windows are not yet available.</td></tr>',
'@@DRAG_GAP@@':fmt(dif,1),'@@LE_SHARE@@':'97.7','@@M03_TIME@@':fmt(latest['M03']['physical_time_s'],3),
'@@FORCE_CHART@@':image('force_history.png','Continuation from t = 0.2 s, shown on fitted coefficient scales. Instantaneous measured values; no smoothing.'),
'@@FORCE_DETAILS@@':image('force_components.png','Pressure and viscous drag on the 20 mm slice, plus interface CFL during continuation.'),
'@@FORCE_JS@@':(R/'force_explorer.js').read_text(encoding='utf-8'),
'@@FLOW_CHART@@':image('flow_streamlines_pressure.png',snapshot_label+'. Instantaneous streamlines from saved velocity vectors. Common colour scales; solid foil masked. Startup fields are replaced on acceptance of a settled result.'),
'@@PRESSURE_CHART@@':image('pressure_localization.png',snapshot_label+'. Surface pressure and integrated pressure drag from each saved solution. Force reconstruction is checked against its corresponding STAR report.'),
'@@YPLUS_CHART@@':image('yplus_history_distribution.png','Measured wall y+ histories from t = 0.2 s to the latest available sample. Axes extend automatically as the runs progress.'),
'@@SPATIAL_YPLUS@@':image('yplus_spatial_m04.png',snapshot_label+'. Actual wall values and mesh layers.'),
'@@YPLUS_DISTRIBUTION@@':image('yplus_distribution.png',snapshot_label+'. Exact boundary-face area weighting.'),
'@@MESH_CHART@@':image('mesh_detail_comparison.png','Edges are read directly from the source-plane CGNS connectivity. Each mesh contains exactly one cell through the span. The sharp trailing edge is the main location of incomplete regular-layer coverage.'),
'@@DATA@@':json.dumps({'wave_scope':read(R/'wave_extension_plan.json',{}),'active_tests':active_tests,'simulation_links':sim_links,'histories':histories,'snapshot':live,'yplus':yp,'M04_proposal':proposal,'flow_provenance':exports,'mesh_comparison':read(R/'mesh_convergence.json',{}),'wall_design_review':read(R/'wall_design_review_20261029.json',{}),'mesh_budget_cfl':read(R/'mesh_budget_cfl.json',{}),'mesh_optimization_evidence':read(R/'mesh_optimization_evidence.json',{}),'mesh_definition_evidence':read(R/'mesh_definition_evidence.json',{}),'temporal_settings':read(R/'temporal_settings_audit.json',{})},ensure_ascii=True).replace('</','<\\/')}
page=r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NTNU | Quasi-2D Hydrofoil Evidence</title>
<style>
:root{--ink:#142e3d;--muted:#5e7180;--line:#dce5ea;--navy:#102d40;--teal:#187b73;--orange:#bf5a28;--paper:#f3f6f8}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 "Segoe UI",Arial,sans-serif}a{color:var(--teal)}button{font:inherit}
.hero{background:var(--navy);color:#fff;padding:48px max(5vw,24px) 34px}.hero-inner,main,.nav-inner{max-width:1280px;margin:auto}.eyebrow{font-size:12px;letter-spacing:2.2px;text-transform:uppercase;color:#84d4c8;font-weight:700}.hero h1{font-size:clamp(30px,4vw,48px);line-height:1.13;letter-spacing:-1.3px;margin:14px 0}.hero p{color:#c3d7e1;max-width:780px;font-size:17px}.hero-bottom{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-top:26px}.hero small{color:#b4cad5}.tag{padding:6px 11px;background:#233e50;border-radius:5px;font-size:12px;font-weight:600}.tag.warning{background:#634c27;color:#ffe6b5}
nav{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);box-shadow:0 2px 10px #183b4d08}.nav-inner{display:flex;gap:5px;align-items:center;overflow-x:auto;padding:10px 16px}nav a{white-space:nowrap;padding:9px 13px;text-decoration:none;color:var(--muted);border-radius:6px;font-weight:600;font-size:13px}nav a:hover,nav a.active{background:#e7f3f0;color:#155c54}.refresh{margin-left:auto;white-space:nowrap;font-size:12px;background:#fff;border:1px solid var(--line);padding:7px 11px;border-radius:6px;color:var(--muted);cursor:pointer}
main{padding:28px 20px 60px}section{scroll-margin-top:78px;margin:0 0 34px}.section-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;margin:28px 0 15px}.section-head h2{margin:0;font-size:25px;line-height:1.25;letter-spacing:-.4px}.section-head p{margin:4px 0 0;color:var(--muted)}.index{color:var(--teal);font-size:12px;font-weight:800;letter-spacing:1.5px;display:block;margin-bottom:7px}
.card{min-width:0;background:white;border:1px solid var(--line);border-radius:10px;padding:24px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.kpi small{display:block;color:var(--muted);font-size:12px}.kpi strong{display:block;font-size:30px;line-height:1.2;margin:10px 0 6px;letter-spacing:-.6px}.kpi span{font-size:12px;color:var(--muted)}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.callout{border-left:4px solid var(--teal);background:#eaf4f1;border-radius:5px;padding:17px 20px;margin:18px 0}.callout.amber{border-color:#bd893d;background:#fff6e8}.callout p{margin:3px 0}.card h3{font-size:17px;margin:0 0 10px}.muted{color:var(--muted)}.sub{display:block;color:var(--muted);font-size:12px;font-weight:400}.pill{display:inline-block;font-size:11px;text-transform:uppercase;letter-spacing:.7px;font-weight:700;padding:5px 8px;background:#edf1f4;border-radius:4px;white-space:nowrap}.pill.green{background:#dff1e9;color:#18664d}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:13px}th{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);text-align:left;white-space:nowrap}th,td{border-bottom:1px solid #e6ecef;padding:13px 11px}td{white-space:nowrap}tr:last-child td{border-bottom:0}.bar{height:4px;width:130px;background:#e2e9ed;margin-top:6px;border-radius:4px}.bar i{display:block;height:100%;background:var(--teal);border-radius:4px}.pipeline{display:flex;gap:8px;flex-wrap:wrap;margin:15px 0 22px}.pipeline span{padding:8px 12px;border:1px solid var(--line);background:#fff;border-radius:5px;font-size:12px}.pipeline .current{border-color:#68a99e;background:#eaf4f1}
figure{margin:18px 0;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}figure img{display:block;width:100%;height:auto}figcaption{padding:15px 22px;border-top:1px solid #e8eef1;color:var(--muted);font-size:12px;line-height:1.6}.pending{padding:40px;border:1px dashed #a8bac4;background:#fff;color:var(--muted);border-radius:10px}.formula{font-family:Georgia,serif;font-size:20px;margin:14px 0}.specs{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.spec{padding:16px;background:#f5f8fa;border-radius:6px}.spec b{display:block;font-size:23px}.spec small{color:var(--muted)}ul{padding-left:20px}li{margin:7px 0}details{background:#fff;border:1px solid var(--line);padding:16px 20px;border-radius:7px;margin:14px 0}summary{cursor:pointer;font-weight:600}details p{color:var(--muted)}.btn{border:1px solid var(--line);background:white;color:var(--ink);border-radius:6px;padding:9px 14px;cursor:pointer;font-weight:600;font-size:12px}.btn:hover{background:#edf5f2}.downloads{display:flex;gap:9px;flex-wrap:wrap;margin:16px 0}.footer{color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:20px}code{font-size:12px;overflow-wrap:anywhere}dt{font-weight:600}dd{margin:0 0 12px;color:var(--muted)}
@media(max-width:850px){.cards,.specs{grid-template-columns:repeat(2,minmax(0,1fr))}.kpi strong{font-size:24px}.hero-bottom .tag{max-width:100%}.grid2,.grid3{grid-template-columns:minmax(0,1fr)}.hero{padding-top:32px}.card{padding:18px}.refresh{margin-left:8px}.section-head{align-items:flex-start;flex-direction:column}}
@media print{nav,.refresh,.downloads{display:none}.hero{background:#fff;color:#142e3d;padding:20px}.hero p,.hero small{color:#526674}figure,.card{break-inside:avoid}body{background:white}main{max-width:none}}
.chart-toolbar{display:flex;gap:8px;flex-wrap:wrap}.chart-toolbar button[aria-pressed="true"]{background:#126b62;color:white;border-color:#126b62}.force-chart{border:1px solid var(--line);border-radius:10px;background:white;margin:18px 0;overflow:hidden;min-width:0}.chart-heading{padding:18px 22px 0;display:flex;justify-content:space-between;gap:12px;align-items:center}.chart-heading h3{font-size:20px;margin:0}.chart-heading small{font-size:12px;font-weight:400;color:var(--muted)}.chart-values{padding:10px 22px 3px;display:flex;gap:26px;flex-wrap:wrap;font-size:18px;font-variant-numeric:tabular-nums}.chart-values small{font-size:12px;color:var(--muted)}.force-chart svg{display:block;max-width:100%;touch-action:pan-y}.chart-readout{padding:8px 22px 14px;font-size:13px;min-height:42px;color:var(--muted);font-variant-numeric:tabular-nums}figure img{cursor:zoom-in}figure:after{content:"Click image to enlarge";display:block;font-size:11px;color:var(--teal);padding:0 22px 12px}#imageViewer{width:96vw;max-width:1800px;max-height:95vh;border:0;border-radius:10px;padding:16px;background:white}#imageViewer::backdrop{background:#081d2dde}.viewer-controls{display:flex;gap:8px;justify-content:flex-end;margin-bottom:12px}.viewer-scroll{overflow:auto;max-height:80vh}.viewer-scroll img{display:block;width:100%;height:auto}.viewer-scroll img.original-size{width:auto;max-width:none}
@media(max-width:600px){.chart-heading{padding:16px 14px 0}.chart-heading h3{font-size:18px}.chart-heading small{display:block}.chart-values{padding:10px 14px;font-size:16px;gap:12px}.chart-readout{padding:8px 14px 12px}.hero h1{font-size:32px}}
/* Minimal engineering presentation */
:root{--ink:#182b36;--muted:#52636d;--line:#cfd7dc;--paper:#fff;--teal:#126b62}
body{background:#fff;font-size:14px}.hero{background:#fff;color:var(--ink);padding:20px max(3vw,20px);border-bottom:1px solid var(--line)}.hero h1{font-size:28px;letter-spacing:0;margin:0 0 18px}.hero p,.hero small{color:var(--muted)}.hero .case-meta{font-size:15px;line-height:1.9}.engineering-header{display:grid;grid-template-columns:1fr 480px;align-items:center;gap:30px}.section-schematic svg{display:block;width:100%;height:auto;max-height:310px}
nav{box-shadow:none}.nav-inner{padding:6px 12px}nav a{border-radius:0}main{padding-top:18px}.index,.pipeline{display:none}.section-head h2{font-size:22px;letter-spacing:0}.card,figure,details,.force-chart{border-radius:0;box-shadow:none}.card{padding:18px}.kpi strong{font-size:24px}.callout{border-radius:0;background:#f5f7f8;border-color:#71828d}.callout.amber{background:#f5f7f8;border-color:#71828d}.cards{gap:10px}.btn{border-radius:2px}.pill{border-radius:0}.section-head{margin-top:22px}.hero-bottom,.eyebrow{display:none}
@media(max-width:850px){.engineering-header{grid-template-columns:1fr}.section-schematic{max-width:480px}.hero{padding:20px}.hero h1{font-size:26px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}

</style></head><body>
<header class="hero"><div class="hero-inner engineering-header"><div><h1>Quasi-2D hydrofoil</h1><p class="case-meta">NACA 66-012 · 18 m/s · α = 0°<br>Chord 1.19 m · submergence 2.00 m<br>SST k–ω · VOF · STAR-CCM+ 2602</p><small>Updated @@STAMP@@</small></div><div class="section-schematic">@@SCHEMATIC@@</div></div></header>
<nav><div class="nav-inner"><a href="file:///F:/ntnu/mesh_screening_20261028/professor_dashboard.html" title="Local research review on this computer">Research review · local ↗</a><a href="#overview">Overview</a><a href="#live-tests">Live tests</a><a href="#mesh">Mesh campaign</a><a href="#mesh-selection">Mesh comparison</a><a href="#forces">Forces</a><a href="#validation">Brockett</a><a href="#flow">Flow fields</a><a href="#wall">Wall resolution</a><a href="#method">Method & sources</a><button class="refresh" id="refreshToggle">Auto-refresh: on</button></div></nav>
<main>
<section id="overview"><div class="section-head"><div><span class="index">01 / CAMPAIGN STATE</span><h2>Campaign status</h2><p>Force settling, near-wall resolution and mesh refinement at 18 m/s.</p></div></div>

@@PAUSE_NOTE@@
@@LIVE_TESTS@@
<div class="card"><h3>Run state and force settling</h3><p class="muted" style="overflow-wrap:anywhere">Campaign queue: <b>@@ACTIVE@@</b>. GPU solves run sequentially. Calm-force settling uses changes below 0.5% in both coefficients over adjacent 0.2 s windows; wave-pilot checks are reported separately.</p><div class="table-wrap"><table><thead><tr><th>Mesh</th><th>Status</th><th>Physical time</th><th>Latest CD</th><th>Latest CL</th><th>Δ mean CD</th><th>Δ mean CL</th><th>Settling</th><th>Local simulation</th></tr></thead><tbody>@@STATUS_ROWS@@</tbody></table></div><p class="muted">Simulation links point to saved files on this computer. Use Copy path if the browser does not open the file.</p></div>
<div class="callout amber"><p><b>Historical first-order settings:</b> Δt = 1 ms, 20 inner iterations. Current second-order settings and the supported calm template are reported in Live tests.</p></div>
</section>
@@CAMPAIGN_MESH@@
@@MESH_SELECTION@@
<section id="forces"><div class="section-head"><div><span class="index">02 / HYDRODYNAMIC LOADS</span><h2>Forces, drift and pressure-drag origin</h2><p>CL includes buoyancy. Forces in newtons refer to the 20 mm slice.</p></div><div class="downloads"><button class="btn" onclick="downloadHistory('M03')">Download M03 history</button><button class="btn" onclick="downloadHistory('M02')">Download M02 history</button></div></div>
@@SETTLED_TABLE@@
<div id="forceExplorer">
<div class="chart-toolbar" role="group" aria-label="Time range"><button class="btn" data-force-range="continuation" aria-pressed="true">Continuation · from 0.2 s</button><button class="btn" data-force-range="recent" aria-pressed="false">Latest common 0.4 s</button><button class="btn" data-force-range="startup" aria-pressed="false">Full startup</button></div>
<p id="forceRangeNote" class="muted"></p>
<div class="force-chart" id="cdChart"><div class="chart-heading"><h3>Drag coefficient, CD</h3><button class="btn svg-download">Save SVG</button></div><div class="chart-values"></div><svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Drag coefficient history"></svg><div class="chart-readout"></div></div>
<div class="force-chart" id="clChart"><div class="chart-heading"><h3>Lift coefficient, CL <small>includes buoyancy</small></h3><button class="btn svg-download">Save SVG</button></div><div class="chart-values"></div><svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Lift coefficient history"></svg><div class="chart-readout"></div></div>
</div>
<details><summary>Force components and interface CFL</summary>@@FORCE_DETAILS@@</details>
<details><summary>Static force figure for export</summary>@@FORCE_CHART@@</details>
<div class="grid2"><div class="card"><h3>Settling screen</h3><p class="muted">Compare two adjacent 0.2 s windows. Require mean CD and CL changes below 0.5%. The solver stops at the first passing evaluation. RMS and within-window drift remain diagnostics. This tests force settling, not mesh or time-step independence.</p><div class="table-wrap"><table><thead><tr><th>Mesh</th><th>Mean CD change</th><th>Mean CL change</th><th>Assessment</th></tr></thead><tbody>@@WINDOW_ROWS@@</tbody></table></div></div>
<div class="card"><h3>Original pilot comparison · t = 0.2 s</h3><p><b>98.7%</b> of the pilot total-drag difference comes from the pressure component. About <b>@@LE_SHARE@@%</b> of that pressure-drag difference accumulates in the first <b>5% of the chord</b>.</p><p class="muted">This localizes the discrepancy near the leading edge. It does not prove a unique cause. Wall-normal refinement and a separate leading-edge mesh check should be evaluated independently.</p></div></div>
<details><summary>Archived startup comparison · t = 0.2 s</summary><div class="card" style="margin-top:18px"><div class="table-wrap"><table><thead><tr><th>Mesh</th><th>Drag [N]</th><th>Lift [N]</th><th>CD</th><th>CL total</th><th>Mean y+</th><th>Max y+</th></tr></thead><tbody>@@PILOT_ROWS@@</tbody></table></div><p class="muted">Both snapshots use Δt = 1 ms, first-order time integration and the same force normalization. They are completed startup tests, not converged reference cases.</p></div></details>
@@PRESSURE_CHART@@
</section>
<section id="validation"><div class="section-head"><h2>Brockett comparison</h2></div>
<div class="card"><div class="formula">CL,B = 2π (1 − 0.83 t/c) (α + 2.05 f/c) = <b>@@BROCKETT@@</b></div>
<p>α = 0 rad · t/c = 0.12 · f/c = 0.025. CFD comparison uses <b>CL,dynamic = CL,total − 0.00589226</b>, subtracting the nominal 22.7182 N buoyancy of this slice.</p>
<div class="table-wrap"><table><thead><tr><th>Mesh</th><th>Averaging window</th><th>Mean CL,dynamic</th><th>Difference from Brockett</th><th>Status</th></tr></thead><tbody>@@BROCKETT_ROWS@@</tbody></table></div>
<p class="muted">Engineering cross-check for lift. Brockett's correlation describes the TMB-modified NACA 66 thickness form and a = 0.8 camber. This reconstructed section has a sharp trailing edge; the CFD also includes the free surface at h/c = 1.68. Agreement is not independent validation of drag, wave forces or numerical accuracy.</p>
<p class="muted"><a href="https://dome.mit.edu/bitstream/handle/1721.3/49032/DTMB_1966_1780.pdf?isAllowed=y&amp;sequence=1">T. Brockett, DTMB Report 1780 (1966), equation (2), printed p. 5.</a></p></div></section>
<section id="flow"><div class="section-head"><div><span class="index">03 / COMPLETED FLOW SNAPSHOTS</span><h2>Streamlines and pressure fields</h2><p>Saved at the accepted settling time for each mesh. Each panel states its time and status; colour limits and camera extent are shared.</p></div></div>
@@FLOW_CHART@@
<div class="grid3"><div class="card"><h3>What the lines show</h3><p class="muted">Instantaneous streamlines integrated from the saved x and z velocity components. White arrows indicate flow direction around the fixed foil.</p></div><div class="card"><h3>What the colours show</h3><p class="muted">Speed and pressure coefficient with nominal hydrostatic pressure removed. The free surface is 2 m above the foil and outside this local view.</p></div><div class="card"><h3>How this was obtained</h3><p class="muted">Fields are exported from the final saved solution. Settled panels use the timestamp at which the force criterion was accepted.</p></div></div>
</section>
<section id="wall"><div class="section-head"><div><span class="index">04 / NEAR-WALL RESOLUTION</span><h2>Near-wall resolution</h2><p>Measured wall y+ and layer coverage for the completed solutions.</p></div></div>
<p>SST k–ω with All y+ Wall Treatment. Siemens recommends y+ below 1 or above 30; minimize cells in the buffer layer. The distributions below use the saved timestamps shown in their captions.</p>
@@WALL_DESIGN@@
@@YPLUS_CHART@@
@@YPLUS_DISTRIBUTION@@
@@SPATIAL_YPLUS@@
</section>

<section id="method"><div class="section-head"><div><span class="index">06 / REPRODUCIBILITY & LIMITS</span><h2>Read the numbers in their proper context</h2></div></div>
<div class="grid2"><div class="card"><h3>Reference quantities</h3><dl><dt>Flow and geometry</dt><dd>U = 18 m/s in +X; lift in +Z; chord 1.19 m; span 0.02 m; foil held at its existing incidence; calm water level z = +2 m.</dd><dt>Normalization</dt><dd>ρ = 1000 kg/m³; Sref = 0.0238 m²; qS = 3855.6 N. Divide slice force by 0.02 m to obtain N/m.</dd><dt>Buoyancy</dt><dd>CL total includes hydrostatic lift. Nominal buoyancy is 22.7182 N; use an explicitly documented subtraction when reporting dynamic lift.</dd></dl><div class="formula">CD = D / (½ρU²Sref) &nbsp; · &nbsp; CL = L / (½ρU²Sref)</div></div>
@@WAVE_PLAN@@</div>
<details><summary>Primary sources and technical interpretation</summary><p><b>Siemens STAR-CCM+ 2602 User Guide:</b> “Setting up a Wall Treatment”, installed help page GUID-70D648E4-1172-43E5-8F45-C8D92F12D814. All-y+ recommends y+ &lt; 1 or y+ &gt; 30; low-y+ targets y+ &lt; 1, with limited faces below 5 accepted. First-layer thickness provides an approximate linear adjustment to y+.</p><p><a href="https://nasa.github.io/CFL3D/Cfl3dv6/cfl3dv6_testcases.html#flatplateyplus">NASA CFL3D: flat plate with minimum y+ effect</a>. Its SST results demonstrate sensitivity of skin friction and drag to wall-normal spacing. This supports checking low-y+ resolution; it is not a validation of this STAR hydrofoil model.</p><p><a href="https://community.sw.siemens.com/s/article/How-Wall-Roughness-is-modelled-in-Simcenter-STAR-CCM">Siemens: wall-law regimes and blended wall treatment</a>.</p></details>
<details><summary>Recovery and handover</summary><p>The run directory is <code>F:\\ntnu\\mesh_screening_20261028\\force_stabilization_20261029</code>. Each case records its input hash, process ID, live CSV, progress, resource samples and an explicit completion result. Checkpoint files are written every 500 steps. The original pilot simulations are preserved.</p><p>To request a graceful stop, create <code>STOP_ALL</code> in the run directory, or <code>STOP</code> in the active case directory. To recover after an interruption, inspect <code>latest_checkpoint.json</code>, confirm the old process is no longer active, and create a new attempt ID with the correct restart time. Do not reuse a directory containing an existing history.</p><p>This HTML contains its charts, styles and downloadable force histories. It opens offline and can be copied as a single file. Live updates appear only while the local controller continues to regenerate this file.</p></details>
<div class="downloads"><button class="btn" onclick="downloadJSON()">Download evidence snapshot</button><button class="btn" onclick="window.print()">Print / save as PDF</button></div>
<div class="footer">NTNU · Quasi-2D hydrofoil · Updated @@STAMP@@<br>Preliminary computational evidence. No finite-span tip effects, induced drag of the full foil, waves, flap motion or FSI are represented in these pilot results.</div>
</section></main>
<dialog id="imageViewer" aria-label="Enlarged chart"><div class="viewer-controls"><button class="btn" id="fitImage">Fit to window</button><button class="btn" id="actualImage">Original size</button><button class="btn" id="closeImage">Close ×</button></div><div class="viewer-scroll"><img alt=""></div></dialog>
<script id="evidence" type="application/json">@@DATA@@</script>
<style>.copy-sim-path{display:block;border:0;background:none;color:#345d72;padding:5px 0;font-size:11px;cursor:pointer}.local-sim-link{white-space:nowrap}#shared-mesh-settings dl{display:grid;grid-template-columns:minmax(140px,1fr) 2fr;gap:10px 20px}#shared-mesh-settings dt,#shared-mesh-settings dd{margin:0;text-transform:none;letter-spacing:0}@media(max-width:600px){#shared-mesh-settings dl{grid-template-columns:1fr;gap:6px}#shared-mesh-settings dd{margin-bottom:12px}}</style>
<script>
document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-copy-sim]');if(!button)return;
 const path=button.dataset.copySim;
 try{
  if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(path);
  else{const field=document.createElement('textarea');field.value=path;field.style.position='fixed';field.style.opacity='0';document.body.appendChild(field);field.select();const ok=document.execCommand('copy');field.remove();if(!ok)throw new Error('copy unavailable');}
  button.textContent='Copied';setTimeout(()=>button.textContent='Copy path',1500);
 }catch(error){button.textContent='Select path';window.prompt('Copy the simulation path:',path);}
});
const evidence=JSON.parse(document.getElementById('evidence').textContent);
function saveFile(name,text,type){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
function downloadHistory(mesh){const rows=evidence.histories[mesh];const keys=['physical_time_s','CD','CL_total','Fx_slice_N','Fz_slice_N','pressure_drag_N','viscous_drag_N','mean_yplus','foil_mean_yplus'];saveFile(mesh+'_force_history.csv',keys.join(',')+'\n'+rows.map(r=>keys.map(k=>r[k]??'').join(',')).join('\n'),'text/csv')}
function downloadJSON(){saveFile('NTNU_evidence_snapshot.json',JSON.stringify(evidence,null,2),'application/json')}
let enabled=sessionStorage.getItem('ntnuRefresh')!=='off';const toggle=document.getElementById('refreshToggle');
function label(){toggle.textContent='Auto-refresh: '+(enabled?'on':'paused')}label();
toggle.onclick=()=>{enabled=!enabled;sessionStorage.setItem('ntnuRefresh',enabled?'on':'off');label()};
const scrollSaved=sessionStorage.getItem('ntnuScroll');if(scrollSaved&&!location.hash)window.scrollTo(0,Number(scrollSaved));
setInterval(()=>{if(enabled&&!document.hidden){sessionStorage.setItem('ntnuScroll',String(window.scrollY));location.reload()}},30000);
const observer=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id))}},{rootMargin:'-10% 0px -70% 0px'});
document.querySelectorAll('main section').forEach(s=>observer.observe(s));
@@FORCE_JS@@
</script></body></html>"""
for key,value in templates.items():page=page.replace(key,value)
assert '@@' not in page
page=__import__('operational_dashboard_layout').transform(page)
for out in [R.parent/'dashboard.html',R/'dashboard.html']:
 tmp=out.with_suffix('.en.'+str(os.getpid())+'.tmp');tmp.write_text(page,encoding='utf-8');tmp.replace(out)
(R/'dashboard_build.json').write_text(json.dumps({'updated_at':stamp,'bytes':len(page.encode()),'embedded_pngs':page.count('data:image/png;base64,'),'self_contained':True,'language':'en'},indent=2))
print('English dashboard built: '+str(len(page))+' characters')
