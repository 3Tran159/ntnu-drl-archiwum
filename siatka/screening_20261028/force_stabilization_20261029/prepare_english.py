from pathlib import Path
import json
R=Path(__file__).resolve().parent
p=R/'yplus_diagnostic.py';s=p.read_text(encoding='utf-8')
replacements={
'Maksymalne y+ w czasie':'Maximum wall y+ over time','Średnie y+ ważone powierzchnią':'Area-weighted mean wall y+','Minimalne y+ w czasie':'Minimum wall y+ over time','Czas fizyczny [s]':'Physical time [s]','Linie poziome: y+=1, 5 i 30':'Reference lines: y+ = 1, 5 and 30','Udział powierzchni płata [%]':'Foil surface area [%]','Przedział Wall y+':'Wall y+ range','Rozkład po powierzchni przy t=0,2 s':'Surface distribution at t = 0.2 s',
'M02 i M03 · y+ nie spada do 1 przez samo wydłużanie obliczeń':'M02 / M03 - longer integration does not make this a y+ = 1 mesh',
'linia pionowa: restart przy 0,2 s':'vertical line: restart at 0.2 s',' góra':' upper','dół':' lower',
'Wall y+ przy t=0,2 s':'Wall y+ at t = 0.2 s','Rozkład y+ wzdłuż płata':'Wall y+ along the foil','Krawędź spływu — lokalne maksima':'Trailing edge - localized peaks',
'Rzeczywista pierwsza warstwa [µm]':'Actual first-layer thickness [µm]','Grubość warstwy z połączeń komórek':'Layer thickness from mesh connectivity',
'Szacowane y+ (stałe naprężenie ścinające)':'Estimated y+ (frozen wall shear)','Wstępny efekt 4 µm: nie jest wynikiem M04':'4 µm scaling estimate - not an M04 result',
'M04: potrzebna cienka pierwsza warstwa i kontrola jej pokrycia':'M04 design: refine the first layer and preserve its coverage',
'Skalowanie 4/179,9 to orientacja; zapadnięte warstwy przy TE wymagają osobnej poprawy':'4/179.9 scaling is illustrative; collapsed layers at the trailing edge need a separate correction',
'· skalowanie 4/179,9':'- scaled by 4/179.9'}
for a,b in replacements.items():s=s.replace(a,b)
p.write_text(s,encoding='utf-8')
old=(R/'update_status.py').read_text(encoding='utf-8')
cut=old.index('\ntr=[]')
(R/'collect_status.py').write_text(old[:cut]+'\n',encoding='utf-8')
proposal={'status':'design proposal, not meshed or run','reference':'M03','target_wall_yplus':'approximately 1 or below over the resolved foil surface','first_layer_thickness_m':3e-6,'layer_count':40,'total_prism_thickness_m':.01546,'equivalent_geometric_growth_ratio':1.1875157536,'last_layer_thickness_m':.0024437516,'rationale':'Measured M03 first-layer scaling gives approximately 3.23 to 5.86 micrometres for y+=1 over the central 90% of fully layered surface area. 3 micrometres provides a modest starting margin. Actual y+ must be remeasured.','controls':['Keep M03 tangential and outer mesh settings for the first wall-normal comparison.','Inspect and repair local layer collapse at the sharp trailing edge without changing foil geometry.','Retain SST and All y+ for the first comparison; the low-y+ branch is recovered on a sufficiently fine mesh.','Recheck mesh quality, achieved layer thickness and coverage, CFL and inner convergence before extending the solver.','Separate a later leading-edge refinement experiment from the wall-normal refinement test.'],'cost':'Cell count and runtime are unknown until meshed and benchmarked; do not multiply whole mesh cell count by the 60x first-layer reduction.'}
(R/'M04_design_proposal.json').write_text(json.dumps(proposal,indent=2))
print('English analysis labels and M04 proposal prepared')
