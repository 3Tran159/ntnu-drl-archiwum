from pathlib import Path
import subprocess,json
root=Path(r'F:\ntnu\mesh_screening_20261028')
chrome=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
try:
 result=subprocess.run([str(chrome),'--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--user-data-dir='+str(root/'night_20261028/dashboard_test_profile2'),'--dump-dom',(root/'dashboard.html').as_uri()],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
 html=result.stdout
 (root/'night_20261028/dashboard_rendered_dom.html').write_text(html,encoding='utf-8')
 checks={'exit':result.returncode,'bytes':len(html),'events':html.count('class="event '),'mesh_rows':html.count('D001'),'has_log':'>Dziennik pracy<' in html,'rendered_stats':'Measured meshes</span><strong>10' in html}
 print(json.dumps(checks))
except Exception as exc:print(type(exc).__name__,str(exc))
