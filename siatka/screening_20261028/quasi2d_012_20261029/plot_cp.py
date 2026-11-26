import sys,csv
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
sys.path.insert(0,str(r/"deps311"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"svg.fonttype":"none"})
fig,ax=plt.subplots(figsize=(9,5.3),layout="constrained")
for name,color in [("M01","#167e92"),("M02","#bc6115"),("M03","#704cb6")]:
 p=r/name/"F18_dt500us/foil_final_fields.csv"
 with p.open() as f:rows=[{k:float(v) for k,v in x.items()} for x in csv.DictReader(f)]
 pk=next(k for k in rows[0] if "Pressure" in k)
 for upper in [True,False]:
  data=sorted([x for x in rows if (x["Z (m)"]>.025*1.19*4*(x["X (m)"]/1.19)*(1-x["X (m)"]/1.19))==upper],key=lambda x:x["X (m)"])
  ax.plot([x["X (m)"]/1.19 for x in data],[(x[pk]-1000*9.81*(2-x["Z (m)"]))/(.5*1000*18**2) for x in data],color=color,ls="-" if upper else "--",lw=1.5,label=name+" "+("góra" if upper else "dół"))
ax.set(xlabel="x/c",ylabel="Cp po odjęciu nominalnego ciśnienia hydrostatycznego",title="Ciśnienie na profilu · 18 m/s · t=0,02 s · dt=0,5 ms")
ax.invert_yaxis();ax.grid(alpha=.2);ax.legend(ncols=2)
fig.savefig(r/"plots/Cp_startup.png",dpi=150);fig.savefig(r/"plots/Cp_startup.svg")
print("Saved Cp comparison")
