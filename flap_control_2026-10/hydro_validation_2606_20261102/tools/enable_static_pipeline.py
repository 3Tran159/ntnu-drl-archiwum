from pathlib import Path
import datetime,shutil
h=Path(__file__).resolve().parents[1];p=h/'tools/native_launch.py';s=p.read_text(encoding='utf8')
shutil.copy2(p,h/'audit'/('native_launch_before_angles_'+datetime.datetime.now().strftime('%H%M%S')+'.py'))
s=s.replace("'PrepareStaticFlap.java','RunHydroStatic.java'","'PrepareStaticFlap.java','RunHydroStatic.java','RunStaticAngle.java'")
s=s.replace("['InitializeHydroControl.java','StabilizeHydro.java']] if macro.name=='RunHydroStatic.java' else []","(['PrepareStaticFlap.java'] if macro.name=='RunStaticAngle.java' else [])+['InitializeHydroControl.java','StabilizeHydro.java']] if macro.name in {'RunHydroStatic.java','RunStaticAngle.java'} else []")
s=s.replace("{'InitializeHydroControl.java','StabilizeHydro.java','RunHydroStatic.java'}","{'InitializeHydroControl.java','StabilizeHydro.java','RunHydroStatic.java','RunStaticAngle.java'}")
s=s.replace("if macro.name=='RunHydroStatic.java':\n for child in ['InitializeHydroControl.java','StabilizeHydro.java']:","if macro.name in {'RunHydroStatic.java','RunStaticAngle.java'}:\n for child in (['PrepareStaticFlap.java'] if macro.name=='RunStaticAngle.java' else [])+['InitializeHydroControl.java','StabilizeHydro.java']:")
s=s.replace("if macro.name=='PrepareStaticFlap.java':","if macro.name in {'PrepareStaticFlap.java','RunStaticAngle.java'}:")
compile(s,str(p),'exec');p.write_text(s,encoding='utf8');print('enabled bounded static-angle pipeline; not launched')
