from pathlib import Path
h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102')
t=(h/'runs/macro_snapshots/20261102_181259/BuildHydroMesh.java').read_text(encoding='utf8')
t=t.replace('class BuildHydroMesh','class BuildExtrudedHydroMesh').replace('import star.common.*;','import star.common.*;import star.extruder.*;')
new=(h/'macros/BuildHydroMesh.java').read_text(encoding='utf8')
t=t[:t.index('void meshAudit()')]+new[new.index('void meshAudit()'):new.index('public void execute()')]+t[t.index('public void execute()'):]
helper="""
Region exactExtrude(MeshOperationPart source,Region old,String name,boolean inner)throws Exception{
PhysicsContinuum pc=old.getPhysicsContinuum();List<PartSurface> caps=new ArrayList<>();for(PartSurface f:source.getPartSurfaces())if(f.getPresentationName().endsWith("span_source"))caps.add(f);if(caps.size()!=1)throw new IllegalStateException("One source cap required");
SurfaceExtruderOperation se=(SurfaceExtruderOperation)s.get(MeshOperationManager.class).createSurfaceExtruderOperation(List.of(source),name+" exact surface extrusion");
se.getPartSurfaces().setObjects(caps);se.setOutputMode(SurfaceExtruderOperation.OutputMode.SINGLE_NEW_PART);se.setPreExecuteMode(SurfaceExtruderOperation.PreExecuteMode.ALL_PERTINENT);se.setInternalSurfacesOption(SurfaceExtruderOperation.InternalSurfacesOption.NONE);
SurfaceExtruderDirection dir=se.getSurfaceExtruderControls().get(SurfaceExtruderDirection.class);dir.setDirectionMode(SurfaceExtruderDirection.DirectionMode.SPECIFIED);dir.getUserSpecifiedDirection().getDirection().setComponents(0,-.02,0);se.execute();
MeshOperationPart p=(MeshOperationPart)se.getOutputParts().getObjects().iterator().next();p.setPresentationName(name+" exact quasi2D fluid");Region fresh=region(p,name+" extruded",inner);fresh.setPhysicsContinuum(pc);
VolumeExtruderOperation ve=(VolumeExtruderOperation)s.get(MeshOperationManager.class).createVolumeExtruderOperation(List.of(p),name+" one span layer");ve.getVolumeExtruderControls().get(NumberOfLayers.class).setNumLayers(1);ve.setCheckIntersections(false);ve.execute();
s.getRepresentationManager().translateMesh(new Vector<Region>(List.of(fresh)),new Vector<Double>(List.of(0.,.02,0.)),s.getUnitsManager().getObject("m"),s.getCoordinateSystemManager().getLabCoordinateSystem());
List<Boundary> oldWalls=new ArrayList<>(old.getBoundaryManager().getBoundaries());fixed.removeAll(oldWalls);flap.removeAll(oldWalls);regions.remove(old);s.getRegionManager().removeRegions(List.of(old));fresh.setPresentationName(name);
FieldFunction hp=s.getFieldFunctionManager().getFunction("HYDRO_PiezometricZero");for(Boundary b:fresh.getBoundaryManager().getBoundaries()){
if(b.getBoundaryType() instanceof InletBoundary){b.getConditions().get(InletVelocityOption.class).setSelected(InletVelocityOption.Type.COMPONENTS);velocity(b.getValues().get(VelocityProfile.class));turbulence(b);}
else if(b.getBoundaryType() instanceof PressureBoundary){pressure(b.getValues().get(StaticPressureProfile.class),hp);turbulence(b);}
else if(b.getBoundaryType() instanceof WallBoundary&&b.getPresentationName().endsWith("bottom"))b.getConditions().get(WallShearStressOption.class).setSelected(WallShearStressOption.Type.SLIP);
}note(name+" exact one-layer extrusion ready for quality audit");return fresh;
}
"""
t=t.replace('public void execute()',helper+'public void execute()')
start=t.index('if(over){IndirectRegionInterface')
end=t.index('s.saveState(out.resolve(variant+"_configured_',start)
interface=t[start:end]
t=t[:start]+t[end:]
needle='reports((.10619978819242386+.009330092384759108)*.02*1000*9.8100004196167);meshAudit();'
t=t.replace(needle,'bg=exactExtrude(bgp,bg,"Background",false);if(over)ov=exactExtrude(ovp,ov,"FlapOverset",true);\n'+interface+needle)
(h/'macros/BuildExtrudedHydroMesh.java').write_text(t,encoding='utf8')
print('Independent exact extrusion builder prepared from first source-mesh recipe')
