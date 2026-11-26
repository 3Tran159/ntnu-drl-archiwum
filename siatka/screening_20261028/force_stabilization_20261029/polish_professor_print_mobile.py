from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'build_professor_dashboard.py';s=p.read_text(encoding='utf-8')
s=s.replace("return '<figure class=\"field\"><img loading=\"lazy\" alt=\"'+esc(caption)+'\" src=\"data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'\"><figcaption>'+caption+'</figcaption></figure>'","return '<figure class=\"field\"><button class=\"expand-field\" type=\"button\">Expand figure</button><div class=\"figure-scroll\" tabindex=\"0\" role=\"region\" aria-label=\"Scrollable field figure\"><img loading=\"lazy\" alt=\"'+esc(caption)+'\" src=\"data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'\"></div><figcaption>'+caption+'</figcaption></figure>'")
s=s.replace("force=bars(sorted(mesh,key=lambda r:r['id']))","force='<div class=\"chart-scroll\" tabindex=\"0\" role=\"region\" aria-label=\"Scrollable drag chart\">'+bars(sorted(mesh,key=lambda r:r['id']))+'</div>'")
s=s.replace("cost=svg_plot(mesh,'cells','wall_s_per_step_median','Cells [thousands]','Median computing time / step [s]',2,True)","cost='<div class=\"chart-scroll\" tabindex=\"0\" role=\"region\" aria-label=\"Scrollable timing chart\">'+svg_plot(mesh,'cells','wall_s_per_step_median','Cells [thousands]','Median computing time / step [s]',2,True)+'</div>'")
s=s.replace("lineage+='<details><summary>Chronological", "lineage+='<details class=\"chronology\"><summary>Chronological")
insert="""# Compact print lineage deliberately omits repeated force means.
lineage+='<div class="lineage-print"><div><h3>Mesh-design relationships</h3><p><b>Wall-function:</b> M02 → M03 → M05<br>Surface and bulk refinement.</p><p>↓ M03 → M04: near-wall spacing changed</p><p><b>Low y+:</b> M04 → M06 → M07<br>Wall-normal, surface and bulk refinement.</p><p><b>M06 surface/bulk + M07 prisms → M08</b><br>Isolate wall-normal resolution at lower cell count.</p><p><b>M08 → M09</b><br>Coarsen remote domain; retain foil/free-surface/prism controls.</p><p>Dashed next option: M10 local LE/TE design.</p></div><div><h3>Saved-state relationships</h3><p><b>M04 checkpoint at t = 1.642 s</b></p><p>↓ Four independent branches</p><p>T01: first-order / 1 ms / 20 inner<br>T02: second-order / 1 ms / 20 inner<br>T03: second-order / 0.5 ms / 20 inner<br>T04: second-order / 1 ms / 10 inner</p><p>All compared over 2.042–2.242 s.</p><p><b>T02 final → two mass-balance probes</b><br>20 versus 10 inner; 40 steps at 1 ms.</p><p><b>Decision sequence</b><br>Calculation settings → matched mesh screen → C01 / W01 / W02 → extra waves.</p></div></div>'
"""
anchor="# Temporal matched comparisons and original reference."
assert s.count(anchor)==1;s=s.replace(anchor,insert+anchor)
s=s.replace("body=decision_html","body='<p class=\"mobile-hint\">Wide tables and figures can be scrolled horizontally. Use Expand figure for pressure and streamline details.</p>'+decision_html")
css=r'''
.lineage-print{display:none}.figure-scroll,.chart-scroll{overflow-x:auto;max-width:100%}.chart-scroll svg{display:block;width:100%;max-height:520px}.expand-field{font-size:14px;float:right;margin-bottom:10px}.figure-scroll{clear:both}.mobile-hint{display:none}
dialog{border:1px solid #8da2af;padding:0;max-width:96vw;width:96vw;height:92vh;max-height:92vh;background:white;color:var(--ink)}dialog::backdrop{background:#142b3cbd}.dialog-controls{padding:10px 18px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;font-size:14px}.dialog-scroll{overflow:auto;height:calc(100% - 60px);padding:16px}.dialog-scroll img{display:block;min-width:1100px;width:100%;height:auto}
@media(max-width:900px){.mobile-hint{display:block;font-size:14px;color:var(--muted);margin:16px 0}.field img{width:1100px;max-width:none;min-width:1100px}.chart-scroll svg{width:760px;min-width:760px;max-height:none}.expand-field{float:none;margin-bottom:8px}}
@media print{
body{font-size:10.5pt}.section-heading{margin-bottom:12pt}section{padding:8pt 0}h3{margin:12pt 0 6pt}p{margin:6pt 0 9pt}
td,th{padding:5pt 7pt}table{font-size:10pt}thead{display:table-header-group}.table-scroll{margin:10pt 0}
.lineage{display:none}.lineage-print{display:grid;grid-template-columns:1fr 1fr;gap:24pt;font-size:11pt;line-height:1.4}.lineage-print>div{border-top:2px solid #456578}.lineage-print h3{font-size:13pt}.lineage-print p{margin:9pt 0}
details.chronology,#numerics details{display:none!important}
#numerics .interpretation{break-inside:avoid;margin:10pt 0;padding-left:12pt}#numerics .interpretation h3{font-size:12pt}
.figure-scroll,.chart-scroll{overflow:visible}.field img{width:100%;min-width:0;max-width:100%;max-height:138mm;object-fit:contain}
.chart-scroll svg{width:100%;min-width:0;max-height:135mm}.field{break-before:page;border:0;padding-top:0;margin:0}.field:first-of-type{break-before:auto}.field figcaption{font-size:9pt}
#fields>p:last-child{font-size:9pt}.expand-field,dialog,.mobile-hint{display:none!important}
#sources details{display:block}#sources table td:first-child{font-size:8.5pt;word-break:break-word}.note{font-size:9pt}.method-note p{font-size:10pt}
}
'''
s=s.replace("body=decision_html","body=decision_html")
s=s.replace("page='<!doctype html>","CSS+="+repr(css)+"\npage='<!doctype html>")
s=s.replace("page+='<script id=\"research-evidence\"","page+='<dialog id=\"field-dialog\" aria-label=\"Expanded scientific figure\"><div class=\"dialog-controls\"><span>Scroll to inspect at full size</span><button id=\"close-field\">Close ×</button></div><div class=\"dialog-scroll\"><img alt=\"\"></div></dialog>'\npage+='<script id=\"research-evidence\"")
s=s.replace("const payload=JSON.parse","const dialog=document.querySelector('#field-dialog');document.querySelectorAll('.expand-field').forEach(btn=>btn.onclick=()=>{const src=btn.closest('figure').querySelector('img');const image=dialog.querySelector('img');image.src=src.src;image.alt=src.alt;dialog.showModal()});document.querySelector('#close-field').onclick=()=>dialog.close();\nconst payload=JSON.parse")
p.write_text(s,encoding='utf-8')
p=R/'configured_mesh_panel.py';s=p.read_text(encoding='utf-8')
s=s.replace("+'<br><small>Last saved progress '+f(active['age_s'],0)+' s ago.</small></p>'","+'<br><small>'+('Last saved progress '+f(active['age_s'],0)+' s ago.' if active['age_s'] is not None else 'Waiting for first progress record.')+'</small></p>'")
p.write_text(s,encoding='utf-8')
print('Print tree condensed; scientific figures pan and expand on small screens')
