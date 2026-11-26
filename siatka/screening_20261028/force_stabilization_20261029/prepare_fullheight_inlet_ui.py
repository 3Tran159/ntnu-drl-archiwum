from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent;p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
s=s.replace("if state.get('case')=='W01a_W20L4_M10_inlet_wave_r1':return _render_inlet_wave(state)","if str(state.get('case','')).startswith('W01a_W20L4_M10_inlet_'):return _render_inlet_wave(state)")
s=s.replace(" stage=state.get('computation_stage','inlet_wave_loading')\n done=", " stage=state.get('computation_stage','inlet_wave_loading')\n constant=activation.get('height_mode')=='constant_full_height_from_activation' or '_inlet_fullheight_' in case\n done=",1)
s=s.replace(" elif stage=='inlet_wave_loading':headline=", " elif state.get('stop_requested') is True:headline='Save requested · preserving this attempt before the next case'\n elif stage=='inlet_wave_loading':headline=",1)
s=s.replace("elif origin is None:headline='Full inlet-wave amplitude · measuring arrival at the foil'", "elif origin is None:headline='Full-height inlet wave active · measuring arrival at the foil'",1)
old="The wave is introduced at the inlet with a smooth ramp; the interior flow was not globally reinitialized."
new="'+('The first inlet waveform uses full H = 0.5 m; no height ramp is applied.' if constant else 'The wave is introduced at the inlet with a smooth ramp.')+' The interior flow was not globally reinitialized."
assert old in s;s=s.replace(old,new,1)
s=s.replace("enumerate(('Startup','Inlet wave ramp','Wave arrival','Repeating cycles'))", "enumerate(('Startup','Full-height inlet' if constant else 'Inlet wave ramp','Wave arrival','Repeating cycles'))",1)
s=s.replace(" fraction=max(0,min(100,100*((t or start)-start)/duration))", " fraction=max(0,min(100,100*((t or start)-start)/duration))",1)
old=" s+='<div><h3>Inlet-height ramp</h3><div class=\"wcp-progress\"><span style=\"width:'+str(fraction)+'%\"></span></div><div class=\"wcp-progress-labels\"><span>Activation '+_f(start)+' s</span><span>'+_f(fraction,1)+'%</span><span>Ramp end '+_f(ramp_end)+' s</span></div><p class=\"wcp-meta\">Ramp duration '+_f(duration,6)+' s. H and T are evaluated analytic inlet-wave targets, not measured local crest-to-trough height or transported-front position.</p></div>'"
new=""" if constant:
  fraction=100 if height is not None and abs(height-.5)<1e-8 else 0
  s+='<div><h3>Full-height inlet · no ramp</h3><div class="wcp-progress"><span style="width:'+str(fraction)+'%"></span></div><div class="wcp-progress-labels"><span>Activation '+_f(start)+' s</span><span>H = 0.5 m from the first waveform</span></div><p class="wcp-meta">Constant height from activation. H and T are evaluated analytic inlet targets; the transported front and local crest-to-trough height are measured separately.</p></div>'
 else:
  s+='<div><h3>Inlet-height ramp</h3><div class="wcp-progress"><span style="width:'+str(fraction)+'%"></span></div><div class="wcp-progress-labels"><span>Activation '+_f(start)+' s</span><span>'+_f(fraction,1)+'%</span><span>Ramp end '+_f(ramp_end)+' s</span></div><p class="wcp-meta">Ramp duration '+_f(duration,6)+' s. H and T are evaluated analytic inlet-wave targets, not measured local crest-to-trough height or transported-front position.</p></div>'"""
assert old in s;s=s.replace(old,new)
s=s.replace("if ramp_end is not None and t is not None and t<ramp_end:s+=", "if not constant and ramp_end is not None and t is not None and t<ramp_end:s+=",1)
s=s.replace("'view_epoch':'inlet-wave-production-v1'", "'view_epoch':'inlet-fullheight-production-v1' if constant else 'inlet-wave-production-v1'",1)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Full-height production branch prepared; current state alone chooses the displayed case.')
