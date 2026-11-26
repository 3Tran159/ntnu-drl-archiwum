from pathlib import Path
import shutil,datetime
h=Path(__file__).resolve().parents[1];p=h/'tools/night_native.py'
shutil.copy2(p,h/'audit'/('night_native_before_queue_'+datetime.datetime.now().strftime('%H%M%S')+'.py'))
s=p.read_text(encoding='utf8')
s=s.replace("'ResumeC0Qualified.java':8}","'ResumeC0Qualified.java':8,'InspectHydroComparison.java':1}")
s=s.replace("macro=h/'macros'/name;", "variant='SP_B' if 'SP_B_split0_fixed' in sim.parts else 'SP_C'\nassert name=='InspectHydroComparison.java' or variant=='SP_C'\nassert shutil.disk_usage(h).free>15*1024**3,'Insufficient free space'\nmacro=h/'macros'/name;")
s=s.replace("+'_SP_C_'+stamp", "+'_'+variant+'_'+stamp")
s=s.replace("'NTNU_HYDRO_VARIANT':'SP_C'","'NTNU_HYDRO_VARIANT':variant")
s=s.replace("receipt=dict(pid=proc.pid,","receipt=dict(pid=proc.pid,variant=variant,")
s=s.replace("print(json.dumps(receipt,indent=2))","print(json.dumps(receipt,indent=2))")
p.write_text(s,encoding='utf8')
print('Launcher extended for explicit read-only B/C comparison; existing approved licensing unchanged.')
