"""Shared read-only wave-case legend. panel() -> standalone scoped HTML; no solver actions."""
import argparse,datetime,html,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def _read(path):
 try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
def _num(value):
 try:
  x=float(value);return x if math.isfinite(x) else None
 except (ValueError,TypeError):return None
def _esc(value):return html.escape(str(value),quote=True)
def _fmt(value,d=2):return '—' if value is None else f'{value:.{d}f}'
def _link(path,label):
 try:return '<a href="'+_esc(Path(path).as_uri())+'">'+_esc(label)+'</a>'
 except ValueError:return _esc(label)
def _active(case,state):
 if state.get('computation_stage')=='calm_settling':return case.get('id')=='C01'
 return bool(case.get('active_prefix')) and str(state.get('case','')).startswith(case['active_prefix'])
def _period(case,state,root):
 if case['height_m']==0:return None,None
 if case.get('period_source'):
  record=_read(case['period_source']);v=_num(record.get(case.get('period_key','wave_period_s')))
  if v and v>0:return v,case['period_source']
 if _active(case,state):
  stage=str(state.get('computation_stage','')).lower()
  if 'calm' in stage or (not stage and 'calm' in str(state.get('case','')).lower()):return None,None
  folder=Path(state.get('directory',''))
  activation=state.get('activation',{})
  if activation.get('case')==state.get('case') and activation.get('target_height_m')==case['height_m']:
   value=_num(activation.get('wave_period_s'))
   if value and value>0:return value,str(folder/'wave_activation.json')
  if folder.is_absolute():
   requested=folder/'requested_wave_audit.json';a=_read(requested)
   if a.get('height_m')==case['height_m'] and a.get('wavelength_m')==case['wavelength_m']:
    v=_num(a.get('period_s'))
    if v and v>0:return v,str(requested)
   setup=folder/'setup.json';v=_num(_read(setup).get('wave_period_s'))
   if v and v>0:return v,str(setup)
  return None,None
 if case.get('active_prefix'):return None,None
 registry=_read(Path(root)/'campaign_inputs'/(case['domain_id']+'.json'))
 label={.25:'H025',.5:'H050',.75:'H075'}.get(case['height_m']);item=registry.get('inputs',{}).get(label,{})
 if registry.get('domain',{}).get('id')!=case['domain_id'] or item.get('height_m')!=case['height_m']:return None,None
 audit_path=item.get('audit');a=_read(audit_path) if audit_path else {};v=_num(a.get('wave_period_s'))
 if a.get('wave') is True and 'FifthOrderVofWave' in str(a.get('wave_class','')) and v and v>0:return v,audit_path
 return None,None
