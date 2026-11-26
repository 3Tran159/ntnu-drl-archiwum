from pathlib import Path
import shutil,datetime
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');p=R/'wave_cycle_repeatability.py'
s=p.read_text()
changes=[
('Time is the absolute simulation wave clock (origin 0), including across restarts.','History time remains absolute. An explicit analysis origin can exclude calm/ramp/arrival stages.'),
('def _cycle(number,period,times,series,nominal_dt,invalid_times):\n lo=(number-1)*period;hi=number*period','def _cycle(number,period,times,series,nominal_dt,invalid_times,origin_s=0.0):\n lo=origin_s+(number-1)*period;hi=origin_s+number*period'),
('def evaluate(history_paths,period,min_cycles=10,max_cycles=20):','def evaluate(history_paths,period,min_cycles=10,max_cycles=20,analysis_origin_s=0.0):'),
(' period=float(period)\n',' period=float(period)\n analysis_origin_s=float(analysis_origin_s)\n if not math.isfinite(analysis_origin_s) or analysis_origin_s<0:raise ValueError("analysis_origin_s must be finite and nonnegative")\n'),
('math.floor((last+1e-10)/period)','math.floor((last-analysis_origin_s+1e-10)/period)'),
('last+1e-10>=min_cycles*period','last+1e-10>=analysis_origin_s+min_cycles*period'),
('last+1e-10>=max_cycles*period','last+1e-10>=analysis_origin_s+max_cycles*period'),
('_cycle(n,period,times,series,interval,[x["time_s"] for x in invalid])','_cycle(n,period,times,series,interval,[x["time_s"] for x in invalid],analysis_origin_s)'),
('"wave_clock_origin_s":0.0','"wave_clock_origin_s":analysis_origin_s'),
('"earliest_review_time_s":min_cycles*period,"review_cap_time_s":max_cycles*period','"earliest_review_time_s":analysis_origin_s+min_cycles*period,"review_cap_time_s":analysis_origin_s+max_cycles*period'),
('"elapsed_wave_periods":last/period if last is not None else None','"elapsed_wave_periods":max(0.0,(last-analysis_origin_s)/period) if last is not None else None')]
for a,b in changes:
 if s.count(a)!=1:raise RuntimeError('Unexpected origin anchor '+a)
 s=s.replace(a,b)
compile(s,str(p),'exec');shutil.copy2(p,R/('wave_cycle_repeatability_before_origin_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.py'))
tmp=p.with_suffix('.origin_stage');tmp.write_text(s,encoding='utf8');tmp.replace(p)
print('Added explicit analysis origin; default legacy behavior unchanged')
