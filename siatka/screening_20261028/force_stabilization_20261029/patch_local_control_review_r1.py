from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'local_control_worker.py';s=p.read_text()
s=s.replace('class Halt(RuntimeError):pass','''class Halt(RuntimeError):pass
class Cancelled(Halt):pass
def ensure_not_cancelled(j):
 if m.read(D/'jobs'/j['id']/'job.json').get('status')=='cancelled':raise Cancelled('Cancelled before next phase')''')
s=s.replace(" s=j['spec'];t0=source.get('physical_time_s',0);token=uuid.uuid4().hex"," ensure_not_cancelled(j)\n s=j['spec'];t0=source.get('physical_time_s',0);token=uuid.uuid4().hex")
s=s.replace(" while not safe_ready():\n  if pause():", " while not safe_ready():\n  ensure_not_cancelled(j)\n  if pause():")
s=s.replace(" if pause():raise Halt('Queue paused')\n calm=", " ensure_not_cancelled(j)\n if pause():raise Halt('Queue paused')\n calm=")
s=s.replace("   prepared=domain.prepare(s,j['id'],lambda text,path:status(j,text,status='preparing',preparation_directory=path))","   ensure_not_cancelled(j)\n   prepared=domain.prepare(s,j['id'],lambda text,path:status(j,text,status='preparing',preparation_directory=path))")
s=s.replace("   except BaseException as ex:stop_report(j,e.redact(str(ex)));break","   except Cancelled:\n    j=m.read(D/'jobs'/j['id']/'job.json');status(j,'Cancelled; no next phase launched',status='cancelled')\n   except BaseException as ex:stop_report(j,e.redact(str(ex)));break")
p.write_text(s,encoding='utf-8');compile(s,p.name,'exec')
# Scope the caption to the actual continuation, preserving source provenance.
p=R/'plot_wave_side_view.py';s=p.read_text().replace("'Fresh calm-start calculated field' if calm","('Computed calm continuation from t = '+str(state.get('source_time_s',0))+' s; no reinitialization') if calm")
p.write_text(s,encoding='utf-8');compile(s,p.name,'exec')
print('Cancellation gates and current calm lineage corrected')
