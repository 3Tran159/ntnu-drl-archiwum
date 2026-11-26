from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'build_local_control_report.py';s=p.read_text(encoding='utf8')
def rep(a,b):
 global s
 assert a in s,a[:90]
 s=s.replace(a,b,1)
rep(" hist=[];invalid_time=0\n for row in rows(folder/'history.csv'):",""" from live_analysis_panel import history_sources
 stage=state.get('computation_stage') or ('inlet_wave_full_amplitude' if identity.get('continuation_mode')=='wave' or identity.get('resume_wave') is True else 'calm_settling' if 'C01' in folder.name or attempt.get('stage',attempt.get('mode'))=='calm' else 'inlet_wave_full_amplitude')
 sources,lineage_warnings=history_sources({**state,'computation_stage':stage},folder)
 combined_rows={}
 for item in sources:
  for row in rows(item['path']):
   stamp=n(row.get('time_s',row.get('physical_time_s')))
   if stamp is not None:combined_rows[round(stamp,9)]=row
 hist=[];invalid_time=0
 for row in combined_rows.values():""")
rep(" accepted=bool(not failed and settled.get('status')=='calm_force_settled' and settled.get('source_unchanged') is True and settled.get('settling',{}).get('passed',settled.get('settling',{}).get('pass')) is True and Path(settled.get('file','missing')).is_file())",""" historical_accepted=bool(not failed and settled.get('status')=='calm_force_settled' and settled.get('source_unchanged') is True and settled.get('settling',{}).get('passed',settled.get('settling',{}).get('pass')) is True and Path(settled.get('file','missing')).is_file())
 source_ok=bool(identity.get('source_sha256')) and identity.get('source_sha256')==identity.get('input_sha256') and identity.get('source_is_guard_failed') is False and control.get('source_unchanged') is True
 corrected_gate=settled.get('settling',{}).get('CL_definition')=='buoyancy_subtracted' or 'CL' in settled.get('settling',{}).get('changes_pct',{})
 accepted=bool(historical_accepted and corrected_gate and reference.get('available') and source_ok and not lineage_warnings)""")
rep("assessment=cycles.evaluate([folder/'history.csv'],","assessment=cycles.evaluate([Path(item['path']) for item in sources],")
rep(" screen=bool(not failed and assessment.get('stop_for_repeatability') is True)"," screen=bool(not failed and reference.get('available') and source_ok and not lineage_warnings and assessment.get('CL_definition')=='buoyancy_subtracted' and assessment.get('stop_for_repeatability') is True)")
rep(" 'force_reference':reference,"," 'history_sources':sources,'lineage_warnings':lineage_warnings,'source_identity_verified':source_ok,'historical_raw_calm_acceptance':historical_accepted,'force_reference':reference,")
rep("Raw latest-window CL_total: ","Verified plotted history files: '+esc((r.history_sources||[]).map(x=>x.path).join('; '))+'. '+esc((r.lineage_warnings||[]).join(' '))+'</p><p class=\"note\">Raw latest-window CL_total: ")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
a=s.index('def render(');b=s.index('\ndef panel()',a)
part=s[a:b]
part=part.replace(" matching=case_matches and a.get('min_cycles')==policy.get('min_cycles',4)"," matching=case_matches and a.get('min_cycles')==policy.get('min_cycles',4)")
part=part.replace(" sources=a.get('history_sources',[])\n if points is None:points,read_errors=_history(sources)",""" from live_analysis_panel import history_sources
 folder=Path(state.get('directory',''));sources,lineage_warnings=history_sources(state,folder)
 if points is None:points,read_errors=_case_history(state,folder)
 else:points=_correct_points(points,folder)
 historical=a
 ref=_reference(folder)
 if period and ref.get('available') and not lineage_warnings:
  import wave_cycle_repeatability as cycles
  a=cycles.evaluate([Path(item['path']) for item in sources],period,min_cycles=policy.get('min_cycles',4),max_cycles=policy.get('max_cycles',20),analysis_origin_s=_n(historical.get('wave_clock_origin_s')) or 0.,force_reference=ref)
  a['case']=state.get('case')
 else:a={}
 matching=bool(a) and a.get('CL_definition')=='buoyancy_subtracted'
""")
part=part.replace("('CL_total','CL, total',2)","('CL','CL, buoyancy subtracted',2)")
part=part.replace("s+=_cycle_overlay_html(points,a,period)","s+=_cycle_overlay_html(points,a,period,corrected=True)")
part=part.replace("for k in ('CD','CL_total'):","for k in ('CD','CL'):")
part=part.replace("'CL_total':[(p[0],p[2])","'CL':[(p[0],p[2])")
part=part.replace("<th>CL, total</th>","<th>CL, buoyancy subtracted</th>")
part=part.replace("Instantaneous drag and total lift coefficients, read from the saved history.","Instantaneous drag and buoyancy-subtracted lift coefficients from the verified saved history.")
part=part.replace(" s+='<h3>Force coefficient history</h3>"," s+=_correction_notice(folder)\n s+='<h3>Force coefficient history</h3>")
s=s[:a]+part+s[b:]
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
print('Verified report lineage and corrected legacy-wave presentation applied.')
