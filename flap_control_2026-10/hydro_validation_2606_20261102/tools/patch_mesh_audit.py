from pathlib import Path
R=Path(__file__).resolve().parents[1];p=R/'macros/BuildHydroMesh.java';t=p.read_text()
old='Files.writeString(out.resolve("mesh_integrity.txt"),fv.generateMeshReport(regions).toFormattedString());'
new='NeoProperty integrity=fv.generateMeshReport(regions);Files.writeString(out.resolve("mesh_integrity.txt"),integrity.toFormattedString());'
assert old in t;t=t.replace(old,new)
old='if(!(q>0&&v>0&&f>.5))throw new IllegalStateException("Invalid mesh");';assert old in t;t=t.replace(old,'boolean valid=integrity.getBoolean("success")&&q>0&&v>0&&f>.5;')
t=t.replace('s.getFieldFunctionManager().getFunction("CellQuality"),s.getFieldFunctionManager().getFunction("PrismLayerNumber")','s.getFieldFunctionManager().getFunction("Volume"),s.getFieldFunctionManager().getFunction("FaceValidity"),s.getFieldFunctionManager().getFunction("CellQuality"),s.getFieldFunctionManager().getFunction("PrismLayerNumber")')
anchor='\\\"hydrodynamically_validated\\\":false}\\");'
# Insert guard at end of meshAudit after its summary export, retaining all diagnostic exports.
start=t.index('void meshAudit()');end=t.index('\npublic void execute()',start);part=t[start:end];pos=part.rfind('\n}')
part=part[:pos]+'\nif(!valid){scene();throw new IllegalStateException("Mesh integrity failed: "+integrity.toFormattedString());}'+part[pos:]
t=t[:start]+part+t[end:];p.write_text(t,encoding='utf8');print('Mesh audit now exports diagnostics on failure and requires closed cells')
