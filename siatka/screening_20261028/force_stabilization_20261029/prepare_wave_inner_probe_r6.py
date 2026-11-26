from pathlib import Path
R=Path(__file__).resolve().parent
a=R/'WaveInner20ProbeR6.java';b=R/'run_wave_inner20_probe_r6.py'
if a.exists() or b.exists():raise RuntimeError('Preserve existing R6')
s=(R/'WaveInner20ProbeR5.java').read_text().replace('class WaveInner20ProbeR5','class WaveInner20ProbeR6')
old='av.write(t+","+w+","+analyticWater.getReportMonitorValue()+"\\n");av.flush();'
new='double analyticInventory=analyticWater.getReportMonitorValue();if(Double.isFinite(analyticInventory)){av.write(t+","+w+","+analyticInventory+"\\n");av.flush();}else if(step==0){Files.writeString(out.resolve("reference_cache_at_load.json"),json(Map.of("time_s",t,"state","Analytic wave inventory unavailable immediately after checkpoint load; independent physical fields checked before first step","reinitialized",false)));}else throw new IllegalStateException("Analytic wave cache still unavailable after first step");'
assert s.count(old)==1;s=s.replace(old,new)
old='if(step%10==0){for(int k=0;k<xs.length;k++){double a=actual.get(k).getReportMonitorValue()/.02-24,b=analytic.get(k).getReportMonitorValue()/.02-24;'
new='if(step==1||step%10==0){for(int k=0;k<xs.length;k++){double a=actual.get(k).getReportMonitorValue()/.02-24,b=analytic.get(k).getReportMonitorValue()/.02-24;if(step==0&&!Double.isFinite(b)&&Double.isFinite(a)&&Math.abs(a)<=1.5){Files.writeString(out.resolve("reference_gauges_at_load.json"),json(Map.of("time_s",t,"state","Analytic plane cache unavailable at load; require finite reference after first guarded step","reinitialized",false)));continue;}'
assert s.count(old)==1;s=s.replace(old,new)
# Keep all independent physical speed/phase/time/mass guards, no solution reset.
a.write_text(s)
s=(R/'run_wave_inner20_probe_r5.py').read_text().replace('W20_H24_X4_GPUprop_environmentalOutlet_inner20probe_r5','W20_H24_X4_GPUprop_environmentalOutlet_inner20probe_r6').replace('wave_inner20_probe_r5.lock','wave_inner20_probe_r6.lock').replace('WaveInner20ProbeR5','WaveInner20ProbeR6').replace('GPU inner20 diagnostic r5','GPU inner20 diagnostic r6')
b.write_text(s)
s=(R/'analyze_wave_inner20_probe_r5.py').read_text().replace('inner20probe_r5','inner20probe_r6').replace('wave_inner20_probe_r5_review.json','wave_inner20_probe_r6_review.json')
s=s.replace("for x in gb]","for x in gb if (round(x['time_s'],6),x['x_m']) in gmap]")
(R/'analyze_wave_inner20_probe_r6.py').write_text(s)
print('R6 preserves source fields; t0analyticcache separately recorded, finite references mandatory after first guardedstep.')
