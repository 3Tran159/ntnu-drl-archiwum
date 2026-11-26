from pathlib import Path
import subprocess,json
p=Path(r"F:\ntnu\phase2_012_20261029")
r=Path(r"F:\ntnu\mesh_screening_20261028")
# Keep the phase-1 dashboard as an archive rather than refreshing its old figures.
f=r/"night_20261028/update_dashboard.py";s=f.read_text(encoding="utf-8")
s=s.replace("    atomic_text(root/'phase1_dashboard.html',html)","    if not (root/'phase1_dashboard.html').exists():atomic_text(root/'phase1_dashboard.html',html)")
f.write_text(s,encoding="utf-8")
chrome=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
result=subprocess.run([str(chrome),"--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check","--user-data-dir="+str(p/"qa_browser_profile"),"--dump-dom",(p/"dashboard.html").as_uri()],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=40)
html=result.stdout
checks={"chrome_exit":result.returncode,"bytes":len(html),"phase2_title":"Etap 2.0" in html,"stage0":"H0_0ms" in html,"stage18":"F18_18ms" in html,"work_log":"Dziennik pracy etapu 2.0" in html,"svg_plots":html.count("<svg"),"legacy_chart_table_absent":"Measured meshes" not in html}
(p/"dashboard_qa.json").write_text(json.dumps(checks,indent=2))
assert result.returncode==0 and all(checks[k] for k in ["phase2_title","stage0","stage18","work_log","legacy_chart_table_absent"]),checks
print(json.dumps(checks))
