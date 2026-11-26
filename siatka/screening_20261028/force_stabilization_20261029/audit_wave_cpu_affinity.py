import ctypes,json,datetime
from ctypes import wintypes as w
from pathlib import Path
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.GetSystemCpuSetInformation.argtypes=[ctypes.c_void_p,w.ULONG,ctypes.POINTER(w.ULONG),w.HANDLE,w.ULONG]
n=w.ULONG();k.GetSystemCpuSetInformation(None,0,ctypes.byref(n),None,0)
buf=ctypes.create_string_buffer(n.value)
if not k.GetSystemCpuSetInformation(buf,n,ctypes.byref(n),None,0):raise ctypes.WinError(ctypes.get_last_error())
cpu=[];off=0
while off<n.value:
 size=ctypes.c_uint32.from_buffer(buf,off).value
 if size<32:raise RuntimeError('Unexpected CPU set size')
 typ=ctypes.c_uint32.from_buffer(buf,off+4).value
 if typ==0:
  cpu.append(dict(id=ctypes.c_uint32.from_buffer(buf,off+8).value,group=ctypes.c_uint16.from_buffer(buf,off+12).value,logical_cpu=buf.raw[off+14],core_index=buf.raw[off+15],efficiency_class=buf.raw[off+18],flags=buf.raw[off+19]))
 off+=size
s=json.loads((R/'wave_foil_run_state.json').read_text());pid=s['server_pid']
k.OpenProcess.restype=w.HANDLE;k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]
k.GetProcessAffinityMask.argtypes=[w.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
k.CloseHandle.argtypes=[w.HANDLE]
h=k.OpenProcess(0x1000,False,pid)
if not h:raise ctypes.WinError(ctypes.get_last_error())
pm=ctypes.c_size_t();sm=ctypes.c_size_t()
if not k.GetProcessAffinityMask(h,ctypes.byref(pm),ctypes.byref(sm)):raise ctypes.WinError(ctypes.get_last_error())
k.CloseHandle(h)
d=dict(updated_at=datetime.datetime.now().astimezone().isoformat(),server_pid=pid,process_affinity_mask=pm.value,system_affinity_mask=sm.value,allowed_cpu=[i for i in range(64) if pm.value&(1<<i)],cpu_sets=cpu)
(R/'wave_cpu_affinity_audit.json').write_text(json.dumps(d,indent=2));print(json.dumps(d,indent=2))
