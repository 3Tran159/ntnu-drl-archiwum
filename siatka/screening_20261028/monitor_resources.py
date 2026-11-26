"""Sample STAR processes associated with each encoded case session on Windows.

Read-only monitor, separate from result acceptance. Sum of process working sets
can double-count shared pages and excludes the GUI client without an encoded
session argument. Sample maxima are not true process high-water marks.
"""
import argparse
import base64
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-pid',type=int,required=True)
    parser.add_argument('--runs',type=Path,required=True)
    parser.add_argument('--interval',type=float,default=15)
    args=parser.parse_args()
    if os.name!='nt' or args.root_pid<=0 or args.interval<5:
        raise SystemExit('Windows, positive owned PID and interval >=5 seconds required')
    args.runs.mkdir(parents=True,exist_ok=True)
    output=args.runs/'resource_samples.csv'
    metadata={'method':'Win32_Process.WorkingSetSize summed for STAR processes whose command line contains the exact Base64 encoded baseline_copy.sim path of the latest owned case','interval_s':args.interval,'limitations':'Shared pages may be counted more than once. Client without encoded session is excluded. Sampled maximum only, not true peak. System free physical memory from Win32_OperatingSystem.','root_process_id':args.root_pid}
    (args.runs/'resource_method.json').write_text(json.dumps(metadata,indent=2)+'\n')
    with output.open('x',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['time_utc','case_id','star_working_set_bytes','free_physical_bytes','matched_star_processes'])
        while True:
            jobs=sorted(args.runs.glob('A*/attempt_*/job.json'),key=lambda p:p.stat().st_ctime)
            job=jobs[-1] if jobs else None
            enc=base64.b64encode(str(job.parent/'baseline_copy.sim').encode()).decode() if job else 'NO_JOB'
            script=f"if(-not (Get-Process -Id {args.root_pid} -ErrorAction SilentlyContinue)){{Write-Output '{{\"done\":true}}';exit}}; $e='{enc}'; $p=@(Get-CimInstance Win32_Process | Where-Object {{$_.Name -match '^star-?ccm\\+\\.exe$' -and $_.CommandLine -like ('*'+$e+'*')}}); [PSCustomObject]@{{memory=($p|Measure-Object WorkingSetSize -Sum).Sum;free=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory*1024;count=$p.Count}}|ConvertTo-Json -Compress"
            result=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,timeout=30,check=True)
            data=json.loads(result.stdout)
            if data.get('done'):break
            case=json.loads(job.read_text())['case_id'] if job else 'none'
            writer.writerow([datetime.now(timezone.utc).isoformat(),case,int(data.get('memory') or 0),int(data['free']),data['count']]);stream.flush()
            time.sleep(args.interval)
    print('Resource sampling completed:',output)

if __name__=='__main__':main()
