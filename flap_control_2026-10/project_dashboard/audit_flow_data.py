import csv, collections, pathlib, time, json, math
ROOT=pathlib.Path(r"F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset")
SOURCES=[
("smoke_background",ROOT/"ramp_plus2_20261103_093316"/"Background_final_volume.csv"),
("smoke_flap",ROOT/"ramp_plus2_20261103_093316"/"FlapOverset_final_volume.csv"),
("final_background_mesh",ROOT/"ramp_plus2_20261103_094340"/"Background_latest_full_plane.csv"),
("final_flap_mesh",ROOT/"ramp_plus2_20261103_094340"/"FlapOverset_latest_full_plane.csv")
]
for name,p in SOURCES:
 t=time.time();count=0;codes=collections.Counter();typ=collections.Counter();extr={}
 mn=[math.inf,math.inf];mx=[-math.inf,-math.inf]
 try:
  with p.open(newline="",encoding="utf-8-sig") as f:
   for row in csv.DictReader(f):
    count+=1;codes[row.get("Overset Cell Status")]+=1;typ[row.get("Overset Cell Type")]+=1
    if row.get("Overset Cell Status")=="0":
     x=float(row["X (m)"]);z=float(row["Z (m)"])
     mn[0]=min(x,mn[0]);mn[1]=min(z,mn[1]);mx[0]=max(x,mx[0]);mx[1]=max(z,mx[1])
     for k in ("Velocity[i] (m/s)","Velocity[k] (m/s)","Absolute Pressure (Pa)","Pressure (Pa)"):
      if k in row:
       v=float(row[k]);a=extr.setdefault(k,[math.inf,-math.inf]);a[0]=min(a[0],v);a[1]=max(a[1],v)
  print(json.dumps({"source":name,"count":count,"status_counts":codes,"type_counts":typ,"active0_xz_min":mn,"active0_xz_max":mx,"active0_extrema":extr,"seconds":round(time.time()-t,2)},default=list))
 except Exception as e: print(name,str(e))
