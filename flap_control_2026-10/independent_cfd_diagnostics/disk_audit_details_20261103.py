import os,shutil,collections,json,datetime
from pathlib import Path
G=1024**3
roots={
 "mesh_screening":Path(r"F:\ntnu\mesh_screening_20261028"),
 "wave_old":Path(r"F:\ntnu\New Folder"),
 "flap_checkpoints":Path(r"F:\ntnu\flap_control\checkpoints"),
 "flap_cases":Path(r"F:\ntnu\flap_control\hydro_validation_2606_20261102\cases"),
 "flap_C0_cases":Path(r"F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset")
}
def sizes(path):
    top=collections.defaultdict(lambda:[0,0])
    ext=collections.defaultdict(lambda:[0,0])
    larg=[]
    for current,dirs,files in os.walk(path):
        dirs[:]=[di for di in dirs if not os.path.islink(os.path.join(current,di))]
        for file in files:
            p=Path(current)/file
            try:
                st=p.stat()
            except OSError: continue
            rel=p.relative_to(path).parts
            head=rel[0] if len(rel)>1 else file
            top[head][0]+=st.st_size;top[head][1]+=1
            k=p.suffix.lower()
            ext[k][0]+=st.st_size;ext[k][1]+=1
            if st.st_size>250*1024**2:
                larg.append((st.st_size,str(p),st.st_mtime))
    return {"children":sorted([{"name":k,"GiB":round(v[0]/G,3),"n":v[1]} for k,v in top.items()],key=lambda x:-x["GiB"])[:45],
    "ext":sorted([{"ext":k,"GiB":round(v[0]/G,3),"n":v[1]} for k,v in ext.items()],key=lambda x:-x["GiB"])[:20],
    "big": [{"GiB":round(s/G,3),"path":p,"modified":datetime.datetime.fromtimestamp(t).astimezone().isoformat()} for s,p,t in sorted(larg,reverse=True)[:24]]}
out={"drives":{},"areas":{k:sizes(p) for k,p in roots.items()},"ntnu_root_files":[]}
for dr in "CDEF":
    try:
        u=shutil.disk_usage(dr+":\\")
        out["drives"][dr]={"total_GiB":round(u.total/G,2),"free_GiB":round(u.free/G,2)}
    except Exception as e:out["drives"][dr]={"error":str(e)}
for p in Path(r"F:\ntnu").iterdir():
    if p.is_file():
        st=p.stat();out["ntnu_root_files"].append({"name":p.name,"GiB":round(st.st_size/G,3),
        "modified":datetime.datetime.fromtimestamp(st.st_mtime).astimezone().isoformat()})
out["ntnu_root_files"].sort(key=lambda a:-a["GiB"])
target=Path(r"F:\ntnu\flap_control\independent_cfd_diagnostics\disk_audit_details_20261103.json")
target.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print("DRIVES",out["drives"])
for k,v in out["areas"].items():
    print("AREA",k,"TOP",json.dumps(v["children"][:13],ensure_ascii=False),"EXT",json.dumps(v["ext"][:7],ensure_ascii=False))
print("NTNU TOP ROOT",json.dumps(out["ntnu_root_files"][:20],ensure_ascii=False))
print("DETAILS_SAVED",target)
