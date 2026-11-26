import json,datetime
from pathlib import Path
import manual_control_common as c
R=c.R
v=dict(status='javac_passed',compiled_at=datetime.datetime.now().astimezone().isoformat(),class_name='ManualFoilWave',java_release=17,macro_sha256=c.digest(R/'ManualFoilWave.java'),flow_runtime_validation='Not run: user paused calculations; first existing W01 r1 flow was stopped and saved. Manual variants will enforce getters and physical guards at runtime.')
(R/'manual_macro_build_receipt.json').write_text(json.dumps(v,indent=2),encoding='utf8')
p=R/'run_manual_wave.py';s=p.read_text(encoding='utf8');old=" pset=c.preset(cfg['preset']);source,sha=c.validate_source(pset)"
new=old+"\n receipt=c.read(R/'manual_macro_build_receipt.json')\n if receipt.get('status')!='javac_passed' or c.digest(R/'ManualFoilWave.java')!=receipt.get('macro_sha256'):raise RuntimeError('Manual macro changed after compilation; rebuild required.')"
assert s.count(old)==1;p.write_text(s.replace(old,new),encoding='utf8')
# Add a clear reason why Start is unavailable while the stopped interactive server is held.
p=R/'manual_control_panel.html';s=p.read_text(encoding='utf8')
old="if(s.pending?.error)msg(s.pending.error,true);}"
new="if(st.computation_active===false&&busy)msg('Paused and saved. The open STAR inspection session still owns this campaign queue. No new run will start while it remains open.');else if(s.pending?.error)msg(s.pending.error,true);}"
assert s.count(old)==1;p.write_text(s.replace(old,new),encoding='utf8')
print('Compiled macro identity recorded; paused-server status clarified.')
