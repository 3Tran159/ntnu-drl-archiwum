from pathlib import Path
h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102')
p=h/'macros/StabilizeHydro.java';t=p.read_text(encoding='utf8')
t=t.replace('String variant;','String variant;double staticAngle=0;RotatingMotion rotation=null;')
old='if(!a.equals("<0 deg>")&&!a.equals("0.0"))throw new IllegalStateException("Stabilization currently requires zero angle: "+a);'
new='rotation=(RotatingMotion)m;if(a.equals("0.0"))staticAngle=0;else if(a.matches("<[+-]?[0-9.]+ deg>"))staticAngle=Double.parseDouble(a.substring(1,a.length()-5));else throw new IllegalStateException("Constant angle required: "+a);if(Math.abs(staticAngle)>5.000001)throw new IllegalStateException("Angle exceeds approved range");'
assert old in t;t=t.replace(old,new)
t=t.replace('Initializing fresh singlephase working case','Activating saved field storage or initializing fresh singlephase case; retain existing physical time')
t=t.replace('static_angle_deg\\\":0','static_angle_deg\\\":"+staticAngle+"')
t=t.replace('for(int k=1;k<=2000;k++)','ElementCountReport oversetErrors=null,oversetFallback=null;if(variant.equals("SP_C")){Representation rep=(Representation)s.getRepresentationManager().getObject("Overset Mesh");oversetErrors=count("Static overset errors "+runId,namedField("Overset Error Status","OversetErrorStatus"),.5,100,rep);oversetFallback=count("Static difficult interpolation "+runId,namedField("Overset Interpolation Type","OversetInterpolationType"),3.5,6.5,rep);}\nfor(int k=1;k<=2000;k++)')
t=t.replace('virtual_h_clear_over_c,mass_imbalance_relative','virtual_h_clear_over_c,mass_imbalance_relative,overset_error_cells,difficult_interpolation_cells')
t=t.replace('double h=2-zmax.getReportMonitorValue();','double angle=0;if(rotation!=null){Vector3 measured=rotation.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));angle=-Math.toDegrees(Math.atan2(measured.z-zh,measured.x-xh));if(Math.abs(angle-staticAngle)>.01)throw new IllegalStateException("Static angle changed unexpectedly");}double oe=oversetErrors==null?0:oversetErrors.getReportMonitorValue(),of=oversetFallback==null?0:oversetFallback.getReportMonitorValue();if(!Double.isFinite(oe+of)||oe>0)throw new IllegalStateException("Overset connectivity guard failed");\ndouble h=2-zmax.getReportMonitorValue();')
t=t.replace('%d,%.12g,%.12g,0,0,','%d,%.12g,%.12g,%.12g,0,')
t=t.replace('k,t,t-t0,fx,fz','k,t,t-t0,angle,fx,fz')
t=t.replace('w.write(","+massRel);','w.write(","+massRel+","+oe+","+of);')
motion=(h/'macros/CheckHydroMotion.java').read_text(encoding='utf8')
helper=motion[motion.index('FieldFunction namedField('):motion.index('public void execute()')]
t=t.replace('public void execute()',helper+'public void execute()')
p.write_text(t,encoding='utf8');print('Static +/-5deg support; explicit Overset and measured-angle gates')
