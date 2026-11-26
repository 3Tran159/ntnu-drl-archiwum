"""Exact linear finite-depth reference for the designed STAR wave tank cases."""
import csv,json,math
from pathlib import Path
root=Path(r'F:\ntnu\wave_depth_20261029')
cases=json.loads((root/'cases.json').read_text(encoding='utf-8'))
samples=[];summary=[];g=9.81;U=18.0;z=-2.0
for v in cases:
 L=v['lambda_m'];h=v['depth_m'];dt=v['dt_s'];a=.5*v['height_m']
 k=2*math.pi/L;sigma=math.sqrt(g*k*math.tanh(k*h));w=sigma+U*k;enc=2*math.pi/w
 cu=a*sigma*math.cosh(k*(h+z))/math.sinh(k*h)
 cw=a*sigma*math.sinh(k*(h+z))/math.sinh(k*h)
 summary.append(dict(case=v['id'],lambda_m=L,h_m=h,amplitude_m=a,k_m_inverse=k,kh=k*h,
 phase_speed_relative_water_mps=sigma/k,lab_speed_mps=U+sigma/k,
 T_intrinsic_s=2*math.pi/sigma,T_enc_s=enc,dt_s=dt,
 steps_per_Tenc=enc/dt,peak_u_orbit_2m_mps=cu,peak_w_orbit_2m_mps=cw,
 expected_x_CFL=U*dt/.2048,expected_vertical_orbital_CFL=cw*dt/.0256))
 for i in range(601):
  t=2*enc*i/600;phase=-w*t
  samples.append(dict(case=v['id'],t_s=t,eta_x0_m=a*math.cos(phase),
    u_wave_x0_zminus2_mps=cu*math.cos(phase),
    w_wave_x0_zminus2_mps=cw*math.sin(phase),phase_rad=phase))
for path,rows in [(root/'analytic_summary.csv',summary),(root/'theoretical_wave_probes.csv',samples)]:
 with path.open('w',newline='',encoding='utf-8') as fh:
  writer=csv.DictWriter(fh,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
print('REFS',len(summary),'wave cases and',len(samples),'sample rows')
