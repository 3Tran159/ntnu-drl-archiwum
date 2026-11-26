"""Low-priority saved-field renderer scheduler. No STAR calls or solver controls."""
import ctypes,datetime,json,os,subprocess,sys,time,uuid
from pathlib import Path
from ctypes import wintypes
R=Path(__file__).resolve().parent
BASE=Path('E:/ntnu/quasi2d_waves_20261029')
PYTHON=Path('E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/python/python.exe')
LOCK=R/'wave_side_view_renderer.lock'
STATE=R/'wave_side_view_renderer_state.json'
CADENCE_S=120
TIMEOUT_S=180
def stamp():return datetime.datetime.now().astimezone().isoformat()
def read(p):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return {}
def write(p,data):
    temp=p.with_name(p.name+'.'+str(os.getpid())+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(data,indent=2),encoding='utf-8');os.replace(temp,p)
def alive(pid):
    if not isinstance(pid,int) or pid<=0:return False
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
    k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];k.GetExitCodeProcess.restype=wintypes.BOOL
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=k.OpenProcess(0x1000,False,pid)
    if not handle:return ctypes.get_last_error()!=87
    code=wintypes.DWORD()
    try:return bool(k.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
    finally:k.CloseHandle(handle)
def acquire_render_lock():
    for unused in range(2):
        try:
            with LOCK.open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'started_at':stamp(),'purpose':'Saved-field side-view renderer; no solver'},f)
            return True
        except FileExistsError:
            previous=read(LOCK)
            if alive(previous.get('pid')):return False
            if not previous and time.time()-LOCK.stat().st_mtime<180:return False
            try:LOCK.rename(LOCK.with_name('wave_side_view_renderer.stale_'+uuid.uuid4().hex+'.json'))
            except FileNotFoundError:pass
    return False
def release_render_lock(pid=None):
    if read(LOCK).get('pid')==(os.getpid() if pid is None else pid):
        try:LOCK.unlink()
        except FileNotFoundError:pass
def free_memory_gib():
    class Mem(ctypes.Structure):
        _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD),('totalPhysical',ctypes.c_ulonglong),('availablePhysical',ctypes.c_ulonglong),('totalPageFile',ctypes.c_ulonglong),('availablePageFile',ctypes.c_ulonglong),('totalVirtual',ctypes.c_ulonglong),('availableVirtual',ctypes.c_ulonglong),('extendedVirtual',ctypes.c_ulonglong)]
    data=Mem();data.length=ctypes.sizeof(data)
    return data.availablePhysical/1024**3 if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(data)) else None
def candidate():
    case=read(R/'wave_foil_run_state.json').get('case')
    if not case or not case.startswith(('W01_W20L4_M10_FS020_','W01a_W20L4_M10_','C01_W20L4_M10_calm_settle_r2','LOCAL_')):return None
    active=BASE/case
    if active.parent!=BASE:return None
    identity=read(active/'source_identity.json');folders=[active]
    parent=BASE/'W01_W20L4_M10_FS020_diagnostic_r1'
    if identity.get('source_sha256')==identity.get('input_sha256') and Path(identity.get('source','')).parent==parent and identity.get('reinitialized') is False:
        folders.append(parent)
    found=[]
    for folder in folders:
        for p in folder.glob('local_balance_t*.csv'):
            try:
                t=float(p.stem.split('_t')[-1]);s=p.stat()
                if s.st_size<=1000 or time.time()-s.st_mtime<8:continue
                if folder==parent and abs(t-float(identity.get('source_time_s',-1)))>1e-7:continue
                found.append({'case':case,'path':str(p),'time_s':t,'mtime_ns':s.st_mtime_ns,'size_bytes':s.st_size})
            except (OSError,ValueError):continue
    return max(found,key=lambda x:x['time_s']) if found else None
def record(status,**values):
    old=read(STATE)
    write(STATE,dict(updated_at=stamp(),status=status,refresh_s=CADENCE_S,timeout_s=TIMEOUT_S,
        service_pid=os.getpid(),last_success=old.get('last_success'),**values))
def tick():
    source=candidate()
    if source is None:record('waiting_for_compatible_saved_field',renderer_pid=None);return
    held=read(LOCK)
    if alive(held.get('pid')):record('existing_renderer_active',renderer_pid=held['pid'],source=source);return
    manifest=read(R/'wave_side_view_current.json')
    if (manifest.get('case')==source['case'] and manifest.get('source_file')==source['path'] and
        manifest.get('source_mtime_ns')==source['mtime_ns'] and Path(manifest.get('image_path','missing')).is_file()):
        record('idle_cached',renderer_pid=None,source=source,field_time_s=manifest.get('time_s'));return
    available=free_memory_gib()
    if available is not None and available<4:
        record('deferred_low_memory',renderer_pid=None,available_memory_gib=round(available,2),source=source);return
    env=os.environ.copy()
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[key]='1'
    flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS
    p=subprocess.Popen([str(PYTHON),str(R/'plot_wave_side_view.py')],cwd=str(R),env=env,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags)
    record('rendering',renderer_pid=p.pid,source=source,started_at=stamp(),priority='below_normal',numeric_threads=1)
    try:out,err=p.communicate(timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        p.terminate();out,err=p.communicate(timeout=10);release_render_lock(p.pid)
        record('renderer_timeout',renderer_pid=None,source=source,last_error='Renderer exceeded 180 s; only this renderer child was stopped.');return
    summary=out.decode('utf-8',errors='replace').strip()[-2000:]
    if p.returncode:
        record('renderer_error',renderer_pid=None,source=source,returncode=p.returncode,last_error=err.decode('utf-8',errors='replace')[-2000:]);return
    manifest=read(R/'wave_side_view_current.json')
    state=read(STATE)
    state.update(updated_at=stamp(),status='ready',renderer_pid=None,source=source,last_error=None,
        last_success={'at':stamp(),'field_time_s':manifest.get('time_s'),'source_file':manifest.get('source_file'),'image_path':manifest.get('image_path')},renderer_output=summary)
    write(STATE,state)
def watch():
    while True:
        started=time.monotonic()
        try:tick()
        except Exception as ex:record('refresh_error',renderer_pid=None,last_error=str(ex))
        time.sleep(max(1,CADENCE_S-(time.monotonic()-started)))
if __name__=='__main__':tick()
