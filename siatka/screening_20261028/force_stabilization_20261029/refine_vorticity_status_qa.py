from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'plot_wave_vorticity_view.py';s=p.read_text(encoding='utf8')
s=s.replace("if current.get('source_sha256')==digest and", "if current.get('renderer_version')==2 and current.get('source_sha256')==digest and")
s=s.replace("format(clipped,'.2f')","format(clipped,'.3f')")
s=s.replace("{'status':'ready','case':source_case", "{'status':'ready','renderer_version':2,'case':source_case")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
s=s.replace("def _immediate_wave_progress(state,folder,t):\n s=", "def _immediate_wave_progress(state,folder,t):\n saved=_n(_read(folder/'completed.json').get('time_s')) is not None\n s=")
s=s.replace(" s+='<div class=\"wcp-stage-transition\"><div><b>1. Startup</b><small>Saving calculated state</small>", " s+='<div class=\"wcp-stage-transition\"><div><b>1. Startup</b><small>'+('Calculated state saved' if saved else 'Saving calculated state')+'</small>")
s=s.replace("and is being preserved for inlet-wave activation.</p></div><div><h3>Inlet-wave activation</h3>", "and is '+('saved' if saved else 'being preserved')+' for inlet-wave activation.</p></div><div><h3>Inlet-wave activation</h3>")
s=s.replace("<b>Save requested · wave not active yet</b>","<b>'+('State saved' if saved else 'Save requested')+' · wave not active yet</b>")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Saved transition status and vorticity clipping precision updated.')
