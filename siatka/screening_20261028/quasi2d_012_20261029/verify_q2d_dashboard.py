from pathlib import Path
import subprocess,json
p=Path(r"F:\ntnu\phase2_012_20261029")
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
subprocess.run(["python",str(p/"build_dashboard.py")],check=True,capture_output=True)
chrome=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
result=subprocess.run([str(chrome),"--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check","--user-data-dir="+str(r/"qa_browser_profile"),"--dump-dom",str((p/"dashboard.html").as_uri())],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=40)
html=result.stdout
checks={"chrome_exit":result.returncode,"html_bytes":len(html),"quasi2d_panel":'id="quasi2d"' in html,"mesh_counts":all(str(n) in html for n in [37411,66707,123256]),"force_table":"Fx wycinka" in html,"yplus_table":"y+ średnie" in html,"embedded_images":html.count("data:image/png;base64,"),"no_fetch":"fetch(" not in html,"gpu_test":all(x in html for x in ["M02_GPU","M03_GPU","M03_CPU24"]),"work_log":"Dziennik quasi-2D" in html}
(r/"dashboard_qa.json").write_text(json.dumps(checks,indent=2))
assert result.returncode==0 and all(checks[k] for k in ["quasi2d_panel","mesh_counts","force_table","yplus_table","no_fetch","gpu_test","work_log"]) and checks["embedded_images"]>=6,checks
print(json.dumps(checks))
