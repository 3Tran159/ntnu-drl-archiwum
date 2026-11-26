from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'FoilWaveDiagnosticR1.java';s=p.read_text(encoding='utf8')
lines=s.splitlines();trace=next(x for x in lines if 'out.resolve("linear_trace_setup.json")' in x);lines.remove(trace);s='\n'.join(lines)+'\n'
anchor='waterInner=everyInner(nativeWater);airInner=everyInner(nativeAir);'
assert anchor in s;s=s.replace(anchor,anchor+'\n'+trace)
s=s.replace('scalarScene("12 Free-surface band - water fraction",mid,ff("VolumeFractionwater"),5,2,23','scalarScene("12 Free-surface close-up - water fraction",mid,ff("VolumeFractionwater"),-5,2,1.2')
p.write_text(s,encoding='utf8');print('Draft sequencing fixed; scenes and solver guards retained')
