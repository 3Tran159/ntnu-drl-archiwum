"""Build a local evidence-only campaign report; never launches calculations."""
import argparse,datetime,html,json,math
from pathlib import Path
import autonomous_wave_campaign as campaign
R=Path(__file__).resolve().parent
def esc(value):return html.escape(str(value),quote=True)
def num(value,d=4):
 x=campaign.number(value);return 'Pending' if x is None else f'{x:,.{d}f}'
def link(path,label=None):
 if not path:return ''
 p=Path(path)
 if not p.is_absolute():return esc(label or path)
 return '<a href="'+esc(p.as_uri())+'">'+esc(label or str(p))+'</a>'
def rows_from_results(plan,results,root):
 records=results.get('cases',{});blocked=campaign.configuration_failure(root,plan);rows=[]
 for c in plan.get('cases',[]):
  result=records.get(c['id'],{});registry=campaign.read(Path(root)/'campaign_inputs'/(c['domain_id']+'.json'));source=registry.get('inputs',{}).get(c['source_label'],{})
  status=result.get('status','pending')
  if not result:
   if blocked and blocked['case']==c['id']:
    status='rejected_existing_guard_failure';folder=Path(blocked['directory']);external=campaign.read(folder/'controller_result.json')
    saved=next((p for p in (folder/'final.sim',folder/'guard_or_error_preserved.sim') if p.is_file()),None)
    result={'id':c['id'],'status':status,'directory':str(folder),'time_s':blocked.get('physical_time_s'),'elapsed_wall_s':external.get('elapsed_s'),'final_sim':str(saved) if saved else None,'error':blocked['reason'],'history_paths':[str(folder/'history.csv')] if (folder/'history.csv').is_file() else [],'means':{},'accuracy_admitted':False}
   elif blocked:status='blocked_configuration_review'
   elif not source:status='input_preparation_pending'
   elif c.get('height_m') and not (campaign.number(source.get('wave_period_s')) or 0)>0:status='encounter_period_audit_pending'
  rows.append({'case':c,'result':result,'registry':registry,'source':source,'status':status})
 return rows,blocked
