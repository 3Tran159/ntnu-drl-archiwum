from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
p=R/'macros/TestFlapPOC.java';s=p.read_text()
s=s.replace('AreaAverageReport cx=centroid("POC flap centroid x",0,flapwalls),cz=centroid("POC flap centroid z",2,flapwalls);','Boundary marker=null;for(Boundary b:ov.getBoundaryManager().getBoundaries())if(b.getPresentationName().endsWith("Block Surface 6"))marker=b;if(marker==null)throw new IllegalStateException("Unblanked outer mesh marker not found");\n   AreaAverageReport cx=centroid("POC mesh marker x",0,Arrays.asList(marker)),cz=centroid("POC mesh marker z",2,Arrays.asList(marker));')
s=s.replace('frame(scene,frames);s.saveState(out.resolve("FlapPOC_2606_working.sim").toString());','frame(scene,frames);for(SolverStoppingCriterion stop:s.getSolverStoppingCriterionManager().getObjects())if(stop instanceof PhysicalTimeStoppingCriterion){((PhysicalTimeStoppingCriterion)stop).getMaximumTime().setValue(.4);stop.setIsUsed(true);}s.saveState(out.resolve("FlapPOC_2606_working.sim").toString());')
p.write_text(s)
for old,new in [('runs/motion_check.csv','runs/motion_check_attempt1.csv'),('audit/test_error.txt','audit/test_error_attempt1.txt')]:
 if (R/old).exists() and not (R/new).exists():shutil.copy2(R/old,R/new)
p=R/'make_report.py';s=p.read_text().replace('z ruchu centroidu powierzchni klapki','z ruchu centroidu zewnętrznej powierzchni strefy overset, sztywno związanej z klapką i pozostającej poza obszarem wycinania komórek')
s=s.replace('Gotowy plik zawiera ruch, raporty i scenę','Gotowy plik zatrzymuje kontynuację po osiągnięciu t = 0,4 s. Zawiera ruch, raporty i scenę')
p.write_text(s)
print('Changed marker measurement; earlier stopped attempt retained; bounded continuation enabled')