def _status(case,state,results,root):
 if state.get('computation_stage')=='calm_settling' and case.get('id') in ('C01','W01a'):
  folder=Path(state.get('directory',''));record=_read(folder/'settled_checkpoint.json')
  ready=record.get('status')=='calm_force_settled' and record.get('source_unchanged') is True and record.get('settling',{}).get('passed') is True and bool(record.get('file')) and Path(record['file']).is_file()
  if case['id']=='W01a':return ('Settled C01 saved · wave setup pending' if ready else 'Waiting for C01 force settling and completed save'),'pending'
  progress=_read(folder/'progress.json') or state.get('progress',{});t=_num(progress.get('time_s'));check=_read(folder/'calm_settling.json')
  if any(w in str(state.get('status','')).lower() for w in ('fail','error','guard','needs_review')):return 'Calm trial stopped · review required','failed'
  if ready:return 'Calm settled · C01_settled.sim saved at '+_fmt(_num(record.get('physical_time_s')),3)+' s','recorded'
  text='Force gate passed · saving C01' if check.get('passed') is True else 'Calm settling' if t is not None else 'Loading computed calm source'
  return text+(' · t = '+_fmt(t,3)+' s' if t is not None else '')+' · inlet H = 0 m','active' if state.get('computation_active') else 'pending'
 if case.get('failure_review'):
  review=_read(Path(root)/case['failure_review'])
  if review.get('status')=='physical_speed_guard_failed':
   return 'Stopped · physical guard at '+_fmt(_num(review.get('time_s')),3)+' s','failed'
 if _active(case,state):
  status=str(state.get('status',''));stage=str(state.get('computation_stage',''))
  if any(word in status.lower() for word in ('fail','error','guard','needs_review')):return 'Stopped · review required','failed'
  p=state.get('progress',{});t=_num(p.get('time_s'))
  activation=state.get('activation',{})
  if state.get('case')=='W01a_W20L4_M10_inlet_fullheight_restart_r3' and activation.get('case')==state.get('case') and activation.get('height_mode')=='constant_full_height_from_activation':
   text='Full H = 0.50 m inlet wave · no ramp' if state.get('computation_active') else 'Saved full-height inlet trial'
   return text+(' · t = '+_fmt(t,3)+' s' if t is not None else '')+' · arrival unverified','active' if state.get('computation_active') else 'pending'
  immediate=_read(Path(root)/'w01a_immediate_wave_authorization.json')
  if immediate.get('no_force_settling_requirement') is True and ('calm' in stage.lower() or (not stage and 'calm' in str(state.get('case','')).lower())):
   text='Saving startup state for inlet-wave activation' if state.get('stop_requested') else 'Calm starting fields · inlet activation next'
   return text+(' · t = '+_fmt(t,3)+' s' if t is not None else ''),'active'
  if 'calm' in stage.lower() or (not stage and 'calm' in str(state.get('case','')).lower()):
   text=('Calm settling' if t is not None and t>0 else 'Calm initialization / loading') if state.get('computation_active') else 'Calm stage saved'
   if 'settled' in status.lower():text='Calm settled'
   return text+(' · t = '+_fmt(t,3)+' s' if t is not None and t>0 else '')+' · no wave yet','active'
  if state.get('computation_active'):
   return (stage.replace('_',' ') or 'Wave calculation running')+(' · t = '+_fmt(t,3)+' s' if t is not None else ''),'active'
  return status.replace('_',' ') or case['status_default'],'pending'
 result=results.get('cases',{}).get(case.get('campaign_case_id'),{})
 if result:
  status=result.get('status','')
  if status=='repeatability_screen_pass':return 'Cycle screen passed · accuracy checks pending','recorded'
  if status=='calm_settled':return 'Calm settled','recorded'
  return status.replace('_',' '),'pending'
 if case.get('domain_id') and not case.get('active_prefix'):
  registry=_read(Path(root)/'campaign_inputs'/(case['domain_id']+'.json'))
  label={.25:'H025',.5:'H050',.75:'H075'}.get(case['height_m'])
  if registry.get('status')=='paired_inputs_audited_zero_steps' and registry.get('inputs',{}).get(label):return 'Input prepared · flow pending','pending'
 return case['status_default'],'pending'
