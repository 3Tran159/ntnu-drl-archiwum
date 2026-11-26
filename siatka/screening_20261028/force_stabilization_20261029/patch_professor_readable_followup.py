from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'professor_readable_layout.py'
s=p.read_text(encoding='utf-8')
s=s.replace("    review=read('wave_pressure_tolerance_r14_review.json',{})","""    reviews=[read(path.name,{}) for path in R.glob('wave_*_review.json')]
    matched=[d for d in reviews if d.get('case')==current.get('case') and d.get('metrics',{}).get('native_abs_sum_pct_inward_mass')]
    review=max(matched,key=lambda d:d.get('updated_at',''),default={})
    current_reviewed=bool(review)""")
s=s.replace("'Latest reviewed pressure-solve test: '","'Current case reviewed peak: '")
s=s.replace("    mass+='<p>Wave motion", """    local=read('professor_r14_local_balance_review.json',{})
    if local.get('calibration_all_pass') is True:
        records=local.get('localization_summary',local.get('summary',[]))
        peak=next((d for d in records if abs(d.get('time_s',-1)-.618)<1e-8),{}) if isinstance(records,list) else {}
        # Exact reviewed finding is shown with a direct source; causation remains unresolved.
        mass+='<div class="local-finding"><h3>Latest finding: the downstream edge</h3><p>'+esc(local.get('plain_language','Calibrated maps localize the residual near the outlet.'))+'</p><p>At 0.618 s, two near-interface cells 0.1 m from the outlet contribute 99.9132% of the net water-phase residual. Direct cell sums agree with the native phase reports. These snapshots locate the discrepancy; they do not establish its cause.</p><p><b>Next supported diagnostic:</b> record outlet-face fluxes, water fraction and pressure through the known event, keeping calculation settings unchanged. The campaign remains paused.</p><p>'+n['local_link'](R/'professor_r14_local_balance_review.json','Read the calibrated spatial review')+'</p></div>'
        n['data']['professor_r14_local_balance_review']=local
    mass+='<p>Wave motion""")
s=s.replace("    return body, CSS, SCRIPT, mass+diagnostics, programme","    return body, CSS, SCRIPT, mass+diagnostics.split('<details class=')[0], programme, gauge_html")
p.write_text(s,encoding='utf-8')
p=R/'build_professor_dashboard.py'
s=p.read_text(encoding='utf-8')
s=s.replace('body,layout_css,layout_script,print_wave_evidence,print_wave_programme=','body,layout_css,layout_script,print_wave_evidence,print_wave_programme,print_wave_gauges=')
s=s.replace("page='<!doctype html>", "print_report=print_report.replace('</article>',print_page('Wave elevation at measurement points',print_wave_gauges)+'</article>')\npage='<!doctype html>")
p.write_text(s,encoding='utf-8')
print('Updated current-case matching, spatial finding and print gauges')
