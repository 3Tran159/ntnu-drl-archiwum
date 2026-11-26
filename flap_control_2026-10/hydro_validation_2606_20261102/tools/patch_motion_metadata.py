from pathlib import Path
R=Path(__file__).resolve().parents[1];p=R/'macros/CheckHydroMotion.java';t=p.read_text();old='note("MOTION_VERIFIED_FLOW_NOT_SOLVED");';new='Files.copy(base.resolve("normalization.json"),out.resolve("normalization.json"));note("MOTION_VERIFIED_FLOW_NOT_SOLVED");'
assert old in t
if new not in t:p.write_text(t.replace(old,new),encoding='utf8')
print('Motion output retains normalization metadata; no solver launched')
