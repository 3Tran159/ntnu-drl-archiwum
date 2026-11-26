from pathlib import Path
import re
R=Path(__file__).resolve().parent
p=R/'build_dashboard_en.py';s=p.read_text()
command="Start-Process -FilePath 'C:\\Python315\\python.exe' -ArgumentList 'F:\\ntnu\\mesh_screening_20261028\\force_stabilization_20261029\\resume_campaign.py','--resume' -WindowStyle Hidden -PassThru"
pause='<div class="callout"><b>Paused.</b> Saved states are ready.<details><summary>Resume command · Desktop Commander</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere"><code>'+command+'</code></pre></details></div>'
s=s.replace("templates={","templates={\n'@@PAUSE_NOTE@@':"+repr(pause)+" if state.get('status')=='paused_for_shutdown' else '',")
s=re.sub(r'<div class="callout"><b>Paused for transport.</b>.*?</div>','@@PAUSE_NOTE@@',s)
s=s.replace('M02 and M03 are settled. M04 and M05 are prepared for the next GPU runs.','Force settling, near-wall resolution and mesh refinement at 18 m/s.')
s=s.replace('<h1>Quasi-2D hydrofoil</h1>','<h1>Quasi-2D hydrofoil</h1>')
p.write_text(s)
# Make artifact names and comments match current stopping criterion.
p=R/'ContinueUntilSettled.java';s=p.read_text().replace('|mean change|<0.5%, RMS<1%, endpoint drift<1%; stop at the first passing evaluation. RMS and drift are diagnostic only.','|mean change|<0.5% for both CD and CL; stop at the first passing evaluation. RMS and drift are diagnostic only.');p.write_text(s)
(R/'RESUME_COMMAND.txt').write_text(command+'\n',encoding='utf-8')
print('Pause note and exact Desktop Commander resume command saved.')
