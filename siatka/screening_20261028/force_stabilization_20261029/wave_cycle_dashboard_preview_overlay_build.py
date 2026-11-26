"""Isolated overlay fixtures and checks; never campaign evidence."""
import csv,json,math
from pathlib import Path
import wave_cycle_dashboard_panel as ui
import wave_cycle_repeatability as evaluator
R=Path(__file__).resolve().parent
OUT=R/'wave_cycle_dashboard_preview_overlay_fixtures';OUT.mkdir(exist_ok=True)
policy={'min_cycles':4,'typical_cycles':10,'max_cycles':20}
def fixture(name,end,drift=False):
 points=[]
 for i in range(20,int(round(end*1000))+1):
  t=i/1000;phase=2*math.pi*t+(.08*t if drift else 0)
  points.append((t,.01+.002*math.sin(phase)+(0 if drift else .0001*t),.2+.04*math.sin(phase)+(0 if drift else .003*t),None,None))
 path=OUT/(name+'.csv')
 with path.open('w',newline='') as f:
  writer=csv.writer(f);writer.writerow(['time_s','CD','CL_total'])
  writer.writerows(p[:3] for p in points)
 a=evaluator.evaluate([path],1,4,20);a['case']='SYNTHETIC_UI_'+name
 state={'case':a['case'],'status':'preview_only','progress':{'time_s':end},'period_s':1,'computation_active':False}
 content=ui.render(state,a,{'initial_time_s':.168,'period_s':1},points=points,policy=policy)
 content=content.replace('<h2>Wave forces','<p style="font-weight:bold;color:#8b2900">SYNTHETIC UI PREVIEW — not calculation results</p><h2>Wave forces',1)
 content=content.replace('<div class="wcp-cycle-comparison">','<div class="wcp-cycle-comparison"><p style="font-weight:bold;color:#8b2900">SYNTHETIC UI PREVIEW — not calculation results</p>',1)
 html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic cycle overlap QA</title><body style="margin:0;padding:20px;background:#eef2f5"><main style="max-width:1420px;margin:auto">'+content+'</main></body></html>'
 (R/('wave_cycle_dashboard_preview_overlay_'+name+'.html')).write_text(html,encoding='utf8')
 return points,a,ui._cycle_display(points,a,1)
one=fixture('one',2.4);two=fixture('two',3.4);four=fixture('four',5.4);drift=fixture('phase_drift',3.4,True)
p,a,v=two;mutated=[(t,cd+100,cl-100,fx,fz) if t>3.001 else (t,cd,cl,fx,fz) for t,cd,cl,fx,fz in p]
altered=ui._cycle_display(mutated,a,1)
gappy=[point for point in p if not 2.45<point[0]<2.47]
gapview=ui._cycle_display(gappy,a,1)
raw=v['differences'][0]['coefficients']
checks={
 'one_complete_with_no_deviation':len(one[2]['cycles'])==1 and not one[2]['differences'],
 'two_complete_before_four':len(v['cycles'])==2 and len(v['differences'])==1,
 'original_cycle_numbers':[c['cycle'] for c in v['cycles']]==[2,3],
 'four_latest_complete':[c['cycle'] for c in four[2]['cycles']]==[2,3,4,5],
 'current_partial_excluded':v['partial']['cycle']==4 and v['differences']==altered['differences'],
 'fixed_phase_raw_CD_delta':max(abs(x+.0001) for x in raw['CD']['values'])<1e-12,
 'fixed_phase_raw_CL_delta':max(abs(x+.003) for x in raw['CL_total']['values'])<1e-12,
 'raw_CD_RMS_and_max':abs(raw['CD']['rms']-.0001)<1e-12 and abs(raw['CD']['max_abs']-.0001)<1e-12,
 'raw_CL_RMS_and_max':abs(raw['CL_total']['rms']-.003)<1e-12 and abs(raw['CL_total']['max_abs']-.003)<1e-12,
 'phase_drift_not_realigned':drift[2]['differences'][0]['coefficients']['CD']['rms']>0.00005,
 'gap_excludes_full_cycle':not gapview['differences'] and any(c['cycle']==3 for c in gapview['excluded']),
 'acceptance_not_synthesized_before_four':two[1]['comparisons']=={} and not two[1]['latest_four_complete']
}
record={'synthetic_fixture_only':True,'pass':all(checks.values()),'checks':checks,'two_cycle_raw':{key:{k:val for k,val in x.items() if k!='values'} for key,x in raw.items()},'phase_drift_raw_CD_RMS':drift[2]['differences'][0]['coefficients']['CD']['rms']}
(R/'wave_cycle_dashboard_preview_overlay_science_qa.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps(record))
