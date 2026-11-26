from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
for name in ['plot_flow_fields.py','localize_pressure.py','yplus_diagnostic.py']:
 p=R/name
 if not (R/(p.stem+'_pilot_version.py')).exists():shutil.copy2(p,R/(p.stem+'_pilot_version.py'))
 s=p.read_text()
 at="sys.path.insert(0,str(Q/'deps311'))"
 s=s.replace(at,at+"\nsnapshots=json.loads((R/'selected_snapshots.json').read_text())\ncolours={'M03':'#187b73','M02':'#bf5a28','M04':'#5267ad'}\nsnapshot_label=' | '.join(m+' '+v['status']+' t='+format(v['time_s'],'.3f')+' s' for m,v in snapshots.items())")
 if name=='plot_flow_fields.py':
  s=s.replace('plt.subplots(2,2,figsize=(14,5.7)','plt.subplots(len(snapshots),2,figsize=(14,2.65*len(snapshots)+.6)')
  s=s.replace('plt.subplots(2,3,figsize=(14,7)','plt.subplots(len(snapshots),3,figsize=(14,3.1*len(snapshots)+.7)')
  s=s.replace("for row,mesh in enumerate(['M02','M03']):","for row,mesh in enumerate(snapshots):")
  s=s.replace("p=R/(mesh+'_pilot_post')/'velocity_vectors.csv'","p=Path(snapshots[mesh]['velocity'])")
  s=s.replace("if not (p.parent/'EXPORT_OK.json').exists():raise RuntimeError('Need completed vector export: '+mesh)","if not p.exists():raise RuntimeError('Need completed vector export: '+mesh)")
  s=s.replace('body=MPath(poly,closed=True)','body=MPath(np.vstack([poly,poly[0]]),closed=True)')
  s=s.replace("mesh+' - speed and instantaneous streamlines'","mesh+' · '+snapshots[mesh]['status']+' · t = '+format(snapshots[mesh]['time_s'],'.3f')+' s | Speed / streamlines'")
  s=s.replace("mesh+' - pressure coefficient field'","mesh+' · '+snapshots[mesh]['status']+' · t = '+format(snapshots[mesh]['time_s'],'.3f')+' s | Pressure coefficient'")
  s=s.replace("'time_s':.2,","'time_s':snapshots[mesh]['time_s'],'status':snapshots[mesh]['status'],")
  s=s.replace("fig.suptitle('Matched completed pilot snapshots | t = 0.2 s | U = 18 m/s\\nInstantaneous streamlines from saved velocity vectors; common colour scales')","fig.suptitle('Saved flow fields | U = 18 m/s | Common colour scales')")
 elif name=='localize_pressure.py':
  s=s.replace("for mesh,color in [('M03','#187b73'),('M02','#bf5a28')]:","for mesh in snapshots:\n color=colours[mesh]")
  s=s.replace("(Q/(mesh+'_GPU')/'F18_dt1000us_long/foil_final_fields.csv').open()","Path(snapshots[mesh]['wall']).open()")
  s=s.replace("exact={'M03':55.1264,'M02':95.34209}[mesh]","exact=snapshots[mesh]['pressure_drag_N']")
  s=s.replace("summaries[mesh]={'reconstructed_drag_N':total","summaries[mesh]={'time_s':snapshots[mesh]['time_s'],'status':snapshots[mesh]['status'],'reconstructed_drag_N':total")
  s=s.replace("'Pressure distribution at t=0.2 s'","'Surface pressure coefficient'")
  s=s.replace("fig.suptitle('Pilot M02 / M03 at t=0.2 s - pressure drag localization, diagnostic')","fig.suptitle('Pressure drag and surface pressure\\n'+snapshot_label)")
 elif name=='yplus_diagnostic.py':
  s=s.replace("for n,(mesh,color) in enumerate([('M03','#187b73'),('M02','#bf5a28')]):","for n,mesh in enumerate(snapshots):\n color=colours[mesh]")
  s=s.replace("if j['id'].startswith(mesh+'_'):hh+=live_yplus(R/j['id'])","""if j['id'].startswith(mesh+'_'):
   direct=csvrows(R/j['id']/'history.csv')
   if direct and 'min_yplus' in direct[-1]:hh += [{'time':a['physical_time_s'],'mean':a['mean_yplus'],'min':a['min_yplus'],'max':a['max_yplus']} for a in direct]
   else:hh+=live_yplus(R/j['id'])""")
  s=s.replace("rr=csvrows(pilot/'foil_final_fields.csv')","rr=csvrows(Path(snapshots[mesh]['wall']))")
  s=s.replace("(layers>=15)&(yv>1)","(layers>=(40 if mesh=='M04' else 15))&(yv>1e-8)")
  s=s.replace("'pilot_time_s':.2","'snapshot_time_s':snapshots[mesh]['time_s'],'status':snapshots[mesh]['status']")
  s=s.replace("abs(weightedmean-old[-1]['foil_mean_yplus'])","abs(weightedmean-snapshots[mesh]['mean_yplus'])")
  s=s.replace("np.arange(len(labels))+(n-.5)*.36,fractions,.36","np.arange(len(labels))+(n-(len(snapshots)-1)/2)*(.8/len(snapshots)),fractions,.8/len(snapshots)")
  s=s.replace("title='Surface distribution at t = 0.2 s'","title='Area-weighted wall y+ distribution'")
  s=s.replace("distribution.savefig(R/'yplus_distribution.png'","distribution.suptitle(snapshot_label,fontsize=10)\ndistribution.savefig(R/'yplus_distribution.png'")
  s=s.replace("ax.set_ylabel('Wall y+ at t = 0.2 s')","ax.set_ylabel('Wall y+')")
  s=s.replace("fig2.suptitle('Wall resolution and layer coverage | snapshot t = 0.2 s')","fig2.suptitle('Wall resolution and layer coverage\\n'+snapshot_label)")
 p.write_text(s)
print('Field and wall diagnostics now follow accepted saved timestamps.')
