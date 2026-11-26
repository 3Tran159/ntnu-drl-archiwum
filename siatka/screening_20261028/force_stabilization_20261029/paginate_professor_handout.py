from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'build_professor_dashboard.py';s=p.read_text(encoding='utf-8')
anchor="page='<!doctype html>"
insert=r'''
# Separate paginated handout uses the same numbers, with explicit page composition.
def print_page(title,content):
 return '<section class="print-page"><h2>'+title+'</h2>'+content+'</section>'
print_report='<article class="print-report">'
print_report+=print_page('Quasi-2D hydrofoil · numerical verification','<p class="print-meta">NTNU · '+esc(stamp)+'</p>'+decision_html+table(['Case definition','Value'],[
 ['Geometry','NACA 66-012 · a=0.8 · f/c=0.025 · α=0° · chord1.19m · span20mm'],
 ['Flow and domain','U18m/s · submergence2m · waterdepth24m · VOF/SST · fixedfoil'],
 ['Reference','ρ1000kg/m³ · S0.0238m² · qS3855.6N · CL includes hydrostatic lift'],
 ['Force stopping rule','Both adjacent0.2s meanCD/CL changes below0.5%'],
 ['Mesh selection','Both means within1% of two finer comparable meshes; matched settings']
 ])+'<p>Recorded numerical evidence for discussion. Wave-force validation and final mesh selection remain separate decisions.</p>')
compact=lineage[lineage.index('<div class="lineage-print">'):] if '<div class="lineage-print">' in lineage else lineage
print_report+=print_page('Experiment lineage',compact)
prt=table(['Test','Order / Δt [ms] / inner','Mean CD','Mean CL','s / step · s / physical s','State'],tr)
prt+='<h3>Matched changes · 2.042–2.242 s</h3>'+table(['Test / ref.','Change','ΔCD','ΔCL','ΔFx pressure','ΔFx viscous'],pairrows)
prt+='<p>Δ[%] = 100(test−reference)/|reference|. All restart from M04 at1.642s. Cost is measured under shared load.</p><h3>Original M04 versus continuation</h3><p>Original CD '+num(origmean.get('CD'),8)+', CL '+num(origmean.get('CL_total'),8)+'. T01 later-window change: '+pct(t1.get('difference_pct_vs_original',{}).get('CD'))+' CD / '+pct(t1.get('difference_pct_vs_original',{}).get('CL_total'))+' CL. This includes continued physical-time drift.</p>'
if cons:prt+='<p><b>Conservation:</b> matched40-step probes include mass accumulation and net outward flux. Maximum BDF2 residual/inlet: '+', '.join(c['id'].split('_')[2]+' '+f'{c["BDF2_budget_pct_of_inlet"]["max_abs_pct"]:.3g}%' for c in cons)+'. Calm-screen settings: second-order,1ms,10inner.</p>'
print_report+=print_page('Calculation settings',prt)
prm='<p>Historical first-order /1ms /20-inner cohort. Each mesh uses its own final0.2s window.</p><div class="print-plots">'+svg_plot(low,'cells','CD','Cells [thousands]','Mean CD',5)+svg_plot(low,'cells','CL_total','Cells [thousands]','Mean CL',4)+'</div>'
prm+=table(['Mesh','Wall family','Cells','Mean CD','Mean CL','Window [s]'],mr)+'<p>Unconnected points: cellcount alone does not establish a refinement path.</p>'
print_report+=print_page('Historical mesh evidence',prm)
prc=table(['Test / reference','ΔCD','ΔCL','Coefficient test'],mcomp)+'<p>M08 has one finer confirmation in this cohort. M06 has coarser wall-normal spacing than M08.</p>'
if cs.get('jobs'):prc+='<h3>New second-order /1ms /10-inner cohort</h3>'+table(['Mesh','State','Cells','Mean CD','Mean CL','Time [s]'],mr2)
prc+='<p>New results remain separate. Compare residual drift and, when needed, matched final windows before accepting a near-threshold mesh difference.</p>'
print_report+=print_page('Mesh selection · comparison and current work',prc)
prf='<div class="print-force">'+bars(sorted(mesh,key=lambda r:r['id']))+'</div>'+table(['Mesh','Fx pressure [N]','Fx viscous [N]','Fx total [N]','Viscous share'],[[r['id'],num(r['Fx_pressure_N'],3),num(r['Fx_viscous_N'],3),num(r['Fx_total_N'],3),num(100*r['Fx_viscous_N']/r['Fx_total_N'],1)+'%'] for r in sorted(mesh,key=lambda r:r['id'])])
prf+='<p>Final-window mean forces on the20mm slice. Total = pressure + viscous. Saved field snapshots are instantaneous.</p>'
print_report+=print_page('Pressure and viscous drag',prf)
print_report+=print_page('Mesh controls and measured y+',definition)
print_report+=print_page('Measured computational cost',cost)
for ident in ('M04','M07','M08'):
 item=manifest.get('meshes',{}).get(ident)
 if item:
  caption=ident+' · accepted historical first-order snapshot at t='+num(item['time_s'],3)+'s. Instantaneous velocity streamlines and Cp after subtracting nominal hydrostatic pressure. Common limits across the three cases.'
  print_report+=print_page(ident+' · pressure and streamlines',image('professor_fields_'+ident+'.png',caption))
print_report+=print_page('Wave programme · planned cases',waves)
prs='<p>Questions: does M09 retain both forces with two finer comparable references; which drag component is sensitive; and does the selected mesh retain temporal and wave-propagation accuracy?</p>'
prs+=table(['Evidence record','Local update'],[[esc(p['file']),esc(p['modified'].replace('T',' '))] for p in provenance])
prs+='<p>Exact values, paths and SHA-256 hashes are embedded in the HTML evidence download. Sources and all attempts remain preserved on disk.</p>'
print_report+=print_page('Discussion and provenance',prs)+'</article>'
CSS+=r"""
.print-report{display:none}
@media print{
body>header,body>nav,body>main,body>dialog{display:none!important}
.print-report{display:block;font:9.5pt/1.35 "Segoe UI",Arial,sans-serif;color:#000}
.print-report .print-page{break-before:auto;break-after:page;break-inside:avoid;border:0;margin:0;padding:0;scroll-margin:0}
.print-report .print-page:last-child{break-after:auto}
.print-report h2{font-size:19pt;margin:0 0 10pt;break-after:avoid}
.print-report h3{font-size:12pt;margin:10pt 0 6pt}
.print-report p{margin:7pt 0}
.print-report table{font-size:9.5pt;min-width:0;width:100%}.print-report th{font-size:9pt}
.print-report td,.print-report th{padding:3pt 6pt}.print-report .table-scroll{margin:8pt 0;overflow:visible}
.print-report .status{font-size:8.5pt;padding:2pt 4pt}
.print-report .decision{padding:8pt 0;margin-bottom:10pt}
.print-report .decision h2{font-size:13pt}.print-report .assessment-grid{gap:16pt;grid-template-columns:repeat(3,1fr)}
.print-report .assessment-grid h3{font-size:11pt}.print-report .assessment-grid p{font-size:9.5pt}
.print-report .note,.print-report figcaption{font-size:9pt}
.print-report .lineage-print{display:grid;grid-template-columns:1fr 1fr;gap:24pt;font-size:11pt}
.print-report .lineage-print p{margin:11pt 0}.print-report .lineage-print h3{font-size:13pt}
.print-report .print-plots{display:flex;gap:14pt}.print-report .print-plots svg{width:49%;height:auto;max-height:68mm}
.print-report .print-force svg{width:100%;height:auto;max-height:75mm}
.print-report .chart-scroll svg{max-height:115mm;min-width:0;width:100%}
.print-report .field{break-before:auto;margin:0;padding:0;border:0}
.print-report .field img{max-height:135mm;min-width:0;width:100%;object-fit:contain}
.print-report .two-notes{gap:18pt}.print-report .two-notes p{font-size:9.5pt}
.print-report .expand-field{display:none}.print-report .print-meta{font-size:9pt;color:#526572}
}
"""
'''
assert s.count(anchor)==1;s=s.replace(anchor,insert+anchor)
s=s.replace("page+='<script id=\"research-evidence\"","page+=print_report\npage+='<script id=\"research-evidence\"")
p.write_text(s,encoding='utf-8')
p=R/'professor_lineage.py';s=p.read_text(encoding='utf-8')
s=s.replace('<div class="lin-follow"><strong>Next design option','<div class="lin-follow lin-future"><strong>Next design option')
s=s.replace('cstatus = str(conservation.get("status","")).replace("_"," ")','cstatus = "completed" if len(conservation.get("results",[]))==2 else str(conservation.get("status","")).replace("_"," ")')
p.write_text(s,encoding='utf-8')
print('Dedicated paginated handout now uses the same measured tables and figures')
