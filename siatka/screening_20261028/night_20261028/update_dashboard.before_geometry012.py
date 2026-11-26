"""Embed measured results in every user-facing HTML entry point; no fetch/CORS."""
import argparse,csv,json,re,time
from datetime import datetime,timezone
from pathlib import Path

def read_json(path,default=None):
    try:return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return default

def atomic_text(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.new');temp.write_text(text,encoding='utf-8');temp.replace(path)

def work_events(night,records,cfdroot):
    events=read_json(night/'work_log.json',[]) or []
    observed=read_json(night/'automatic_work_log.json',[]) or []
    def add(id,stamp,kind,work,finding='',challenge='',next_step=''):
        events.append(dict(id=id,time=datetime.fromtimestamp(stamp,timezone.utc).isoformat(),kind=kind,work=work,finding=finding,challenge=challenge,next_step=next_step))
    for record,stage,path in records:
        metrics=record.get('metrics',{});case=record['case_id']
        coverage=metrics.get('foil_area_fraction_full_15_prism_layers')
        finding=f"{metrics.get('cell_count',0):,} komórek"+(f"; pełne 15 warstw na {100*coverage:.3f}% powierzchni foila." if coverage is not None else '.')
        add('mesh:'+case,path.stat().st_mtime,'mesh','Zapisano pomiar siatki '+case,finding,'Cel 99,9% nieosiągnięty.' if coverage is not None and coverage<.999 else '', 'Ocena lokalnych warstw i test CFD; sam pomiar siatki nie potwierdza dokładności.')
    if cfdroot.exists():
        for directory in cfdroot.iterdir():
            if not directory.is_dir():continue
            process=read_json(directory/'process.json')
            if process:
                add('start:'+directory.name,process['start_unix'],'cfd','Uruchomiono '+directory.name,f"CPU: {process.get('processes')} procesy; 18 m/s; Double.",'','Inicjalizacja, pomiar RAM i kontrola postępu.')
            history_path=directory/'history.csv'
            if history_path.exists():
                with history_path.open() as stream:history=list(csv.DictReader(stream))
                if history and all(history[-1].get(k) for k in ['wall_seconds','physical_time_s','iteration']):
                    latest=history[-1];bucket=int(float(latest['wall_seconds'])//900);id=f'progress:{directory.name}:{bucket}'
                    if id not in {e['id'] for e in observed}:
                        observed.append(dict(id=id,time=datetime.now(timezone.utc).isoformat(),kind='progress',work='Odczyt postępu: '+directory.name,finding=f"Iteracja {latest['iteration']}; czas fizyczny {latest['physical_time_s']} s; max prędkość {latest.get('max_velocity_m_s')} m/s; max CFL {latest.get('max_convective_CFL')}.",challenge='To rozruch / test stabilności; nie potwierdza zbieżności sił.',next_step='Kontynuować do limitu czasu lub zadziałania zabezpieczenia.'))
            result=read_json(directory/'controller_result.json')
            if result:
                status=result.get('status','unknown');memory=result.get('min_free_gib');measure=result.get('measurement',{})
                detail='Status: '+status+(f"; minimum wolnego RAM {memory:.2f} GiB." if memory is not None else '.')
                if measure:detail+=f" Czas fizyczny: {measure.get('physical_time_s')} s."
                failed=status!='completed'
                add('end:'+directory.name,result.get('end_unix',(directory/'controller_result.json').stat().st_mtime),'problem' if failed else 'cfd','Zakończono próbę '+directory.name,detail,'Próba nie zaliczyła kryteriów wykonania.' if failed else '', 'Weryfikacja przyczyny przed powtórzeniem.' if failed else 'Porównać ten sam czas fizyczny między siatkami; wynik nie oznacza zbieżności.')
            finished=read_json(directory/'queue_finished.json')
            if isinstance(finished,dict):
                add('queue:'+directory.name,finished.get('finished_unix',(directory/'queue_finished.json').stat().st_mtime),'queue','Kolejka zakończona: '+directory.name,f"Zapisano {len(finished.get('results',[]))} wyników prób.",'','Sprawdzić status każdego przypadku, checkpointy i historię.')
    atomic_text(night/'automatic_work_log.json',json.dumps(observed,ensure_ascii=False,indent=2)+'\n')
    return sorted({e['id']:e for e in events+observed}.values(),key=lambda e:e['time'],reverse=True)

def build(root):
    root=Path(root);records=[]
    pilot=list((root/'pilot_v3').glob('A*/latest.json'))
    if not pilot:pilot=list((root/'results/cases').glob('A*/record.json'))
    for p in sorted(pilot):records.append((json.loads(p.read_text(encoding='utf-8-sig')),'surface pilot',p))
    night=root/'night_20261028'
    for p in sorted(night.glob('*/measurement.json')):
        if re.fullmatch('[BD][0-9]{3}',p.parent.name):records.append((json.loads(p.read_text(encoding='utf-8-sig')),'prism/resource pilot',p))
    if not any(stage=='prism/resource pilot' for _,stage,_ in records):
        for p in sorted((night/'results').glob('*/measurement.json')):records.append((json.loads(p.read_text()),'prism/resource pilot',p))
    rows=[];metrics=set()
    for r,stage,path in records:
        m=r.get('metrics',{});metrics.update(m)
        params=r.get('readback_after_mesh',{}).get('parameters_m',r.get('parameters_m',{}))
        reason='Prism topology/local resolution/CFD verification pending';quality='incomplete'
        if r['case_id']=='B001':reason='EQP: reduced full-stack coverage and 3 cells above 85 degrees; excluded from night selection';quality='rejected'
        checks='pass' if m.get('invalid_cells')==0 and m.get('min_cell_volume_m3',0)>0 and m.get('min_face_validity',0)>=.95 else 'fail_or_missing'
        row=dict(mesh_checks=checks,case_id=r['case_id'],stage=stage,generation_status=r['generation_status'],quality_status=quality,pareto=False,failure_reason=reason,**params,**m)
        rows.append(row)
    cfd=[]
    cfdroot=Path(r'E:\ntnu_cfd_night_20261028')
    if cfdroot.exists():
        for directory in sorted(cfdroot.iterdir()):
            if not directory.is_dir() or not (directory/'process.json').exists():continue
            process=json.loads((directory/'process.json').read_text());result=json.loads((directory/'controller_result.json').read_text()) if (directory/'controller_result.json').exists() else {}
            row={'case':directory.name,'processes':process.get('processes'),'status':result.get('status','started; outcome pending'),'min_free_ram_gib':result.get('min_free_gib')}
            resources=read_json(directory/'resources.json',[]) or []
            if resources:
                row['min_free_ram_gib']=min(s['free_physical_bytes'] for s in resources)/1024**3
                row['current_free_ram_gib']=resources[-1]['free_physical_bytes']/1024**3
                row['last_resource_update']=datetime.fromtimestamp(resources[-1]['time_unix'],timezone.utc).isoformat()
            log=directory/'star.log'
            if log.exists() and not result:
                with log.open('rb') as stream:
                    stream.seek(max(0,log.stat().st_size-16000));tail=stream.read().decode('utf-8',errors='replace')
                iterations=re.findall(r'^\s*(\d+)\s+[-+\d.]+[Ee][-+]?\d+',tail,re.M)
                row['status']='solver running' if iterations else 'loading / initializing'
                if iterations:row['inner_iteration']=int(iterations[-1])
            if (directory/'history.csv').exists():
                with (directory/'history.csv').open() as stream:history=list(csv.DictReader(stream))
                if history:
                    for key in ['physical_time_s','iteration','Fx_half_N','Fz_half_N','max_velocity_m_s','max_convective_CFL','foil_mean_yplus']:row[key]=float(history[-1][key])
            cfd.append(row)
        manifest=read_json(night/'overnight_manifest.json',{}) or {}
        finished=read_json(cfdroot/'overnight_queue/queue_finished.json')
        for job_path in manifest.get('jobs',[]):
            job=read_json(Path(job_path),{}) or {};case=Path(job.get('output','')).name
            if case and not any(r['case']==case for r in cfd):
                cfd.append({'case':case,'processes':job.get('processes'),'status':'not attempted; queue ended' if finished else 'queued'})
    events=work_events(night,records,cfdroot)
    data={'generated_at':datetime.now(timezone.utc).isoformat(),'work_log':events,'current_activity':read_json(night/'current_activity.json',{}),'night_summary':read_json(night/'nightly_summary.json',{}),'cfd_runs':cfd,'rows':rows,'parameters':['foil_target_m','hf_fine_factor','core_aspect_ratio','enhanced_prisms'],'metrics':sorted(metrics)}
    template=(root/'dashboard_template.html').read_text(encoding='utf-8');payload=json.dumps(data,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    html=template.replace('/*__DATA__*/null',payload)
    if '/*__DATA__*/null' in html or not rows:raise ValueError('Refuse to publish an empty dashboard')
    destinations=[root/'dashboard.html',root/'results/dashboard.html']
    if (root/'delivery').exists():
        for folder in (root/'delivery').iterdir():
            if folder.is_dir() and folder.name.startswith('NTNU_mesh_screening'):
                destinations.extend([folder/'dashboard.html',folder/'results/dashboard.html'])
    for p in destinations:atomic_text(p,html)
    atomic_text(night/'all_measured_meshes.json',json.dumps(data,indent=2)+'\n')
    atomic_text(night/'work_log_export.json',json.dumps(events,ensure_ascii=False,indent=2)+'\n')
    print('Dashboard updated:',len(rows),'measured cases;',len(destinations),'entry points')
    return html,data
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);a=ap.parse_args();build(a.root)
