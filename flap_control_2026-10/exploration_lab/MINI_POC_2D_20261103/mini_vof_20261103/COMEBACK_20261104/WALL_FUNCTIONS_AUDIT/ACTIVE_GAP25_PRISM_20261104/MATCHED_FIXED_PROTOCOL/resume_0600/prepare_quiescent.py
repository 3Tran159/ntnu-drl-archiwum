from pathlib import Path

d=Path(__file__).resolve().parent
s=(d/"run_two_e.py").read_text(encoding="utf8")
s=s.replace("import shutil","import shutil\nimport subprocess")
s=s.replace("from run_recovery_calm_komega import protect_w06","")
start=s.index("def main():")
s=s[:start]+'''class QuiescentW06(ProtectedTwoRanks):
    case=Path(r"E:\\ntnu_mesh_optimization_20261030\\nwar_automation_20261102\\runs\\W06_20261104_100235_3b75bb")
    known=(18156,12224,13592,1336,1884,22656)

    def snapshot_now(self):
        return query(r"""
$ids=18156,12224,13592,1336,1884,22656
$process=@(Get-Process -Id $ids -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{pid=$_.Id;cpu=[double]$_.CPU;mask=$_.ProcessorAffinity.ToInt64();
        birth=$_.StartTime.ToFileTimeUtc()}
})
$os=Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{process=$process;free_GiB=$os.FreePhysicalMemory/1MB}|ConvertTo-Json -Compress -Depth 4
""")[0]

    def stamps(self):
        return tuple((p.stat().st_size,p.stat().st_mtime_ns) for p in
                     (self.case/"history.csv",self.case/"star.log",self.case/"latest_checkpoint.json"))

    def seed_idle(self):
        with (self.case/"star.log").open("rb") as f:
            f.seek(max(0,(self.case/"star.log").stat().st_size-8192))
            tail=f.read().decode("utf8",errors="replace")
        if "Connection reset" not in tail or "Server process exited with code : 1" not in tail:
            raise RuntimeError("No terminal failure record for the prior W06 run")
        self.fingerprint=self.stamps()
        self.anchor=self.snapshot_now()
        time.sleep(10)
        self.preflight()

    def preflight(self):
        if query(OWNER) or shutil.disk_usage(HERE).free<7*2**30:
            raise RuntimeError("Mini port occupied or insufficient disk space")
        self.check_inactive()

    def check_inactive(self):
        if independent_jobs():
            raise RuntimeError("An independent solver job became active")
        if self.stamps()!=self.fingerprint:
            raise RuntimeError("W06 resumed writing output")
        now=self.snapshot_now()
        initial={p["pid"]:p for p in self.anchor["process"]}
        if now["free_GiB"]<8:
            raise RuntimeError("Insufficient free RAM")
        if any(p["pid"] not in initial or p["birth"]!=initial[p["pid"]]["birth"] or
               p["cpu"]-initial[p["pid"]]["cpu"]>.35 or p["mask"]&coex.MASK for p in now["process"]):
            raise RuntimeError("W06 process activity or affinity changed")

    def poll(self, owned, out, phase):
        if self.stopped:
            return
        try:
            self.check_inactive()
        except Exception as exc:
            self.stopped=str(exc)
            if not STOP.exists():
                STOP.write_text(self.stopped,encoding="utf8")

'''+s[start:]
s=s.replace('output=D/"TWO_E_RESULT.json"','output=D/"TWO_E_QUIESCENT_RESULT.json"')
s=s.replace('marker="Independent queue/process set changed"','marker="W06 progress stalled"')
s=s.replace('or original.get("W06",{}).get("stop")!=marker or retry["status"]!="HOLD"',
'''or json.loads((D/"TWO_E_RESULT.json").read_text())["status"]!="HOLD" or retry["status"]!="HOLD"''')
s=s.replace('status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600"','status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E"')
s=s.replace('or independent_jobs()!=[("W06","running")]):','or independent_jobs()):')
s=s.replace('Get-Process -Id 18156,12224 |','Get-Process -Id 18156,12224 -ErrorAction SilentlyContinue |')
start=s.index('        guard=protect_w06(')
end=s.index('        if archived_stop.exists()',start)
s=s[:start]+'''        guard=QuiescentW06()
        guard.seed_idle()
        coex.save(D/"QUIESCENT_W06_PREFLIGHT.json",dict(w06_queue=independent_jobs(),
                  fingerprints=guard.fingerprint,initial_processes=guard.anchor,cpu_indices=cpus))
        archived_stop=D/"STOP_W06_STALL_ARCHIVED.txt"
'''+s[end:]
s=s.replace('"MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E",dict(', '"MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E_IDLE_W06",dict(')
s=s.replace('result["W06"]=dict(peak=guard.peak,stop=guard.stopped)','result["W06"]=dict(mode="quiescent_after_independent_failure",stop=guard.stopped)')
(d/"run_two_e_quiescent.py").write_text(s,encoding="utf8")

