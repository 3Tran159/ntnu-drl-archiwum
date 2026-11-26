from pathlib import Path
R=Path(__file__).resolve().parent
def patch(file,old,new):
 p=R/file;s=p.read_text(encoding='utf8')
 if s.count(old)!=1:raise RuntimeError('Patch not unique '+file+' '+old[:50])
 p.write_text(s.replace(old,new),encoding='utf8')
patch('manual_control_server.py',"R=c.R;B=R.parent;ORIGIN=","R=c.R;B=R.parent/'dashboard_work_20261030';ORIGIN=")
patch('manual_control_server.py',"controllable=case is not None","controllable=case is not None and s.get('computation_active') is not False")
patch('manual_control_server.py',"computer=c.read(R/'computer_status.json')","computer=c.read(R/'control_computer_status.json')")
patch('manual_control_server.py',"if case is None or data.get('case')!=case.name:","if case is None or s.get('computation_active') is False or data.get('case')!=case.name:")
patch('manual_control_server.py',"def main():\n lock=R/'manual_control_server.lock'","""def refresh_copies():
 while True:
  try:
   import collect_control_status,build_manual_dashboard_copy
   collect_control_status.collect();build_manual_dashboard_copy.build()
  except Exception as ex:e.write(R/'manual_dashboard_copy_error.json',dict(at=e.stamp(),error=e.redact(str(ex))))
  time.sleep(25)
def main():
 lock=R/'manual_control_server.lock'""")
patch('manual_control_server.py',"threading.Thread(target=watch,daemon=True).start();server.serve_forever()","threading.Thread(target=watch,daemon=True).start();threading.Thread(target=refresh_copies,daemon=True).start();server.serve_forever()")
patch('run_manual_wave.py',"str(R/'update_status.py')","str(R/'build_manual_dashboard_copy.py')")
patch('build_manual_dashboard_copy.py',"parent.children[i]=replacement","parent.children[i]=replacement+current+(R/'manual_control_panel.html').read_text(encoding='utf8')")
patch('build_manual_dashboard_copy.py',"main.children.insert(0,notice+current+(R/'manual_control_panel.html').read_text(encoding='utf8'))","main.children.insert(0,notice)")
patch('manual_control_panel.html',"(s.stop_requested?'Stop requested — waiting for save':'Calculation active')","(st.computation_active===false?'Paused — server open for inspection':s.stop_requested?'Stop requested — waiting for save':'Calculation active')")
# Prevent obsolete idle snapshot text from suggesting another wave replay.
patch('build_manual_dashboard_copy.py',"replacement=layout.status_panel()","replacement=layout.status_panel(); replacement=re.sub(r'<p><b>Next useful work:</b>.*?</p>','<p><b>Current state:</b> see the case record and calculated-state files below. No automatic solver launch.</p>',replacement,flags=re.S)")
print('Working-copy service prepared; originals not changed.')
