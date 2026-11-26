from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'yplus_diagnostic.py';s=p.read_text()
s=s.replace("'font.size':10","'font.size':12")
s=s.replace("fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')","fig,hax=plt.subplots(3,1,figsize=(11,9),layout='constrained')\ndistribution,dax=plt.subplots(figsize=(11,3.4),layout='constrained')\naxes=np.array([[hax[0],hax[1]],[hax[2],dax]])")
s=s.replace("ax.plot([a['time'] for a in hh],[a[key] for a in hh]","ax.plot([a['time'] for a in hh if a['time']>=.2-1e-8],[a[key] for a in hh if a['time']>=.2-1e-8]")
s=s.replace("fig.suptitle('M02 / M03 - longer integration does not make this a y+ = 1 mesh\\n18 m/s · SST k–ω / All y+ · vertical line: restart at 0.2 s')","fig.suptitle('Wall y+ histories | t ≥ 0.2 s')\nfor ax in hax:ax.set_xlim(left=.2);ax.margins(y=.12)\ndistribution.savefig(R/'yplus_distribution.png',dpi=170);distribution.savefig(R/'yplus_distribution.svg');plt.close(distribution)")
s=s.replace("ax2[1,1].scatter(fxyz[:,0]/1.19,yv*4/179.9,s=9,color=color,label=mesh+' - scaled by 4/179.9')","ax2[1,1].scatter(fxyz[:,0]/1.19,layers,s=9,color=color,label=mesh)")
s=s.replace("ax2[1,1].axhline(1,color='#333',ls='--');ax2[1,1].axhline(5,color='#777',ls=':')","ax2[1,1].axhline(15,color='#777',ls=':')")
s=s.replace("ax2[1,1].set(ylabel='Estimated y+ (frozen wall shear)',title='4 µm scaling estimate - not an M04 result')","ax2[1,1].set(ylabel='Consecutive regular layers',title='Actual layer coverage')")
s=s.replace("fig2.suptitle('M04 design: refine the first layer and preserve its coverage\\n4/179.9 scaling is illustrative; collapsed layers at the trailing edge need a separate correction')","fig2.suptitle('Wall resolution and layer coverage | snapshot t = 0.2 s')")
p.write_text(s)
p=R/'build_dashboard_en.py';s=p.read_text()
s=s.replace("'@@SPATIAL_YPLUS@@':image('yplus_spatial_m04.png','Spatial values are from t = 0.2 s. The 4 µm panel is a frozen-shear scaling illustration, not an M04 simulation. The proposed first run uses 3 µm to provide a small margin.'),","'@@SPATIAL_YPLUS@@':image('yplus_spatial_m04.png','Wall y+ and actual layer geometry from the completed pilot at t = 0.2 s. Replaced with settled-solution diagnostics when available.'),\n'@@YPLUS_DISTRIBUTION@@':image('yplus_distribution.png','Area-weighted distribution at the explicitly labelled snapshot time.'),")
s=s.replace('@@YPLUS_CHART@@\n@@SPATIAL_YPLUS@@','@@YPLUS_CHART@@\n@@YPLUS_DISTRIBUTION@@\n@@SPATIAL_YPLUS@@')
s=s.replace("status='Meshing' if not (Q/'M04/measurement.json').exists() else 'Mesh ready'","status='Meshing' if not (Q/'M04/measurement.json').exists() else ('Mesh repair' if read(Q/'M04/measurement.json',{}).get('metrics',{}).get('NegativeVolumeCells',0)>0 else 'Mesh ready')")
p.write_text(s)
# Add direct y+ extrema to future runs; already running copied macros remain untouched.
p=R/'ContinueUntilSettled.java';s=p.read_text()
s=s.replace('private ForceReport fx,fz,pressure,shear;','private MinReport yMin; private MaxReport yMax;\n  private ForceReport fx,fz,pressure,shear;')
s=s.replace('FieldFunction vf=null;','''yMin=s.getReportManager().createReport(MinReport.class);yMax=s.getReportManager().createReport(MaxReport.class);
      for(ScalarReport r:List.of(yMin,yMax)){r.setFieldFunction(s.getFieldFunctionManager().getFunction("WallYplus"));r.getParts().setObjects(foil);r.setRepresentation(fv);}
      FieldFunction vf=null;''')
s=s.replace('interface_max_CFL,mean_yplus\\n','interface_max_CFL,mean_yplus,min_yplus,max_yplus\\n')
s=s.replace('ci+","+yp+"\\n"','ci+","+yp+","+yMin.getReportMonitorValue()+","+yMax.getReportMonitorValue()+"\\n"')
p.write_text(s)
print('Lower time-history plots rescaled; speculative M04 panel removed.')
