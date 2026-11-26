from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'build_professor_dashboard.py';s=p.read_text(encoding='utf-8')
for a,b in {
'NACA 66-012 · a=0.8 · f/c=0.025 · α=0° · chord1.19m · span20mm':'NACA 66-012 · a = 0.8 · f/c = 0.025 · α = 0° · chord 1.19 m · span 20 mm',
'U18m/s · submergence2m · waterdepth24m · VOF/SST · fixedfoil':'U = 18 m/s · submergence 2 m · water depth 24 m · VOF/SST · fixed foil',
'ρ1000kg/m³ · S0.0238m² · qS3855.6N':'ρ = 1000 kg/m³ · S = 0.0238 m² · qS = 3855.6 N',
'Both adjacent0.2s meanCD/CL changes below0.5%':'Both adjacent 0.2 s mean CD/CL changes below 0.5%',
'Both means within1% of two finer':'Both means within 1% of two finer',
'All restart from M04 at1.642s':'All restart from M04 at 1.642 s',
'matched40-step probes':'matched 40-step probes',
'second-order,1ms,10inner':'second-order, 1 ms, 10 inner',
'Historical first-order /1ms /20-inner cohort. Each mesh uses its own final0.2s window.':'Historical first-order / 1 ms / 20 inner cohort. Each mesh uses its own final 0.2 s window.',
'New second-order /1ms /10-inner cohort':'New second-order / 1 ms / 10 inner cohort',
'Final-window mean forces on the20mm slice.':'Final-window mean forces on the 20 mm slice.',
'Unconnected points: cellcount alone':'Unconnected points: cell count alone',
"snapshot at t='+num(item['time_s'],3)+'s.":"snapshot at t = '+num(item['time_s'],3)+' s.",
'Dashed next option: M10 local LE/TE design.':'Next design option: M10 local LE/TE refinement.'
}.items():s=s.replace(a,b)
p.write_text(s,encoding='utf-8')
# Keep the companion link accurate on the existing private mirror too.
p=R/'configured_mesh_panel.py';s=p.read_text(encoding='utf-8')
s=s.replace('<a href="professor_dashboard.html">Open research review for discussion</a>','<a href="file:///F:/ntnu/mesh_screening_20261028/professor_dashboard.html" title="Local file on this computer">Open local research review for discussion</a>')
p.write_text(s,encoding='utf-8')
print('Presentation copy normalized')
