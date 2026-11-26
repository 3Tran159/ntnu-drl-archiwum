from pathlib import Path
import csv,json
R=Path(__file__).resolve().parent;D=R/'wave_arrival_ui_qa_20261030'
s=json.loads((R/'wave_foil_run_state.json').read_text(encoding='utf-8-sig'));folder=Path(s['directory']);out={'case':s['case'],'read_only':True,'files':{}}
for name in ('startup_history.csv','history.csv'):
 p=folder/name
 with p.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 ts=[float(r['time_s']) for r in rows if r.get('time_s')]
 out['files'][name]={'rows':len(rows),'first_time_s':min(ts),'last_time_s':max(ts),'samples_before_display_start':sum(t<.2-1e-10 for t in ts)}
assert out['files']['startup_history.csv']['first_time_s']==.0005
assert out['files']['startup_history.csv']['samples_before_display_start']==40
assert out['files']['history.csv']['samples_before_display_start']>0
(D/'raw_history_preservation_review.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out))
