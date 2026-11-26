from pathlib import Path
import subprocess,json
R=Path(__file__).resolve().parent
chrome=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
p=subprocess.run([str(chrome),"--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check","--user-data-dir="+str(R/"qa_browser_profile"),"--window-size=1500,1100","--screenshot="+str(R/"dashboard_preview.png"),"--dump-dom",(R.parent/"dashboard.html").as_uri()],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=45)
s=p.stdout
checks={"browser_exit":p.returncode,"new_section":'id="force-stabilization"' in s,"prior_section":'id="quasi2d"' in s,"handover_link":"force_stabilization_20261029/START_HERE.txt" in s,"M03":"M03_FO1_dt1ms_to1p2_r1" in s,"M02":"M02_FO1_dt1ms_to1p2" in s,"source_snapshot":(R/"dashboard_before_takeover.html").exists(),"screenshot":(R/"dashboard_preview.png").exists()}
(R/"dashboard_qa.json").write_text(json.dumps(checks,indent=2))
assert p.returncode==0 and all(v for k,v in checks.items() if k!="browser_exit"),checks
print(json.dumps(checks))
