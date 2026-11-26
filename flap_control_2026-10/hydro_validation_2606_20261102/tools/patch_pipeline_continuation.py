from pathlib import Path
import shutil,datetime
h=Path(__file__).resolve().parents[1]
p=h/'macros/RunHydroStatic.java';s=p.read_text(encoding='utf8');shutil.copy2(p,h/'audit'/('RunHydroStatic_before_continuation_'+datetime.datetime.now().strftime('%H%M%S')+'.java'))
s=s.replace('name.equals("motion_verified.sim")||name.equals("pose_ready.sim")','name.equals("motion_verified.sim")||name.equals("pose_ready.sim")||(name.equals("steady_checkpoint.sim")&&Files.readString(base.resolve("initialization_status.json")).contains("steady_initialization_incomplete"))')
s=s.replace('Initialization pipeline only for newly prepared model/pose, never an existing flow checkpoint','Pipeline requires a prepared pose or incomplete steady initializer; never a physical-time URANS checkpoint')
p.write_text(s,encoding='utf8')
# Validate child macros before launching an expensive solver.
p=h/'tools/native_launch.py';s=p.read_text(encoding='utf8')
s=s.replace("str(R/'macros/compiled'),str(macro)","str(R/'macros/compiled'),str(macro),*([str(R/'macros'/c) for c in ['InitializeHydroControl.java','StabilizeHydro.java']] if macro.name=='RunHydroStatic.java' else [])")
p.write_text(s,encoding='utf8')
print('patched')
