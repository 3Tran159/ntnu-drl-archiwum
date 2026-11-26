from pathlib import Path
import shutil,re
R=Path(__file__).resolve().parent
p=R/'build_dashboard_en.py';s=p.read_text(encoding='utf-8')
if not (R/'build_dashboard_en_before_readability.py').exists():shutil.copy2(p,R/'build_dashboard_en_before_readability.py')
s=s.replace("'@@FORCE_CHART@@':image('force_history.png','Force histories include the original pilot and the continued solution. The vertical line marks the 0.2 s restart. Values are instantaneous; startup samples are not a settled mean.'),","'@@FORCE_CHART@@':image('force_history.png','Continuation from t = 0.2 s, shown on fitted coefficient scales. Instantaneous measured values; no smoothing.'),\n'@@FORCE_DETAILS@@':image('force_components.png','Pressure and viscous drag on the 20 mm slice, plus interface CFL during continuation.'),\n'@@FORCE_JS@@':(R/'force_explorer.js').read_text(encoding='utf-8'),")
s=s.replace('@@FORCE_CHART@@\n<div class="grid2">','''<div id="forceExplorer">
<div class="chart-toolbar" role="group" aria-label="Time range"><button class="btn" data-force-range="continuation" aria-pressed="true">Continuation · from 0.2 s</button><button class="btn" data-force-range="recent" aria-pressed="false">Latest common 0.4 s</button><button class="btn" data-force-range="startup" aria-pressed="false">Full startup</button></div>
<p id="forceRangeNote" class="muted"></p>
<div class="force-chart" id="cdChart"><div class="chart-heading"><h3>Drag coefficient, CD</h3><button class="btn svg-download">Save SVG</button></div><div class="chart-values"></div><svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Drag coefficient history"></svg><div class="chart-readout"></div></div>
<div class="force-chart" id="clChart"><div class="chart-heading"><h3>Lift coefficient, CL <small>includes buoyancy</small></h3><button class="btn svg-download">Save SVG</button></div><div class="chart-values"></div><svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Lift coefficient history"></svg><div class="chart-readout"></div></div>
</div>
<details><summary>Force components and interface CFL</summary>@@FORCE_DETAILS@@</details>
<details><summary>Static force figure for export</summary>@@FORCE_CHART@@</details>
<div class="grid2">''')
s=s.replace('</style></head>','''.chart-toolbar{display:flex;gap:8px;flex-wrap:wrap}.chart-toolbar button[aria-pressed="true"]{background:#126b62;color:white;border-color:#126b62}.force-chart{border:1px solid var(--line);border-radius:10px;background:white;margin:18px 0;overflow:hidden;min-width:0}.chart-heading{padding:18px 22px 0;display:flex;justify-content:space-between;gap:12px;align-items:center}.chart-heading h3{font-size:20px;margin:0}.chart-heading small{font-size:12px;font-weight:400;color:var(--muted)}.chart-values{padding:10px 22px 3px;display:flex;gap:26px;flex-wrap:wrap;font-size:18px;font-variant-numeric:tabular-nums}.chart-values small{font-size:12px;color:var(--muted)}.force-chart svg{display:block;max-width:100%;touch-action:pan-y}.chart-readout{padding:8px 22px 14px;font-size:13px;min-height:42px;color:var(--muted);font-variant-numeric:tabular-nums}figure img{cursor:zoom-in}figure:after{content:"Click image to enlarge";display:block;font-size:11px;color:var(--teal);padding:0 22px 12px}#imageViewer{width:96vw;max-width:1800px;max-height:95vh;border:0;border-radius:10px;padding:16px;background:white}#imageViewer::backdrop{background:#081d2dde}.viewer-controls{display:flex;gap:8px;justify-content:flex-end;margin-bottom:12px}.viewer-scroll{overflow:auto;max-height:80vh}.viewer-scroll img{display:block;width:100%;height:auto}.viewer-scroll img.original-size{width:auto;max-width:none}
@media(max-width:600px){.chart-heading{padding:16px 14px 0}.chart-heading h3{font-size:18px}.chart-heading small{display:block}.chart-values{padding:10px 14px;font-size:16px;gap:12px}.chart-readout{padding:8px 14px 12px}.hero h1{font-size:32px}}
</style></head>''')
s=s.replace('<script id="evidence"','''<dialog id="imageViewer" aria-label="Enlarged chart"><div class="viewer-controls"><button class="btn" id="fitImage">Fit to window</button><button class="btn" id="actualImage">Original size</button><button class="btn" id="closeImage">Close ×</button></div><div class="viewer-scroll"><img alt=""></div></dialog>
<script id="evidence"''')
s=s.replace('</script></body></html>','@@FORCE_JS@@\n</script></body></html>')
# Remove the proposal chapter; wall diagnostics remain as evidence.
s=re.sub(r'<div class="card"><span class="pill">Design.*?</div>\s*</section>', '</section>',s,flags=re.S)
s=s.replace('<h2>Does y+ justify an M04?</h2><p>Yes, as a controlled accuracy study — the maximum alone does not invalidate M03.</p>','<h2>Near-wall resolution</h2><p>Measured wall y+ and layer coverage for the completed solutions.</p>')
tmp=p.with_suffix('.tmp');tmp.write_text(s,encoding='utf-8');tmp.replace(p)
print('Readable force explorer and image enlargement integrated; M04 proposal card removed.')
