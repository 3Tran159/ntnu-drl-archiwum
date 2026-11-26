from pathlib import Path
import os,json,collections,datetime
G=1024**3
dirs=[Path(r"F:\ntnu\New Folder"),Path(r"F:\ntnu\mesh_screening_20261028")]
out=[]
for root in dirs:
    for current, ds, fs in os.walk(root):
        for f in fs:
            if not f.lower().endswith(".sim~"):continue
            p=Path(current)/f
            original=Path(str(p)[:-1])
            try:
                st=p.stat()
                o=original.stat() if original.is_file() else None
                out.append({
                "backup":str(p),"backup_GiB":round(st.st_size/G,3),"backup_modified":datetime.datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(),
                "original_exists":bool(o),"original_GiB":round(o.st_size/G,3) if o else None,
                "size_difference_MiB":round(abs(o.st_size-st.st_size)/1024**2,1) if o else None,
                "original_modified":datetime.datetime.fromtimestamp(o.st_mtime).astimezone().isoformat() if o else None})
            except Exception as e: print("ERROR",p,e)
print("TOTAL backups",len(out),"GiB",round(sum(x["backup_GiB"] for x in out),3))
print("WITH original",sum(x["original_exists"] for x in out),"GiB",round(sum(x["backup_GiB"] for x in out if x["original_exists"]),3))
for x in sorted(out,key=lambda x:-x["backup_GiB"]): print(json.dumps(x,ensure_ascii=False))
