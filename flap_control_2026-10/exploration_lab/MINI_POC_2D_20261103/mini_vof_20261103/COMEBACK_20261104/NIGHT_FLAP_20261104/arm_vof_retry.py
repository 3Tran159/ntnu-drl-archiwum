from pathlib import Path
p=Path(__file__).with_name("vof_timestep_retry.py")
s=p.read_text().replace("import os","import os\nimport sys",1)
s=s.replace('if __name__=="__main__":\n    if STOP', '''if __name__=="__main__":
    if len(sys.argv)==2:
        prior_pid=int(sys.argv[1])
        while LOCK.exists() and not STOP.exists() and END-time.time()>1200:
            if LOCK.read_text().strip()!=str(prior_pid):
                raise RuntimeError("A different owner holds the controller lock")
            owners=query(f"(Get-Process -Id {prior_pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress")
            if owners!=[prior_pid]:
                raise RuntimeError("Previous owner ended without releasing its lock")
            time.sleep(20)
    if STOP''')
p.write_text(s)
