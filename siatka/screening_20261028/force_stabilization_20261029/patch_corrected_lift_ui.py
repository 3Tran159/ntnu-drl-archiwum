from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
def rep(a,b):
 global s
 if a not in s:raise RuntimeError('Missing '+a[:100])
 s=s.replace(a,b,1)
rep(' return points,errors+warnings\n\ndef _recent_cost',''' return _correct_points(points,folder),errors+warnings

def _reference(folder):
 try:
  import force_reference
  return force_reference.correction_for_case(folder)
 except (ImportError,OSError,ValueError):return {'available':False,'reason':'Audited force reference unavailable'}

def _correct_points(points,folder):
 import force_reference
 ref=_reference(folder);out=[]
 for p in points:
  v=force_reference.correct_row({'CL_total':p[2],'Fz_slice_N':p[4]},ref)
  out.append((p[0],p[1],v.get('CL'),p[3],p[4]))
 return out

def _correction_notice(folder):
 ref=_reference(folder)
 if not ref.get('available'):return '<p class="wcp-empty"><b>Corrected CL unavailable.</b> '+_e(ref.get('reason','No audited reference'))+'. Raw CL_total remains in the unchanged source CSV.</p>'
 s='<p class="wcp-meta"><b>CL excludes nominal buoyancy.</b> CL = (Fz − '+_f(ref['buoyancy_N'],6)+' N) / '+_f(ref['reference_force_N'],3)+' N; offset '+_f(ref['cl_offset'],9)+'. CD is unchanged. Raw CL_total remains in the source CSV. '+_link(ref['provenance_file'],'Force-reference audit')+'.</p>'
 raw,_=_history([{'path':str(Path(folder)/'history.csv')}])
 if raw:s+='<details><summary>Raw lift and correction</summary><p>Latest raw CL_total = '+_f(raw[-1][2],9)+' at t = '+_f(raw[-1][0])+' s. Historical decisions based on raw total lift are preserved.</p></details>'
 return s

def _recent_cost''')
rep('def _cycle_display(points,assessment,period):','def _cycle_display(points,assessment,period,cl_key="CL_total"):')
rep(" series={'CD':[samples[t][1] for t in times],'CL_total':[samples[t][2] for t in times]}"," series={'CD':[samples[t][1] for t in times],cl_key:[samples[t][2] for t in times]}")
a=s.index('def _cycle_display(');b=s.index('\ndef _decimate',a)
part=s[a:b].replace("for key in ('CD','CL_total'):","for key in ('CD',cl_key):").replace('def _cycle_overlay_html(points,assessment,period):','def _cycle_overlay_html(points,assessment,period,corrected=False):').replace(" view=_cycle_display(points,assessment,period);"," cl_key='CL' if corrected else 'CL_total'\n view=_cycle_display(points,assessment,period,cl_key);").replace("('CL_total','CL, total',2)","(cl_key,'CL, buoyancy subtracted' if corrected else 'CL, total',2)").replace("('CL_total','ΔCL, total [–]')","(cl_key,'ΔCL [–]' if corrected else 'ΔCL, total [–]')")
s=s[:a]+part+s[b:]
rep(" for key,label in [('CD','CD'),('CL_total','CL, total')]:"," lift_key='CL' if 'CL' in changes or 'CL' in check.get('means',{}) else 'CL_total'\n for key,label in [('CD','CD'),(lift_key,'CL, buoyancy subtracted' if lift_key=='CL' else 'CL_total · historical raw')]:")
rep(" s+='</tbody></table></div>'\n if check:s+="," s+='</tbody></table></div>'\n if lift_key=='CL_total' and check:s+='<p class=\"wcp-meta\">This saved decision used raw total lift. The newly displayed CL history and rolling comparison subtract audited nominal buoyancy; the historical decision is unchanged.</p>'\n if check:s+=")
# The two current-stage renderers now consume corrected tuple values; legacy renderer stays explicit raw.
a=s.index('def _render_inlet_wave(');b=s.index('\ndef render(',a)
part=s[a:b]
part=part.replace("('CL_total','CL, total',2)","('CL','CL, buoyancy subtracted',2)")
part=part.replace("'CL_total':[(p[0],p[2])","'CL':[(p[0],p[2])")
part=part.replace("s+=_cycle_overlay_html(points,a,period)","s+=_cycle_overlay_html(points,a,period,corrected=True)")
part=part.replace(" s+='<h3>Current inlet-wave case"," s+=_correction_notice(folder)\n s+='<h3>Current inlet-wave case")
part=part.replace(" s+='<h3>Current C01"," s+=_correction_notice(folder)\n s+='<h3>Current C01")
part=part.replace("Case-matched repeatability status: '+_e(assessment.get('status','Assessment pending'))","Corrected-CL repeatability status: '+_e(assessment.get('status','Assessment pending') if assessment.get('CL_definition')=='buoyancy_subtracted' else 'Pending corrected assessment; any earlier raw-CL decision is preserved')")
# Apply correction independently to current-only window history; do not merge resumed history into its stop screen.
part=part.replace(" points,_=_history([{'path':str(folder/'history.csv')}]);times=[p[0] for p in points]"," points,_=_history([{'path':str(folder/'history.csv')}]);points=_correct_points(points,folder);times=[p[0] for p in points]")
part=part.replace("  prefix=[0.]\n  for row in points:prefix.append(prefix[-1]+row[index])","  prefix=[0.];invalid=[0]\n  for row in points:\n   prefix.append(prefix[-1]+(row[index] or 0.));invalid.append(invalid[-1]+int(row[index] is None))")
part=part.replace("and gaps[i]-gaps[max(0,lo-1)]==0","and gaps[i]-gaps[max(0,lo-1)]==0 and invalid[i+1]==invalid[lo]")
part=part.replace("This is the same mean-change definition used by the C01 stopping test.","CL is buoyancy-subtracted. Historical raw-CL stopping records are retained separately; new corrected-CL checks use this definition.")
s=s[:a]+part+s[b:]
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
print('Wave/calm display corrected CL integrated; raw CSV and historical decisions retained.')
