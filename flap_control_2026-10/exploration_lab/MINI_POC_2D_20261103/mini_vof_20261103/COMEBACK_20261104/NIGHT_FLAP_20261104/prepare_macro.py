from pathlib import Path

here = Path(__file__).resolve().parent
base = here.parent / "runs/MATCHED_FIXED_GAP_RESUME0600_STABILIZE_THEN_ACTIVE_20261104_200827/MiniVofStokes.java"
src = base.read_text(encoding="utf-8")

def replace(old, new):
    global src
    if src.count(old) != 1:
        raise RuntimeError(f"Patch anchor count {src.count(old)}: {old[:95]}")
    src = src.replace(old, new, 1)

replace('   return -2*smoothValue(elapsed/.05)+2*smoothValue((elapsed-.05)/.05)\n          +2*smoothValue((elapsed-.10)/.05)-2*smoothValue((elapsed-.15)/.05);',
        '   double a=d("flap_cycle_deg",2), q=d("flap_quarter_s",.05);\n'
        '   return a*(-smoothValue(elapsed/q)+smoothValue((elapsed-q)/q)\n'
        '          +smoothValue((elapsed-2*q)/q)-smoothValue((elapsed-3*q)/q));')
replace('   command="0.03490658503988659*(-"+smooth(time+"/<.05 s>")+"+"+smooth("("+time+"-<.05 s>)/<.05 s>")\n       +"+"+smooth("("+time+"-<.10 s>)/<.05 s>")+"-"+smooth("("+time+"-<.15 s>)/<.05 s>")+")";',
        '   double q=d("flap_quarter_s",.05); String spanTime="/<"+q+" s>";\n'
        '   command=Math.toRadians(d("flap_cycle_deg",2))+"*(-"+smooth(time+spanTime)+"+"\n'
        '       +smooth("("+time+"-<"+q+" s>)"+spanTime)+"+"+smooth("("+time+"-<"+(2*q)+" s>)"+spanTime)\n'
        '       +"-"+smooth("("+time+"-<"+(3*q)+" s>)"+spanTime)+")";')
replace('  if(flap<=FLAP_LIMIT)return "HOLD_FLAP_PRESSURE_MARGIN";',
        '  if(!b("pressure_diagnostic_only")&&flap<=FLAP_LIMIT)return "HOLD_FLAP_PRESSURE_MARGIN";')
replace('"limit_Pa",FLAP_LIMIT,"gate_surface","flap_wall_only"', 
        '"limit_Pa",b("pressure_diagnostic_only")?2339.214766776897:FLAP_LIMIT,\n'
        '      "gate_surface",b("pressure_diagnostic_only")?"flap_wall_and_hinge_diagnostic":"flap_wall_only"')
replace('      BufferedWriter rr=Files.newBufferedWriter(out.resolve("residual_per_step.csv"))){\n   h.write("time_s,solver_s,delta_command_deg',
        '      BufferedWriter warnings=Files.newBufferedWriter(out.resolve("PRESSURE_BELOW_VAPOR.csv"));\n'
        '      BufferedWriter rr=Files.newBufferedWriter(out.resolve("residual_per_step.csv"))){\n'
        '   warnings.write("time_s,flap_Pa,hinge_Pa,vapor_pressure_Pa\\n");\n'
        '   h.write("time_s,solver_s,delta_command_deg')
replace('    String pressureFailure=gapPressureFailure(p,pb,pflap,pgap);\n    h.write(t+","+sec',
        '    String pressureFailure=gapPressureFailure(p,pb,pflap,pgap);\n'
        '    double vapor=2339.214766776897;\n'
        '    if(b("pressure_diagnostic_only")&&(pflap<=vapor||pgap<=vapor)){\n'
        '     warnings.write(t+","+pflap+","+pgap+","+vapor+"\\n");warnings.flush();\n'
        '    }\n'
        '    h.write(t+","+sec')
replace('  if(b("fixed_protocol")){\n   max("CFL"', '  if(b("fixed_protocol")){\n   max("CFL"')
(here/"MiniVofStokes.java").write_text(src,encoding="utf-8")