STYLE="""<style>
.wcc-panel{font-family:Arial,"Segoe UI",sans-serif;color:#17384c;border:1px solid #cbd8df;margin:22px 0;background:white;min-width:0}.wcc-panel>summary{padding:16px 18px;font-size:20px;font-weight:600;cursor:pointer}.wcc-body{padding:0 18px 16px;min-width:0}.wcc-panel p{font-size:14px;line-height:1.5;margin:10px 0}.wcc-panel .wcc-shared{font-size:13px;background:#f2f6f8;padding:10px 12px}.wcc-panel .wcc-scroll{overflow-x:auto;max-width:100%}.wcc-panel table{border-collapse:collapse;width:100%;min-width:1050px;font-size:13px;line-height:1.45}.wcc-panel th,.wcc-panel td{padding:9px 10px;border-bottom:1px solid #dae3e9;text-align:left;vertical-align:top;letter-spacing:0;text-transform:none}.wcc-panel thead th{background:#f2f6f8;font-size:12px}.wcc-panel th[scope=row]{position:sticky;left:0;background:white;z-index:1;white-space:nowrap}.wcc-panel td.wcc-number{white-space:nowrap;font-variant-numeric:tabular-nums}.wcc-panel .wcc-scroll table{table-layout:fixed;min-width:1050px}.wcc-panel .wcc-scroll table th,.wcc-panel .wcc-scroll table td{box-sizing:border-box;min-width:0;max-width:none;white-space:normal;word-break:normal;overflow-wrap:break-word}.wcc-panel .wcc-scroll table td.wcc-number{white-space:nowrap}.wcc-panel .wcc-scroll table td.wcc-definition,.wcc-panel .wcc-scroll table td.wcc-record{white-space:normal;overflow-wrap:anywhere;word-break:normal}.wcc-panel .wcc-scroll col.wcc-case-col{width:13%}.wcc-panel .wcc-scroll col.wcc-height-col,.wcc-panel .wcc-scroll col.wcc-lambda-col{width:7%}.wcc-panel .wcc-scroll col.wcc-domain-col{width:11%}.wcc-panel .wcc-scroll col.wcc-period-col{width:12%}.wcc-panel .wcc-scroll col.wcc-definition-col,.wcc-panel .wcc-scroll col.wcc-record-col{width:25%}.wcc-panel .wcc-active{border-left:3px solid #0072b2}.wcc-panel .wcc-failed{border-left:3px solid #b64620}.wcc-panel small{display:block;color:#526b7b;font-size:11px}.wcc-panel a{color:#00619b;text-decoration:underline}.wcc-panel .wcc-note{font-size:12px;color:#526b7b}.wcc-panel .wcc-technical{margin-top:12px;font-size:12px}.wcc-panel .wcc-technical summary{cursor:pointer}.wcc-panel .wcc-path{overflow-wrap:anywhere}.wcc-panel .wcc-mobile{display:none}
@media screen and (max-width:700px){.wcc-panel>summary{font-size:18px;padding:13px}.wcc-body{padding:0 13px 14px}.wcc-panel p{font-size:13px}.wcc-panel .wcc-scroll{overflow:visible}.wcc-panel .wcc-scroll table{display:block;min-width:0;width:100%}.wcc-panel .wcc-scroll table colgroup,.wcc-panel .wcc-scroll table thead{display:none}.wcc-panel .wcc-scroll table tbody{display:block}.wcc-panel .wcc-scroll table tr{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 10px;border:1px solid #dae3e9;margin:12px 0;padding:10px;background:white}.wcc-panel .wcc-scroll table tr.wcc-active{border-left:3px solid #0072b2}.wcc-panel .wcc-scroll table tr.wcc-failed{border-left:3px solid #b64620}.wcc-panel .wcc-scroll table th[scope=row]{grid-column:1/-1;position:static;padding:0 0 7px;font-size:15px;border-bottom:1px solid #dae3e9;background:white}.wcc-panel .wcc-scroll table td{display:block;min-width:0;padding:4px 0;border:0}.wcc-panel .wcc-scroll table td::before{content:attr(data-label);display:block;color:#526b7b;font-size:11px;font-weight:600;margin-bottom:3px;white-space:normal}.wcc-panel .wcc-scroll table td.wcc-definition,.wcc-panel .wcc-scroll table td.wcc-record{grid-column:1/-1}.wcc-panel .wcc-scroll table td.wcc-record{border-top:1px solid #e7edf1;padding-top:8px}}
@media print{.wcc-panel{break-before:page;border:0;margin:0}.wcc-panel>summary{font-size:15pt;padding:0 0 8pt;list-style:none}.wcc-body{padding:0}.wcc-panel .wcc-scroll table{min-width:0;width:100%;font-size:8pt;line-height:1.3}.wcc-panel th,.wcc-panel td{padding:2pt 4pt}.wcc-panel thead th{font-size:8pt}.wcc-panel th[scope=row]{position:static;white-space:normal}.wcc-panel tr{break-inside:avoid}.wcc-panel .wcc-scroll{overflow:visible}.wcc-panel p{font-size:9pt;line-height:1.35;margin:3pt 0}.wcc-panel .wcc-mobile,.wcc-panel .wcc-technical{display:none}}
</style>"""
def render(catalog,state,results,root=ROOT):
 if not catalog or catalog.get('version')!=1:return ''
 shared=catalog['shared'];period_sources=[]
 s=STYLE+'<details class="wcc-panel" open><summary>Wave cases and parameters</summary><div class="wcc-body">'
 s+='<p><b>H</b> is crest-to-trough height; <b>λ</b> is wavelength. <b>T</b> is the evaluated STAR analytic encounter period for that case, not a measurement of the transported wave. A pending period is not copied from W01.</p>'
 s+='<p class="wcc-shared">Shared geometry and speed: water depth '+_fmt(shared['water_depth_m'],0)+' m · air '+_fmt(shared['air_height_m'],0)+' m · z = '+_fmt(shared['z_bounds_m'][0],0)+' to '+_fmt(shared['z_bounds_m'][1],0)+' m · calm waterline z = '+_fmt(shared['waterline_z_m'],0)+' m · U = '+_fmt(shared['speed_m_s'],0)+' m/s · foil submergence '+_fmt(shared['foil_submergence_m'],0)+' m · span '+_fmt(shared['span_m']*1000,0)+' mm.</p>'
 s+='<p><b>Current sequence: settle C01, save its computed state, then activate W01a.</b> Both adjacent 0.2 s mean CD and CL changes must be below 0.5%. W01a uses a copy of the settled C01 with full H = 0.50 m at the inlet from activation, with no height ramp or global wave reinitialization. H, wavelength and domain remain the same as W01.</p>'
 s+='<div class="wcc-scroll" tabindex="0" role="region" aria-label="Wave cases and parameters"><table><colgroup><col class="wcc-case-col"><col class="wcc-height-col"><col class="wcc-lambda-col"><col class="wcc-domain-col"><col class="wcc-period-col"><col class="wcc-definition-col"><col class="wcc-record-col"></colgroup><thead><tr><th>Case</th><th>H [m]</th><th>λ [m]</th><th>Domain Lx [m]</th><th>STAR T [s]</th><th>Definition / startup</th><th>Current record</th></tr></thead><tbody>'
 for case in catalog['cases']:
  t,source=_period(case,state,root);status,kind=_status(case,state,results,root)
  period='—' if case['height_m']==0 else _fmt(t,6) if t else 'Pending'
  if source:period_sources.append((case['id'],source))
  length=_fmt(case['domain_length_m'],0) if case['domain_length_m'] is not None else 'Matched'
  ratio=case['domain_length_m']/case['wavelength_m'] if case['wavelength_m'] else None
  if ratio is not None:length+='<small>'+_fmt(ratio,0)+' λ</small>'
  definition=_esc(case['startup'])
  if case['id'] not in ('C01','W01','W01a'):definition=_esc(case['purpose'])
  s+='<tr class="wcc-'+kind+'"><th scope="row">'+_esc(case['id'])+'</th><td class="wcc-number" data-label="H [m]">'+_fmt(case['height_m'],2)+'</td><td class="wcc-number" data-label="λ [m]">'+_fmt(case['wavelength_m'],0)+'</td><td class="wcc-number" data-label="Domain Lx [m]">'+length+'</td><td class="wcc-number" data-label="STAR T [s]"'+(' title="'+_esc(str(source))+'"' if source else '')+'>'+period+'</td><td class="wcc-definition" data-label="Definition / startup">'+definition+'</td><td class="wcc-record" data-label="Current record">'+_esc(status)+'</td></tr>'
 s+='</tbody></table></div><p class="wcc-note">C01 denotes the matched calm reference for each domain and mesh; one calm result is not reused across different domains. “Input prepared” means zero-step preparation only. Case definitions do not authorise or validate calculations.</p>'
 s+='<p><b>Fifth-order</b> describes the wave theory. <b>Second-order implicit</b> describes time integration; these are separate settings.</p>'
 s+='<details class="wcc-technical"><summary>How to read the names and recorded periods</summary><p>W = wave configuration · a = changed startup version · M = mesh identifier · r = technical attempt. A new r number alone does not define a new wave.</p>'
 for label,path in period_sources:s+='<p class="wcc-path">'+_esc(label)+' period: '+_link(path,'Actual STAR record')+'</p>'
 s+='<p>'+_link(Path(root)/'wave_case_catalog.json','Central case definitions')+'</p></details></div></details>'
 return s
def panel():
 return render(_read(ROOT/'wave_case_catalog.json'),_read(ROOT/'wave_foil_run_state.json'),_read(ROOT/'campaign_results.json'))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--preview',type=Path,required=True);args=parser.parse_args()
 args.preview.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wave case legend preview</title><body style="margin:0;padding:20px;background:#edf2f5"><main style="max-width:1500px;margin:auto">'+panel()+'</main></body></html>',encoding='utf8')
 print(args.preview)