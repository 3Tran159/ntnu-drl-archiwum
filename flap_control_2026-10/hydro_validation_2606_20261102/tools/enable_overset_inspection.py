from pathlib import Path
h=Path(__file__).resolve().parents[1];p=h/'tools/native_launch.py';s=p.read_text(encoding='utf8')
s=s.replace("allowed={'InspectHydroReference.java'","allowed={'InspectOversetPhysics.java','InspectHydroReference.java'")
s=s.replace("if macro.name=='InspectMeshFailure.java':","if macro.name=='InspectOversetPhysics.java':\n  assert 'RunURANSFromSteady.java' in owned[0]['CommandLine'] and variant=='SP_C','Independent Overset audit alongside owned C URANS only'\n  reason='One CPU snapshot inspection; zero solver steps and no simulation save; input is immutable steady checkpoint'\n elif macro.name=='InspectMeshFailure.java':")
# Existing generic resource gate is free>=24 GiB and load<=50 for this read-only inspection.
p.write_text(s,encoding='utf8');print('bounded independent read-only audit enabled')
