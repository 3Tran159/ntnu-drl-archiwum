from pathlib import Path

d=Path(__file__).resolve().parent
s=(d/"run_two_e_quiescent.py").read_text(encoding="utf8")
s=s.replace("import subprocess","import csv\nimport sqlite3\nimport statistics")
s=s.replace("from run_day import HERE, LOCK, STOP, OWNER, READ, independent_jobs, new_job, query, sha",
            "from run_day import HERE, LOCK, STOP, OWNER, READ, FOREIGN_QUEUE, new_job, query, sha")
start=s.index("class QuiescentW06")
end=s.index("def main():",start)
s=s[:start]+'''class ResourceGuard(ProtectedTwoRanks):
    baseline_s=1.6459431500006758

    def __init__(self):
        super().__init__()
        self.watch=None
        self.last_poll=0
        self.last_sample=None

    def resources(self):
        return query(r"""
$os=Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{free_GiB=$os.FreePhysicalMemory/1MB}|ConvertTo-Json -Compress
""")[0]

    def preflight(self):
        if query(OWNER) or shutil.disk_usage(HERE).free<7*2**30:
            raise RuntimeError("Mini port occupied or insufficient disk space")
        if self.resources()["free_GiB"]<8:
            raise RuntimeError("Insufficient free RAM")
        self.observe_w06()

    def observe_w06(self):
        with sqlite3.connect(FOREIGN_QUEUE.as_uri()+"?mode=ro",uri=True,timeout=3) as db:
            jobs=db.execute("SELECT folder FROM jobs WHERE case_id='W06' AND status='running'").fetchall()
        if not jobs:
            return
        if len(jobs)!=1:
            raise RuntimeError("Multiple W06 jobs are simultaneously running")
        folder=Path(jobs[0][0])
        file=folder/"history.csv"
        if not file.is_file() or time.time()-file.stat().st_mtime>12:
            return
        log=folder/"star.log"
        if log.is_file():
            with log.open("rb") as f:
                import re
                ids=set(int(p) for p in re.findall(rb"(?m)^Process rank \\d+\\s+\\S+\\s+(\\d+)\\s*$",f.read(65536)))
            if ids:
                arg=",".join(str(p) for p in sorted(ids))
                masks=query(f"(Get-Process -Id {arg} -ErrorAction SilentlyContinue | ForEach-Object {{$_.ProcessorAffinity.ToInt64()}}) | ConvertTo-Json -Compress")
                if any(mask & coex.MASK for mask in masks):
                    raise RuntimeError("Active W06 solver affinity overlaps the selected Mini E-cores")
        with file.open("rb") as f:
            f.seek(0,2)
            f.seek(max(0,f.tell()-18000))
            rows=f.read().decode("utf8",errors="replace").splitlines()[1:]
        steps=[]
        for row in rows:
            values=row.split(",")
            try:
                steps.append((int(values[1]),float(values[2])))
            except (ValueError,IndexError):
                continue
        if len(steps)<8:
            return
        recent=steps[-8:]
        sample=(str(folder),recent[-1][0])
        if sample==self.last_sample or any(b[0]!=a[0]+1 or b[1]<=a[1] for a,b in zip(recent,recent[1:])):
            return
        self.last_sample=sample
        seconds=statistics.median(b[1]-a[1] for a,b in zip(recent,recent[1:]))
        slowdown=seconds/self.baseline_s-1
        self.peak=max(self.peak,slowdown)
        if self.watch:
            with self.watch.open("a",encoding="ascii",newline="") as f:
                csv.writer(f).writerow((time.strftime("%H:%M:%S"),sample[1],seconds,slowdown))
        if slowdown>.15:
            raise RuntimeError(f"W06 seven-step median slower by {slowdown:.1%}")

    def poll(self, owned, out, phase):
        if self.stopped or time.monotonic()-self.last_poll<5:
            return
        self.last_poll=time.monotonic()
        try:
            if self.resources()["free_GiB"]<8:
                raise RuntimeError("Insufficient free RAM")
            self.observe_w06()
        except Exception as exc:
            self.stopped=str(exc)
            if not STOP.exists():
                STOP.write_text(self.stopped,encoding="utf8")

'''+s[end:]
s=s.replace('output=D/"TWO_E_QUIESCENT_RESULT.json"','output=D/"TWO_E_COEX_RESULT.json"')
s=s.replace('marker="W06 progress stalled"','marker="An independent solver job became active"')
s=s.replace('status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E"\n        or independent_jobs()):',
            'status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E_IDLE_W06"):')
start=s.index('        guard=QuiescentW06()')
end=s.index('        if archived_stop.exists()',start)
s=s[:start]+'''        guard=ResourceGuard()
        guard.watch=D/"TWO_E_COEX_W06_WATCH.csv"
        guard.preflight()
        with guard.watch.open("x",encoding="ascii") as f:
            f.write("time,W06_step,median_step_s,slowdown_fraction\\n")
        archived_stop=D/"STOP_W06_QUEUE_PRESENCE_ARCHIVED.txt"
'''+s[end:]
s=s.replace('MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E_IDLE_W06",dict(', 'MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E_COEX",dict(')
s=s.replace('dict(mode="quiescent_after_independent_failure",stop=guard.stopped)',
            'dict(mode="measured_resource_protection",peak=guard.peak,stop=guard.stopped)')
(d/"run_two_e_coex.py").write_text(s,encoding="utf8")

