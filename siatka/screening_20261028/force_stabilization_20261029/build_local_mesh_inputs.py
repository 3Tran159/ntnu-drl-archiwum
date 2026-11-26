"""Offline compile only; never starts STAR or changes campaign locks."""
from pathlib import Path
import hashlib,json,datetime,subprocess,uuid
R=Path(__file__).resolve().parent
M=R/"InspectLocalMesh.java"
JAVAC=Path("C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe")
EXT=Path("E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java/platform/modules/ext")
def main():
 text=M.read_text()
 forbidden=["initializeSolution(", "clearSolution(", "clearSolutionWithoutMeshReset(", ".step(", "getSimulationIterator().run("]
 if any(v in text for v in forbidden):raise RuntimeError("Flow/reset call found in inspection macro")
 out=R/("compiled_local_mesh_import_"+uuid.uuid4().hex[:10]);out.mkdir()
 p=subprocess.run([str(JAVAC),"-proc:none","--release","21","-cp",str(EXT/"*"),"-d",str(out),str(M)],capture_output=True,text=True,encoding="utf-8",errors="replace",creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 (out/"compile.log").write_text(p.stdout+"\n"+p.stderr)
 result=dict(status="javac_passed" if p.returncode==0 else "compile_failed",at=datetime.datetime.now().astimezone().isoformat(),macro=str(M),macro_sha256=hashlib.sha256(M.read_bytes()).hexdigest(),compiled_directory=str(out),compile_log=str(out/"compile.log"),zero_flow_static_scan=True,STAR_launched=False,returncode=p.returncode)
 (R/"local_mesh_import_compile_receipt.json").write_text(json.dumps(result,indent=2))
 print(json.dumps(result))
 if p.returncode:print(p.stderr)
 return p.returncode
if __name__=="__main__":raise SystemExit(main())
