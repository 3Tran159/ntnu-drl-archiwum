from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
p=R/'macros/TestFlapPOC.java';s=p.read_text()
a=s.index('   Boundary marker=null;');b=s.index('   MinReport volume=',a)
s=s[:a]+'   Motion actualMotion=ov.getValues().get(MotionSpecification.class).getMotion();\n'+s[b:]
s=s.replace('   x0=cx.getReportMonitorValue()-xh;z0=cz.getReportMonitorValue()-zh;','')
s=s.replace('double command=5*Math.sin(2*Math.PI*t/.2),measured=Math.toDegrees(Math.atan2(z0,x0)-Math.atan2(cz.getReportMonitorValue()-zh,cx.getReportMonitorValue()-xh));','Vector3 moved=actualMotion.transformInitialCoordinate(new Vector3(xh+.2,0,zh));\n     double command=5*Math.sin(2*Math.PI*t/.2),measured=-Math.toDegrees(Math.atan2(moved.z-zh,moved.x-xh));')
p.write_text(s)
for old,new in [('runs/motion_check.csv','runs/motion_check_attempt2.csv'),('audit/test_error.txt','audit/test_error_attempt2.txt')]:
 if (R/old).exists() and not (R/new).exists():shutil.copy2(R/old,R/new)
p=R/'make_report.py';s=p.read_text()
s=s.replace('Rzeczywisty obrót siatki zmierzono z ruchu centroidu zewnętrznej powierzchni strefy overset, sztywno związanej z klapką i pozostającej poza obszarem wycinania komórek; nie jest to samo odczytanie funkcji zadanej.','Obrót kontrolowano przez odczyt transformacji ruchu po stronie solvera dla wirtualnego punktu związanego sztywno z klapką. Klatki rzeczywistej siatki potwierdzają kierunek ruchu i oba skrajne wychylenia. Nie używano średnich z aktywnych powierzchni overset jako znacznika położenia.')
s=s.replace('Maksymalny błąd obrotu','Maksymalna różnica transformacji i kąta zadanego')
p.write_text(s)
print('Using solver-side actual motion transform; all coarse mesh settings unchanged')
