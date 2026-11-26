from pathlib import Path
import json,subprocess,sys
R=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(R/'collect_status.py')],check=True)
a=json.loads((R/'live_summary.json').read_text())['meshes']['M03']
assert all(abs(a['window_mean_shift_pct'][k])<.5 for k in ['CD','CL_total'])
out=R/'M03_until_settled_r1';c=json.loads((out/'completed.json').read_text())
assert c['status']=='stopped_by_marker' and (out/'final.sim').exists() and (out/'velocity_vectors.csv').exists()
(out/'acceptance.json').write_text(json.dumps({'status':'settled','criterion':'Both adjacent 0.2 s window means change by less than 0.5%; user accepted this criterion without an extra confirmation window.','physical_time_s':c['time_s'],'window_mean_shift_pct':a['window_mean_shift_pct'],'windows':a['windows'],'source_completion_status':c['status']},indent=2))
p=R/'ContinueUntilSettled.java';s=p.read_text()
s=s.replace('if(steps%Math.max(1,(int)Math.round(.2/dt))==0&&t>=1.0-dt*.1)','if(steps%10==0&&t>=1.0-dt*.1)')
s=s.replace('consecutivePasses>=2','consecutivePasses>=1')
s=s.replace('&&Math.abs(shift)<.5&&relrms<1&&Math.abs(drift)<1','&&Math.abs(shift)<.5')
s=s.replace('require two consecutive passing evaluations spaced 0.2 s.','stop at the first passing evaluation. RMS and drift are diagnostic only.')
s=s.replace('long start=System.nanoTime();int steps=0;', '''String priorPath=System.getenv("NTNU_STAB_PRIOR_HISTORY");
      if(priorPath!=null&&!priorPath.isBlank()){
        List<String> lines=Files.readAllLines(Paths.get(priorPath));List<String> keys=Arrays.asList(lines.get(0).split(","));
        int ti=keys.indexOf("physical_time_s"),di=keys.indexOf("CD"),li=keys.indexOf("CL_total");
        for(String line:lines.subList(Math.max(1,lines.size()-500),lines.size())){String[] v=line.split(",");if(v.length>Math.max(ti,Math.max(di,li)))samples.add(new double[]{Double.parseDouble(v[ti]),Double.parseDouble(v[di]),Double.parseDouble(v[li])});}
      }
      long start=System.nanoTime();int steps=0;''')
p.write_text(s)
p=R/'run_until_settled.py';s=p.read_text()
s=s.replace("'INIT':str(j.get('initialize',False)).lower()","'INIT':str(j.get('initialize',False)).lower(),'PRIOR_HISTORY':j.get('prior_history','')")
s=s.replace("if prior:\n                c=", """accepted=read(ROOT/(mesh+'_until_settled_r1')/'acceptance.json',{})
            if accepted.get('status')=='settled':
                results.append({'id':mesh+'_until_settled_r1','status':'completed','acceptance':accepted});continue
            if prior:
                c=""")
s=s.replace("'start':c['time_s'],'cells':","'start':c['time_s'],'prior_history':str(ROOT/prior/'history.csv'),'cells':")
s=s.replace("folder=BASE/'quasi2d_012_20261029/M04'\n                start=time.time()","""folder=BASE/'quasi2d_012_20261029/M04'
                repair_start=time.time()
                while (ROOT/'M04_REPAIR_IN_PROGRESS').exists():
                    if time.time()-repair_start>3600:raise RuntimeError('M04 repair still incomplete')
                    write(ROOT/'queue_state.json',{'status':'running','active':'M04 mesh repair','updated_at':stamp()});refresh();time.sleep(20)
                start=time.time()""")
p.write_text(s)
(R/'M04_REPAIR_IN_PROGRESS').touch()
p=R/'build_dashboard_en.py';s=p.read_text()
s=s.replace("complete=result.get('completed',{}).get('status')=='stabilized'","complete=result.get('completed',{}).get('status')=='stabilized' or bool(j and read(R/j['id']/'acceptance.json',{}).get('status')=='settled')")
s=s.replace("'Pass × 2' if complete","'Pass' if complete")
s=s.replace('Automatic stop after two consecutive passing settling checks.','Automatic stop when both mean coefficient changes are below 0.5%.')
s=s.replace('Require mean CD and CL changes below 0.5%, fluctuation RMS below 1% of the mean, and within-window endpoint drift below 1%. The solver stops after two passing evaluations 0.2 s apart.','Require mean CD and CL changes below 0.5%. The solver stops at the first passing evaluation. RMS and within-window drift remain diagnostics.')
p.write_text(s)
print(json.dumps({'M03_accepted_time_s':c['time_s'] if False else a['last']['physical_time_s'],'changes_pct':a['window_mean_shift_pct']}))
