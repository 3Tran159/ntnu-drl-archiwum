from pathlib import Path
import subprocess,json,hashlib,os,re,shutil,datetime
H=Path(__file__).resolve().parents[1];A=H.parent/'checkpoints/RELOCATION_20261103_073441'
def sha(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):d.update(b)
 return d.hexdigest()
meta=json.loads((A/'CHECKPOINTS.json').read_text())[1];source=A/meta['archive'];assert sha(source)==meta['sha256']
ps="Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'star-ccm+.exe' -and $_.ExecutablePath -match '21.04.009-R8'} | Select-Object ProcessId | ConvertTo-Json -Compress"
check=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,check=True);assert not check.stdout.strip(),'Owned native workers still present'
out=H/'cases/SP_B_split0_fixed/relocation_reopen_20261103_native_audit';out.mkdir(exist_ok=False);dst=out/'B0_recovered_t050.sim';shutil.copy2(source,dst);assert sha(dst)==meta['sha256']
approval=json.loads((H/'audit/LICENSE_USE_APPROVAL.json').read_text());assert approval['approved']
lic=Path(approval['source_log']);assert lic==H/'runs/RunURANSFromSteady_SP_C_20261102_203650.log'
with lic.open() as f:line=f.readline()
env=dict(os.environ)
for flag,key in [('-podkey','LM_PROJECT'),('-licpath','CDLMD_LICENSE_FILE')]:
 m=re.search(re.escape(flag)+r'\s+(\"[^\"]+\"|\S+)',line);assert m;env[key]=m.group(1).strip('"')
exe=Path(r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe')
with (out/'native_audit.log').open('w',encoding='utf8') as log:
 p=subprocess.Popen([str(exe),'-power','-np','1','-mpi','ms','-cpubind','off','-batch',str(H/'macros/RelocationNativeAudit.java'),str(dst)],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 receipt=dict(pid=p.pid,case=str(dst),cpu=1,gpu=False,operation='READ_ONLY_AUDIT',solver_steps=0,at=datetime.datetime.now().astimezone().isoformat());(out/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
 rc=p.wait()
 print('NATIVE_B0_AUDIT_EXIT='+str(rc),flush=True);assert rc==0