def render(plan,results,state,root=R):
 rows,blocked=rows_from_results(plan,results,root)
 s='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NTNU wave campaign · calculation record</title><style>'
 s+='body{font:15px/1.5 Arial,sans-serif;color:#172f3d;background:#fff;margin:0}main{max-width:1500px;margin:auto;padding:28px}h1{font-size:28px;margin:0 0 8px}h2{font-size:20px;margin:26px 0 12px}h3{font-size:17px}p{margin:8px 0}a{color:#00619b;overflow-wrap:anywhere}.note{border-left:4px solid #627c8b;background:#f3f6f8;padding:14px 18px}.blocked{border-left-color:#b64326;background:#fff3ed}.meta{font-size:12px;color:#536a78}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;min-width:1000px}th,td{border-bottom:1px solid #dce4e9;padding:9px 10px;text-align:left;vertical-align:top}th{background:#edf3f6}td.n{white-space:nowrap;font-variant-numeric:tabular-nums}.case{border-top:1px solid #cbd7df;padding:14px 0;break-inside:avoid}.path{font-size:12px;overflow-wrap:anywhere}.steps{display:flex;flex-wrap:wrap;gap:8px}.steps span{padding:7px 11px;border:1px solid #bdcbd4}details{margin:12px 0}summary{cursor:pointer;font-weight:bold}@media(max-width:700px){main{padding:16px}h1{font-size:23px}}@media print{main{padding:0}body{font-size:9pt}h1{font-size:18pt}.table-scroll{overflow:visible}table{font-size:7.5pt;min-width:0}th,td{padding:4pt}thead{display:table-header-group}tr,.note{break-inside:avoid}a{color:inherit;text-decoration:none}details{display:block}h2,h3{break-after:avoid}}</style><main>'
 s+='<h1>Quasi-2D wave campaign</h1><p>Calculation record · NACA foil · 24 m water depth</p><p class="meta">Updated '+esc(datetime.datetime.now().astimezone().isoformat(timespec='seconds'))+' · '+esc(plan.get('campaign_id','Plan unavailable'))+'</p>'
 if blocked:
  s+='<div class="note blocked"><b>Campaign unarmed · physical guard failure</b><p>'+esc(blocked['case'])+' ended at '+num(blocked.get('physical_time_s'),3)+' s ('+esc(blocked.get('completion_status'))+'). '+esc(blocked['reason'])+'</p><p>'+link(blocked['review'],'Saved failure review')+' · '+link(Path(blocked['directory'])/'completed.json','Completion record')+'</p></div>'
 else:s+='<div class="note"><b>'+esc(state.get('status','Not started').replace('_',' '))+'</b><p>'+esc(state.get('reason','Sequential execution; the first unresolved original case blocks later cases.'))+'</p></div>'
 s+='<p><b>Exploratory results.</b> Repeated force cycles do not establish grid or time-step accuracy, conservation, wave quality or reflection independence. The 0.01% mass-budget flag remains reported under the authorised exploratory exception.</p>'
 settings=plan.get('settings',{})
 s+='<div class="steps"><span>1 · Confirm configuration</span><span>2 · Matched calm and original waves</span><span>3 · Domain / free-surface checks</span><span>4 · Requested wave variations</span></div>'
 s+='<p class="meta">Configured: second-order time, '+num(settings.get('dt_s',0)*1000,1)+' ms, '+esc(settings.get('inner','—'))+' inner iterations; one GPU and one solver worker. Waves: first passing four-cycle screen; 10 periods indicative, 20-period review cap. Calm: both adjacent 0.2 s mean changes below 0.5%. Wall limit: 36 h per case.</p>'
 if state.get('progress'):
  p=state['progress'];s+='<div class="note"><b>Current: '+esc(state.get('case',''))+'</b><p>t = '+num(p.get('time_s'),3)+' s · CD '+num(p.get('CD'),6)+' · CL '+num(p.get('CL_total'),6)+' · elapsed '+num((state.get('elapsed_s') or 0)/3600,2)+' h</p></div>'
 s+='<h2>All configurations</h2><p class="meta">Scroll the table horizontally on a narrow screen. Pending rows contain no calculated force results.</p><div class="table-scroll"><table><thead><tr><th>Case / stage</th><th>Domain</th><th>H [m]</th><th>Cells</th><th>Status</th><th>Final t [s]</th><th>Wall [h]</th><th>Mean CD</th><th>Mean CL</th><th>Compared cycles / window</th><th>Files</th></tr></thead><tbody>'
 for row in rows:
  c,res,reg,source=row['case'],row['result'],row['registry'],row['source'];means=res.get('means',{});window=means.get('window_s')
  periodtext=', '.join(map(str,means.get('cycle_numbers',[]))) or '—'
  if window:periodtext+=' · '+num(window[0],3)+'–'+num(window[1],3)+' s'
  files=link(res.get('final_sim'),'Saved .sim') if res else link(source.get('path'),'Prepared .sim') if source else 'Pending'
  # Assemble cells separately to keep conditional arithmetic explicit.
  cells=['<b>'+esc(c['id'])+'</b><br>'+esc(c.get('stage','')),esc(c['domain_id']),num(c['height_m'],2),f"{reg['cells']:,}" if isinstance(reg.get('cells'),int) else 'Pending',esc(row['status'].replace('_',' ')),num(res.get('time_s'),3),num(res.get('elapsed_wall_s')/3600 if campaign.number(res.get('elapsed_wall_s')) is not None else None,2),num(means.get('CD'),6),num(means.get('CL_total'),6),esc(periodtext),files]
  s+='<tr>'+''.join('<td>'+cell+'</td>' for cell in cells)+'</tr>'
 s+='</tbody></table></div>'
 for row in rows:
  c,res=row['case'],row['result']
  if not res:continue
  s+='<section class="case"><h2>'+esc(c['id'])+' · '+esc(res.get('status','').replace('_',' '))+'</h2>'
  if res.get('error'):s+='<p class="note blocked">'+esc(res['error'])+'</p>'
  screen=res.get('screen',{});diagnostics=res.get('independent_diagnostics',{})
  if diagnostics:s+='<p>Native absolute phase-budget peak: '+num(diagnostics.get('native_abs_peak_pct'),6)+'% of inlet mass flow. '+('Above the retained 0.01% review flag.' if diagnostics.get('mass_review_flag') else 'Within the retained 0.01% review flag.')+'</p>'
  if c['height_m']:
   s+='<p>Complete cycles: '+esc(', '.join(map(str,screen.get('valid_complete_cycles',[]))) or 'None')+'. Fixed absolute phase; incomplete cycles excluded. Means use the last four complete cycles.</p>'
   comparisons=screen.get('comparisons',{})
   if comparisons:
    s+='<div class="table-scroll"><table style="min-width:650px"><tr><th>Coefficient</th><th>Mean Δ [%]</th><th>Amplitude Δ [%]</th><th>Waveform RMS Δ [%]</th><th>Phase Δ [°]</th></tr>'
    for key in ('CD','CL_total'):
     met=comparisons.get(key,{}).get('worst_pair_metrics',{});s+='<tr><td>'+esc(key)+'</td>'+''.join('<td>'+num(met.get(k),4)+'</td>' for k in ('mean_pct','fundamental_amplitude_pct','waveform_rms_pct','phase_deg'))+'</tr>'
    s+='</table></div>'
  else:
   for key,item in screen.get('coefficients',{}).items():s+='<p>'+esc(key)+' adjacent mean change: '+num(item.get('change_pct'),4)+'%.</p>'
  s+='<p class="path">'+link(res.get('final_sim'),'Computed final state')+' · '+link(Path(res.get('directory','.'))/'controller_result.json','Result and provenance')+'</p>'
  for path in res.get('history_paths',[]):s+='<p class="path">'+link(path,'Force history: '+str(path))+'</p>'
  if res.get('checkpoints'):s+='<details><summary>Preserved checkpoints</summary>'+''.join('<p class="path">'+link(x)+'</p>' for x in res['checkpoints'])+'</details>'
  s+='</section>'
 s+='<h2>Checks still required</h2><ul>'+''.join('<li>'+esc(x)+'</li>' for x in plan.get('accuracy_pending',['Wave-specific time-step, grid, propagation and reflection checks']))+'</ul><p>'+link(Path(root)/'campaign_plan.json','Campaign definitions')+' · '+link(Path(root)/'campaign_results.json','Saved results')+' · '+link(Path(root)/'campaign_state.json','Controller state')+'</p></main></html>'
 return s
def build(root=R,output=None):
 root=Path(root);output=Path(output or root.parent/'campaign_results.html')
 content=render(campaign.read(root/'campaign_plan.json'),campaign.read(root/'campaign_results.json'),campaign.read(root/'campaign_state.json'),root)
 tmp=output.with_name(output.name+'.'+str(__import__('os').getpid())+'.tmp');tmp.write_text(content,encoding='utf8');tmp.replace(output);return output
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();print(build(output=args.output))
if __name__=='__main__':main()