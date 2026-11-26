from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'build_local_control_report.py';s=p.read_text(encoding='utf8')
def rep(a,b):
 global s
 if a not in s:raise RuntimeError('Missing '+a[:80])
 s=s.replace(a,b,1)
a=s.index('def rolling(');b=s.index('\ndef mean_window',a)
s=s[:a]+'''def rolling(hist,dt,window=.2):
 """Full-history corrected-CL windows with source-bound dt and strict gaps."""
 t=[x['t'] for x in hist];out={'CD':[],'CL':[]};latest={}
 if not t or not dt:return out,latest
 min_count=max(2,int(round(window/dt))-1);gap=[0];bad={k:[0] for k in out};sums={k:[0.] for k in out}
 for i,row in enumerate(hist):
  gap.append(gap[-1]+int(i>0 and not .5*dt<=t[i]-t[i-1]<=1.01*dt))
  for k in out:
   bad[k].append(bad[k][-1]+int(row.get(k) is None));sums[k].append(sums[k][-1]+(row.get(k) or 0.))
 for i,end in enumerate(t):
  if end-t[0]<2*window-1e-10:continue
  lo=bisect.bisect_right(t,end-2*window);mid=bisect.bisect_right(t,end-window);hi=i+1
  for k in out:
   good=mid-lo>=min_count and hi-mid>=min_count and bad[k][hi]==bad[k][lo] and gap[hi]==gap[max(1,lo)]
   prev=(sums[k][mid]-sums[k][lo])/(mid-lo) if mid>lo else None;cur=(sums[k][hi]-sums[k][mid])/(hi-mid) if hi>mid else None
   value=100*(cur-prev)/abs(cur) if good and cur is not None and abs(cur)>1e-12 else None
   out[k].append([end,value])
   latest[k]={'time_s':end,'previous_mean':prev,'current_mean':cur,'change_pct':value,'counts':[mid-lo,hi-mid],'windows_s':[[end-2*window,end-window],[end-window,end]]} if value is not None else None
 return out,latest
''' +s[b:]
rep("'max_speed_m_s','max_CFL','interface_CFL','pressure_drag_N','viscous_drag_N']","'max_speed_m_s','max_CFL','interface_CFL','pressure_drag_N','viscous_drag_N','Fz_slice_N']")
rep(" hist.sort(key=lambda x:x['t'])"," import force_reference\n reference=force_reference.correction_for_case(folder)\n hist=[force_reference.correct_row(row,reference) for row in hist]\n hist.sort(key=lambda x:x['t'])")
rep(" dt=n(spec.get('dt_s',setup.get('dt_s'))) or observed_dt"," dt=n(spec.get('dt_s',setup.get('dt_s')))")
rep(" if not assessment and not calm_stage and n(activation.get('wave_period_s')) and n(activation.get('analysis_origin_s')) is not None:"," historical_assessment=assessment\n if not calm_stage and reference.get('available') and n(activation.get('wave_period_s',assessment.get('period_s'))) and n(activation.get('analysis_origin_s',assessment.get('wave_clock_origin_s'))) is not None:")
rep("  assessment=cycles.evaluate([folder/'history.csv'],activation['wave_period_s'],min_cycles=4,max_cycles=20,analysis_origin_s=activation['analysis_origin_s'])","  assessment=cycles.evaluate([folder/'history.csv'],activation.get('wave_period_s',assessment.get('period_s')),min_cycles=4,max_cycles=20,analysis_origin_s=activation.get('analysis_origin_s',assessment.get('wave_clock_origin_s')),force_reference=reference)")
rep("  assessment_source='Recomputed from case-local raw history using the saved runtime period and analysis origin'","  assessment_source='Read-only corrected-CL recomputation from full case-local history, saved runtime period and analysis origin'\n elif assessment.get('CL_definition')!='buoyancy_subtracted':assessment={}")
rep("  for key in ['CD','CL_total']:","  for key in ['CD','CL']:")
rep("for k in ['CD','CL_total','pressure_drag_N','viscous_drag_N']","for k in ['CD','CL','CL_total','pressure_drag_N','viscous_drag_N']")
rep(" if identity.get('source'):links.append(filelink(identity['source'],'Continuation source .sim'))"," if reference.get('provenance_file'):links.append(filelink(reference['provenance_file'],'Buoyancy / force-reference audit'))\n if identity.get('source'):links.append(filelink(identity['source'],'Continuation source .sim'))")
rep("'history_rows':len(hist)","'force_reference':reference,'CL_definition':'buoyancy_subtracted','historical_raw_assessment':{'status':historical_assessment.get('status'),'stop_for_repeatability':historical_assessment.get('stop_for_repeatability'),'comparisons':historical_assessment.get('comparisons',{})},'history_rows':len(hist)")
rep("for k in ['CD','CL_total','max_speed_m_s','max_CFL','interface_CFL']","for k in ['CD','CL','CL_total','max_speed_m_s','max_CFL','interface_CFL']")
# Presentation uses corrected CL only. The separate raw series and historical decisions remain in JSON and details.
a=s.index('JS=r"""');b=s.index('\ndef build():',a)
part=s[a:b].replace('CL_total','CL')
part=part.replace("['Evidence class',r=>r.cohort]","['Evidence class',r=>r.cohort],['Lift definition',r=>r.force_reference.available?'Buoyancy subtracted; offset '+fmt(r.force_reference.cl_offset,9):'Corrected CL unavailable — '+r.force_reference.reason]")
part=part.replace("'Lift coefficient CL'","'Lift coefficient CL · buoyancy subtracted'")
part=part.replace("Recorded source SHA-256:","Raw latest-window CL_total: '+fmt(r.last_window_mean.CL_total,8)+'. Original raw-force decisions remain preserved in exported data. Audited buoyancy offset: '+fmt(r.force_reference.cl_offset,9)+'.</p><p class=\"note\">Recorded source SHA-256:")
s=s[:a]+part+s[b:]
rep("Both coefficients must be within ±0.5%; finite samples","CL subtracts audited nominal buoyancy. Both coefficients must be within ±0.5%; finite samples")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
print('Aggregate report corrected CL integrated.')
