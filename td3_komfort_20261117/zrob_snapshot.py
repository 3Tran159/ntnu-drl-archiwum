"""zrob_snapshot.py - wersja dashboardu na telefon: dane wklejone do jednego pliku HTML (bez serwera). Wynik: TD3K_SNAPSHOT.html"""
import json, time
from pathlib import Path
H = Path(__file__).parent
html = (H / "TD3K_LIVE.html").read_text(encoding="utf-8")
data = {}
for tag in ("TD3K_WA1.5", "TD3K_WA0"):
    for f in ("STATUS.json", "train_log.csv", "eval.csv", "demo_ep.json", "live_ep.json"):
        p = H / "runs" / tag / f
        if p.exists(): data[f"runs/{tag}/{f}"] = p.read_text(encoding="utf-8")
for s in ("S1", "S2", "S3", "S4"):
    for f in (f"viz_{s}.json", f"res_{s}.json"):
        p = H / "seas" / f
        if p.exists(): data[f"seas/{f}"] = p.read_text(encoding="utf-8")
old = 'async function get(u,txt){try{const r=await fetch(u+"?"+Date.now(),{cache:"no-store"});if(!r.ok)return null;return txt?await r.text():await r.json()}catch(e){return null}}'
assert old in html
new = ('const SNAP=' + json.dumps(data) + ';\nasync function get(u,txt){const s=SNAP[u];if(s==null)return null;return txt?s:JSON.parse(s)}')
html = html.replace(old, new).replace("Refreshes every 10 s.", "Snapshot of " + time.strftime("%d %b %H:%M") + " (phone version, no live refresh).")
(H / "TD3K_SNAPSHOT.html").write_text(html, encoding="utf-8")
print(len(html))
