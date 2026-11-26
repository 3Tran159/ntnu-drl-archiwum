from pathlib import Path
import csv
import json
import math
import statistics

d=Path(__file__).resolve().parent
with (d/"MESH_CELLS.csv").open(newline="",encoding="utf-8-sig") as stream:
    cells=list(csv.DictReader(stream))
def metric_size(r):
    return math.sqrt(float(r["Volume (m^3)"])/.02)
def summarize(values):
    return {"count":len(values),"min_m":min(values),"median_m":statistics.median(values),"max_m":max(values)} if values else {"count":0}
def inspect(predicate):
    return summarize([metric_size(r) for r in cells if predicate(float(r["X (m)"]),float(r["Y (m)"]))])
sizes={"domain":inspect(lambda x,y:True),
       "foil_neighbourhood":inspect(lambda x,y:-.30<=x<=1.48 and -.33<=y<=.39),
       "free_surface_band":inspect(lambda x,y:-10.5<=x<=26.5 and 1.65<=y<=2.40),
       "wake_core":inspect(lambda x,y:1.55<=x<=2.45 and abs(y)<.11),
       "farfield_away_from_foil_and_surface":inspect(lambda x,y:(y<-1 or y>3)),
       "near_inlet":inspect(lambda x,y:x<-11.45),
       "near_outlet":inspect(lambda x,y:x>27.45)}
with (d/"OUTER_FACES.csv").open(newline="",encoding="utf-8-sig") as stream:
    faces=list(csv.DictReader(stream))
if faces:
    area=next(k for k in faces[0] if k.startswith("Area") and k not in ("X (m)","Y (m)","Z (m)"))
    def lengths(predicate):
        return summarize([float(r[area])/.02 for r in faces if predicate(float(r["X (m)"]),float(r["Y (m)"]))])
    sizes["boundary_face_length_m"]={"inlet":lengths(lambda x,y:abs(x+12)<1e-6),
                                    "outlet":lengths(lambda x,y:abs(x-28)<1e-6),
                                    "top":lengths(lambda x,y:abs(y-4)<1e-6),
                                    "bottom":lengths(lambda x,y:abs(y+10)<1e-6)}
(d/"MESH_SIZE_STATS.json").write_text(json.dumps(sizes,indent=2))
print(json.dumps(sizes,indent=2))

