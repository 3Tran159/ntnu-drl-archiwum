from pathlib import Path

d = Path(__file__).resolve().parent
p = d/"MiniVofStokes.java"
s = p.read_text()
s = s.replace('  double[][] force=new double[400][3];',
'''  int rampIterations=i("steady_ramp_iterations",0);
  double u0=d("u_initial_m_s",speed);
  double[][] force=new double[rampIterations==0?400:550][3];''',1)
s = s.replace('h.write("iteration,CL,CD,Mh,pABSmin,pbody,mass_relative,quality\\n");',
'''h.write("iteration,CL,CD,Mh,pABSmin,pbody,mass_relative,quality,U_m_s,pmin_x_m,pmin_y_m,pwall_x_m,pwall_y_m\\n");''',1)
s = s.replace('    s.getSimulationIterator().step(1);\n    if(n%5!=4)continue;',
'''    double speedNow=speed;
    if(rampIterations>0){
     speedNow=u0+(speed-u0)*smoothValue((n+1.)/rampIterations);
     inlet.getValues().get(VelocityProfile.class).getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(speedNow,0,0);
    }
    s.getSimulationIterator().step(1);
    if(n%5!=4)continue;''',1)
s = s.replace('","+p+","+pb+","+m+","+q+"\\n");h.flush();',
'''","+p+","+pb+","+m+","+q+","+speedNow+","+minLoc("pmin",0)+","+minLoc("pmin",1)+","+minLoc("pbody",0)+","+minLoc("pbody",1)+"\\n");h.flush();''',1)
s = s.replace('if(n>=149&&n%25==24&&m<=1e-4)','if(n>=Math.max(149,rampIterations+99)&&n%25==24&&m<=1e-4)',1)
s = s.replace('  min("pmin",ff("AbsolutePressure"),parts);min("pbody",ff("AbsolutePressure"),walls);',
'''  for(MinReport pressure:List.of(min("pmin",ff("AbsolutePressure"),parts),min("pbody",ff("AbsolutePressure"),walls)))
   pressure.setCollocatedFieldFunctions(List.of(ff("Position").getComponentFunction(0),ff("Position").getComponentFunction(1)));''',1)
p.write_text(s)
p = d/"run_gap.py"
s = p.read_text().replace('dt=.0005, steps=0,','dt=.0005, steps=0, steady_ramp_iterations=200, u_initial_m_s=.10,',1)
p.write_text(s)

