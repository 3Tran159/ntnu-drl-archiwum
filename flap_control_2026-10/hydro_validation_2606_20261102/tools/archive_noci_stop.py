from pathlib import Path
import sys,json,datetime
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools'))
import night_queue as q
st=q.read(h/'NIGHT_QUEUE_STATE.json')
assert st.get('active') is None,'Active owned job: preserve STOP marker'
plist=q.processes();assert not any(p['ownedBatch'] for p in plist)
tracked=st.get('owned_processes',{})
assert not any(str(p['pid']) in tracked and p['born']==tracked[str(p['pid'])] for p in plist)
rec=st['jobs']['c0_fresh_no_continuity_init']
assert rec['state']=='failed' and rec['macro_status']['status']=='initialization_error'
source=(h.parent/'STOP_OWNED_CFD.json').resolve();assert source.parent==h.parent.resolve()
m=json.loads(source.read_text(encoding='utf8'));assert m.get('owned_job')=='c0_fresh_no_continuity_init'
target=(h/'audit'/('STOP_fresh_noci_rejected_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.json')).resolve();assert target.parent==(h/'audit').resolve();assert not target.exists()
source.rename(target)
print(json.dumps(dict(owned_processes_remaining=0,previous_job_state=rec['state'],marker_archived=str(target))))
