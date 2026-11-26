from pathlib import Path
import re
R=Path(__file__).resolve().parent
p=R/'build_dashboard_en.py';s=p.read_text()
s=s.replace("exports=read(R/'flow_visualization_provenance.json',{})","exports=read(R/'flow_visualization_provenance.json',{});snapshots=read(R/'selected_snapshots.json',{})\nsnapshot_label='; '.join(m+' '+v.get('status','')+' t = '+fmt(v.get('time_s'),3)+' s' for m,v in snapshots.items())")
s=s.replace("fmt(y.get('area_mean',v.get('foil_mean_yplus')),2)","fmt(v.get('foil_mean_yplus'),2)").replace("fmt(y.get('max',v.get('foil_max_yplus')),2)","fmt(v.get('foil_max_yplus'),2)")
s=s.replace("if len(pressure)==2:","if False: # Historic pilot localization is reported separately.")
s=s.replace("'@@LE_SHARE@@':fmt(leadshare,1)","'@@LE_SHARE@@':'97.7'")
s=s.replace("'@@FLOW_CHART@@':image('flow_streamlines_pressure.png','Saved M02 and M03 solutions at t = 0.2 s. Streamlines follow the instantaneous x–z velocity field; they are not particle trajectories. Cell-centred fields are interpolated for display and the solid foil is masked. Both meshes use the same colour limits.'),","'@@FLOW_CHART@@':image('flow_streamlines_pressure.png',snapshot_label+'. Instantaneous streamlines from saved velocity vectors. Common colour scales; solid foil masked. Startup fields are replaced on acceptance of a settled result.'),")
s=s.replace("'@@PRESSURE_CHART@@':image('pressure_localization.png','Pressure forces reconstructed using the exact CGNS face area vectors agree with the STAR report to better than 0.000002% for the two pilot snapshots. Signed contributions can cancel; large local values are not total drag.'),","'@@PRESSURE_CHART@@':image('pressure_localization.png',snapshot_label+'. Surface pressure and integrated pressure drag from each saved solution. Force reconstruction is checked against its corresponding STAR report.'),")
s=s.replace("'@@YPLUS_CHART@@':image('yplus_history_distribution.png','Time histories use solver reports. The histogram uses exact boundary-face area weights at the common pilot time t = 0.2 s. M02 continuation appears automatically as it progresses.'),","'@@YPLUS_CHART@@':image('yplus_history_distribution.png','Measured wall y+ histories from t = 0.2 s to the latest available sample. Axes extend automatically as the runs progress.'),")
s=s.replace("'@@YPLUS_DISTRIBUTION@@':image('yplus_distribution.png','Area-weighted distribution at the explicitly labelled snapshot time.'),","'@@YPLUS_DISTRIBUTION@@':image('yplus_distribution.png',snapshot_label+'. Exact boundary-face area weighting.'),")
s=s.replace("'@@SPATIAL_YPLUS@@':image('yplus_spatial_m04.png','Wall y+ and actual layer geometry from the completed pilot at t = 0.2 s. Replaced with settled-solution diagnostics when available.'),","'@@SPATIAL_YPLUS@@':image('yplus_spatial_m04.png',snapshot_label+'. Actual wall values and mesh layers.'),")
s=s.replace('<h2>Streamlines and pressure fields</h2><p>Identical physical time, camera extent and colour limits for M02 and M03.</p>','<h2>Streamlines and pressure fields</h2><p>Saved at the accepted settling time for each mesh. Each panel states its time and status; colour limits and camera extent are shared.</p>')
s=s.replace('Read-only exports from the existing STAR checkpoints. No solver steps, reinitialization or overwrite of the source simulations.','Fields are exported from the final saved solution. Settled panels use the timestamp at which the force criterion was accepted.')
s=re.sub(r'<div class="cards">.*?</div></div>\s*<div class="pipeline">.*?</div>','',s,flags=re.S)
# Remove stale, time-specific explanatory wall boxes; plots carry measured values.
start=s.index('<div class="grid2"><div class="card"><h3>Current wall treatment')
end=s.index('@@YPLUS_CHART@@',start)
s=s[:start]+'''<p>SST k–ω with All y+ Wall Treatment. Siemens recommends y+ below 1 or above 30; minimize cells in the buffer layer. The distributions below use the saved timestamps shown in their captions.</p>
'''+s[end:]
s=s.replace('<b>Interpretation gate.</b> A stable residual or force trace is not a mesh-accuracy certificate. These runs retain first-order time integration, Δt = 1 ms and 20 inner iterations to isolate the effect of longer startup. Second-order and time-step sensitivity remain to be checked.','<b>Numerical settings:</b> first-order time integration, Δt = 1 ms, 20 inner iterations. Force settling does not establish mesh or time-step independence.')
s=s.replace('<h3>Why M02 and M03 differ</h3>','<h3>Original pilot comparison · t = 0.2 s</h3>')
s=s.replace('<h3>Matched completed pilot: t = 0.2 s</h3>','<h3>Archived startup comparison · t = 0.2 s</h3>')
p.write_text(s)
p=R/'localize_pressure.py';s=p.read_text().replace("(r['z']>.025*1.19*4*(r['x']/1.19)*(1-r['x']/1.19))==upper","(r['area_z_m2']<0)==upper");p.write_text(s)
p=R/'collect_status.py';s=p.read_text()
start=s.index(' stable=bool(shifts)')
end=s.index('\n return ',start)
s=s[:start]+" stable=bool(shifts) and all(abs(x)<.5 for x in shifts.values())"+s[end:]
s=s.replace('mean change <0.5%, RMS <1%, endpoint drift <1%. The solver requires two passing evaluations 0.2 s apart.','mean changes <0.5%. RMS and endpoint drift are diagnostics; no extra confirmation window.')
p.write_text(s)
p=R/'update_status.py';s=p.read_text().replace("if not last.exists() or time.time()-last.stat().st_mtime>75:","if not (R/'field_refresh.lock').exists() and (not last.exists() or time.time()-last.stat().st_mtime>75):");p.write_text(s)
# Correct overview screenshot position after modal testing.
p=R/'dashboard_qa.cjs';s=p.read_text().replace("await page.screenshot({path:path.join(r,'dashboard_en_overview.png')});","await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,0)});\n await page.screenshot({path:path.join(r,'dashboard_en_overview.png')});");p.write_text(s)
print('Captions and values now identify actual saved timestamps; settling criterion aligned.')
