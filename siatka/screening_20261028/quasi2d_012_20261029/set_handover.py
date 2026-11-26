from pathlib import Path
p=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029\FlowQ2DGpuM02.java")
s=p.read_text(encoding="utf-8")
key='      Files.writeString(root.resolve("sequence_completed.json")'
addition='      for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof PhysicalTimeStoppingCriterion){((PhysicalTimeStoppingCriterion)x).getMaximumTime().setValue(s.getSolution().getPhysicalTime()+0.05);((SolverStoppingCriterion)x).setIsUsed(true);}\n      s.saveState(root.resolve("Q2D_012_review.sim").toString());\n'
s=s.replace(key,addition+key)
p.write_text(s,encoding="utf-8")
