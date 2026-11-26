import os, json, time, collections, traceback, pathlib, datetime, heapq
from pathlib import Path
ROOT = Path("F:/")
OUT = Path("F:/ntnu/flap_control/independent_cfd_diagnostics/disk_audit_20261103.json")
sizes=collections.defaultdict(int)
counts=collections.defaultdict(int)
extsizes=collections.defaultdict(int)
extcounts=collections.defaultdict(int)
big=[]
errors=[]
def group(parts):
    if not parts: return
    tops=[parts[0]]
    if len(parts)>1: tops.append("/".join(parts[:2]))
    if len(parts)>2 and parts[0].casefold()=="ntnu" and parts[1].casefold()=="flap_control": tops.append("/".join(parts[:3]))
    if len(parts)>3 and parts[:3]==("ntnu","flap_control","hydro_validation_2606_20261102"): tops.append("/".join(parts[:4]))
    if len(parts)>4 and parts[:4]==("ntnu","flap_control","hydro_validation_2606_20261102","cases"):tops.append("/".join(parts[:5]))
    if len(parts)>5 and parts[:5]==("ntnu","flap_control","hydro_validation_2606_20261102","cases","SP_C_split0_overset"):tops.append("/".join(parts[:6]))
    return tops
t0=time.time()
try:
    roots=sorted([x for x in ROOT.iterdir() if x.is_dir()],key=lambda x:x.name)
    for top in roots:
        name=top.name
        num=0
        for current, dirs, files in os.walk(top,topdown=True,followlinks=False,onerror=lambda e:errors.append(str(e))):
            dirs[:]=[x for x in dirs if not os.path.islink(os.path.join(current,x))]
            for filename in files:
                path=os.path.join(current,filename)
                try:
                    stat=os.stat(path,follow_symlinks=False)
                    size=stat.st_size
                    relative=Path(path).relative_to(ROOT)
                    parts=relative.parts
                    for key in group(parts):
                        sizes[key]+=size
                        counts[key]+=1
                    ex=Path(filename).suffix.lower() or "(none)"
                    if len(parts)>=3 and parts[0].lower()=="ntnu" and parts[1].lower()=="flap_control":
                        extsizes[ex]+=size;extcounts[ex]+=1
                    if size>=250*1024**2:
                        big.append((size,path,stat.st_mtime))
                    num+=1
                except Exception as e: errors.append(f"{path} {e}")
        print("SCANNED",name,"files",num,"GiB",round(sizes[name]/1024**3,3),flush=True)
except Exception as e:
    errors.append("ROOT_SCAN "+str(e))
body={"at":datetime.datetime.now().astimezone().isoformat(),"runtime_s":round(time.time()-t0,1),
      "top":sorted(({"path":k,"GiB":round(v/1024**3,3),"file_count":counts[k]} for k,v in sizes.items() if k.count("/")==0),key=lambda x:-x["GiB"]),
      "folders":sorted(({"path":k,"GiB":round(v/1024**3,3),"file_count":counts[k]} for k,v in sizes.items() if k.count("/")>0),key=lambda x:-x["GiB"])[:120],
      "extensions_flap_control":sorted(({"extension":k,"GiB":round(v/1024**3,3),"count":extcounts[k]} for k,v in extsizes.items()),key=lambda x:-x["GiB"])[:35],
      "big_files": [{"GiB":round(s/1024**3,3),"path":p,"mtime":datetime.datetime.fromtimestamp(m).astimezone().isoformat()} for s,p,m in sorted(big,reverse=True)[:160]],
      "errors":errors[:50]}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(body,ensure_ascii=False,indent=2),encoding="utf-8")
print("AUDIT_SAVED",str(OUT),"ELAPSED",body["runtime_s"],"TOP_BIG",json.dumps(body["top"][:10]),flush=True)
