from pathlib import Path
import subprocess,json,datetime,py_compile,shutil
h=Path(__file__).resolve().parents[1]
s=(h/'macros/PrepareC0OverlapPatch.java').read_text(encoding='utf8').replace('class PrepareC0OverlapPatch','class PrepareC0OverlapBand').replace('c0_overlap_patch05mm_"+id','c0_overlap_band05mm_"+id')
s=s.replace('"C0 local donor stencil patch 0p5mm",new double[]{.752,-.1,-.043},new double[]{.766,.1,-.028},.0005,base','"C0 inner overlap band 0p5mm",new double[]{.74,-.1,-.08},new double[]{.955,.1,.13},.0005,base')
s=s.replace('Local patch0.5mm at x[.752,.766],z[-.043,-.028]m surrounds the one difficult stencil from the1mm candidate.','Inner overlap band0.5mm at x[.74,.955],z[-.08,.13]m covers both identified difficult-stencil locations and the previous turbulence anomaly zone. Outer1mm control retained; background unchanged.')
p=h/'macros/PrepareC0OverlapBand.java';p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8').replace("'PrepareC0OverlapPatch.java':8}","'PrepareC0OverlapPatch.java':8,'PrepareC0OverlapBand.java':8}");assert "'PrepareC0OverlapBand.java':8" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8').replace("'PrepareC0OverlapPatch.java'}","'PrepareC0OverlapPatch.java','PrepareC0OverlapBand.java'}").replace("'PrepareC0OverlapPatch.java':'c0_overlap_patch05mm_',","'PrepareC0OverlapBand.java':'c0_overlap_band05mm_','PrepareC0OverlapPatch.java':'c0_overlap_patch05mm_',");p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8').replace("case={'PrepareC0OverlapPatch.java'","case={'PrepareC0OverlapBand.java':'C0 — poprawa rozdzielczości całej wewnętrznej strefy nakładania0,5mm','PrepareC0OverlapPatch.java'");p.write_text(s,encoding='utf8')
for name in ['night_queue.py','night_native.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_overlap_inner_band',macro='PrepareC0OverlapBand.java',input=str(h/'cases/SP_C_split0_overset/SP_C_build_error_20261102_191807.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='Broaden0.5mm inner-overlap region x[.74,.955],z[-.08,.13], preserving outer1mm region and background mesh. Cover both identified difficult-stencil locations and prior turbulence anomaly zone; DISTANCE, strict zero-error/fallback gate,750k cell cap, no flow.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg.setdefault('release_failure_hold',{})['c0_overlap_local_patch']='Original type4 point atx.758664 resolved; one new type4 atx.8943489,z-.0212401,quality.3857,ratio1.234. Broaden inner-overlap refinement to address the region, no guard relaxation.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_overlap_band_remedy',job=job,previous_cells=425762,previous_min_quality=.06104818624018234,scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' Local0.5mm patch resolved original difficult stencil but a new type4 occurred atx.8943489,z-.0212401. Mesh425762, positive volumes, no native errors, minQ.0610482. Do not solve. Broaden inner-overlap0.5mm band covering both sites and original anomaly zone; keep background and geometry.750k cap/8CPU, all gates unchanged.\n')
print(json.dumps(ev,indent=2))
