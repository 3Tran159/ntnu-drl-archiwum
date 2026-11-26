"""Isolated UI preview only; synthetic data are never campaign evidence."""
import math
from pathlib import Path
import wave_cycle_dashboard_panel as panel
R=Path(__file__).resolve().parent;T=0.8472673206891129
state={'case':'SYNTHETIC_UI_PREVIEW','status':'preview_only','computation_active':False,'progress':{'time_s':5*T}}
cycles=[]
for cycle in range(2,6):
 cycles.append({'cycle':cycle,'complete':True,'coefficients':{k:{'phase_grid_values':[base+amp*math.sin(2*math.pi*j/256+(cycle-2)*.003) for j in range(256)]} for k,base,amp in [('CD',.01,.002),('CL_total',.2,.04)]}})
metrics={'mean_pct':.1,'fundamental_amplitude_pct':.8,'half_peak_to_peak_pct':.7,'waveform_rms_pct':1.2,'phase_deg':.5}
a={'case':state['case'],'min_cycles':4,'max_cycles':20,'period_s':T,'observed_time_s':5*T,'elapsed_wave_periods':5,'valid_complete_cycles':[2,3,4,5],'latest_four_complete':True,'history_quality_pass':True,'stop_for_repeatability':True,'last_four_cycles':cycles,'point_count_per_cycle':256,'thresholds':{'mean_pct':.5,'amplitude_pct':2,'waveform_rms_pct':3,'phase_deg':2},'comparisons':{k:{'pass':True,'phase_applicable':True,'worst_pair_metrics':metrics} for k in ['CD','CL_total']}}
points=[(i*5*T/1000,.01+.002*math.sin(i*10*math.pi/1000),.2+.04*math.sin(i*10*math.pi/1000),40+8*math.sin(i*10*math.pi/1000),800+160*math.sin(i*10*math.pi/1000)) for i in range(1001)]
content=panel.render(state,a,{'initial_time_s':.168,'period_s':T},points=points,policy={'min_cycles':4,'typical_cycles':10,'max_cycles':20})
content=content.replace('<h2>Wave forces', '<p style="font-weight:bold;color:#8b2900">SYNTHETIC UI PREVIEW — not calculation results</p><h2>Wave forces',1)
(R/'wave_cycle_dashboard_preview_four_cycles.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic UI preview</title><body style="margin:0;padding:20px;background:#eef2f5"><main style="max-width:1420px;margin:auto"><h1 style="font:18px Arial;color:#8b2900">SYNTHETIC UI PREVIEW — not calculation results</h1>'+content+'</main></body></html>',encoding='utf-8')
print('Synthetic overlay preview written; no campaign data changed.')
