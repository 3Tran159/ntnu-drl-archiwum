from pathlib import Path
import json,hashlib,subprocess
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
s=(R/'CampaignFoilWave.java').read_text().replace('public class CampaignFoilWave','public class W01aCalmStartR1')
anchor='  scalarScene("12 Free-surface close-up - water fraction",mid,ff("VolumeFractionwater"),-5,2,1.2,false,0,1);'
if s.count(anchor)!=1:raise RuntimeError('Unexpected scene anchor')
s=s.replace(anchor,anchor+'\n  if(s.getFieldFunctionManager().hasFunction("Vorticity")){scalarScene("13 Signed vorticity - upstream foil and wake [1 per s]",mid,ff("Vorticity").getComponentFunction(1),2,0,2.2,false,-200,200);scalarScene("14 Signed vorticity - foil detail [1 per s]",mid,ff("Vorticity").getComponentFunction(1),.6,0,.8,false,-1000,1000);Files.writeString(out.resolve("vorticity_definition.json"),json(Map.of("field","Vorticity","component",1,"meaning","omega_y = du_x/dz - du_z/dx, signed normal-to-slice vorticity; units 1/s. Display ranges can be adjusted; neither circulation nor particle paths.","native_scenes",true)));}else Files.writeString(out.resolve("vorticity_unavailable.txt"),"Native Vorticity field unavailable; no surrogate circulation claim.");')
anchor2='fields.add(v.getMagnitudeFunction());tab.setFieldFunctions(fields);'
if s.count(anchor2)!=1:raise RuntimeError('Unexpected snapshot anchor')
s=s.replace(anchor2,'fields.add(v.getMagnitudeFunction());if(s.getFieldFunctionManager().hasFunction("Vorticity"))fields.add(ff("Vorticity").getComponentFunction(1));tab.setFieldFunctions(fields);')
(R/'W01aCalmStartR1.java').write_text(s,encoding='utf8')
base='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java'
cp=';'.join(base+'/'+x for x in ['platform/modules/ext/*','platform/modules/*','platform/core/*'])
folder=R/'w01a_calm_macro_classes';folder.mkdir(exist_ok=True)
p=subprocess.run([r'C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','--release','17','-cp',cp,'-d',str(folder),str(R/'W01aCalmStartR1.java')],capture_output=True,text=True)
(R/'w01a_calm_compile.log').write_text(p.stdout+p.stderr)
receipt=dict(status='javac_passed' if p.returncode==0 else 'failed',macro_sha256=hashlib.sha256((R/'W01aCalmStartR1.java').read_bytes()).hexdigest())
(R/'w01a_macro_build_receipt.json').write_text(json.dumps(receipt,indent=2))
if p.returncode:print(p.stderr);raise SystemExit(p.returncode)
controller=(R/'run_manual_wave.py').read_text().replace('import ctypes,json,','import ctypes,csv,statistics,json,')
controller=controller.replace("if request.parent!= (R/'manual_requests').resolve() or not request.name.endswith('.json'):","if request!= (R/'w01a_calm_request_r1.json').resolve():")
controller=controller.replace("receipt=c.read(R/'manual_macro_build_receipt.json')","receipt=c.read(R/'w01a_macro_build_receipt.json')")
controller=controller.replace('ManualFoilWave','W01aCalmStartR1')
controller=controller.replace("case=W/('MANUAL_'+pset['id']+'_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6])","case=W/'W01a_W20L4_M10_calm_start_r1'\n if case.exists():raise RuntimeError('Unique W01a attempt exists; never restart it')")
controller=controller.replace("own=R/'manual_wave_controller.lock'","own=R/'w01a_calm_start_r1.lock'")
controller=controller.replace("scope=pset['label']+'; manual exploratory run'","scope='W01a stage1: fresh calm settling before inlet-generated FifthOrder wave; no wave yet',computation_stage='calm_settling'")
controller=controller.replace("state('manual_wave_GPU_running',","state('W01a_calm_GPU_running',computation_active=True,")
controller=controller.replace("state('manual_run_saved_pending_review' if ok else 'needs_review',result=result,progress=done)","state('W01a_calm_saved_pending_wave_setup' if ok else 'needs_review',result=result,progress=done,computation_active=False)")
controller=controller.replace("NTNU_WAVE_WALL_S=str(wall))","NTNU_WAVE_WALL_S=str(wall),NTNU_CFG_XMIN='-35',NTNU_CFG_XMAX='45',NTNU_CFG_LAMBDA='20',NTNU_CFG_GAUGES='-10,-5,2.5,5,10,15,20')")
anchor3="    if now-last_update>40:"
if controller.count(anchor3)!=1:raise RuntimeError('Unexpected analysis anchor')
screen="""    if (case/'history.csv').exists() and pt>=.42 and not (case/'STOP').exists():
     try:
      rows=list(csv.DictReader((case/'history.csv').open()))
      end=float(rows[-1]['time_s']);old=[r for r in rows if end-.4<float(r['time_s'])<=end-.2];new=[r for r in rows if end-.2<float(r['time_s'])<=end+1e-10]
      if len(old)>=199 and len(new)>=199:
       means={key:[statistics.mean(float(r[key]) for r in win) for win in [old,new]] for key in ['CD','CL_total']}
       changes={key:100*(v[1]-v[0])/max(abs(v[1]),1e-12) for key,v in means.items()}
       passed=all(abs(v)<.5 for v in changes.values())
       e.write(case/'calm_settling.json',dict(time_s=end,windows_s=[[end-.4,end-.2],[end-.2,end]],means=means,changes_pct=changes,passed=passed,threshold_pct=.5,source_history='history.csv'))
       if passed:
        (case/'STOP').touch();e.write(case/'calm_stop_decision.json',dict(reason='first_pass_adjacent_0p2s_means',time_s=end,changes_pct=changes));reason='calm_settled'
     except (ValueError,KeyError,IndexError):pass
"""
controller=controller.replace(anchor3,screen+anchor3)
# Only this controller and its own descendants may use the preferred P cores.
controller=controller.replace("started=time.time();last_pt=0;","k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]\n  if not k.SetProcessAffinityMask(k.GetCurrentProcess(),3):raise RuntimeError('Cannot apply requested CPU0/1 affinity')\n  started=time.time();last_pt=0;")
(R/'run_w01a_calm_start_r1.py').write_text(controller,encoding='utf8')
request=dict(preset='C01_M10',target_s=6,wall_minutes=720,requested_at='User explicitly requested W01a restart: calm then inlet-generated wave')
(R/'w01a_calm_request_r1.json').write_text(json.dumps(request,indent=2))
compile(controller,'run_w01a_calm_start_r1.py','exec')
print(json.dumps({'macro':receipt,'controller_compile':True,'case':'W01a_W20L4_M10_calm_start_r1','stage':'calm only; wave onset pending reviewed inlet-front setup'},indent=2))
