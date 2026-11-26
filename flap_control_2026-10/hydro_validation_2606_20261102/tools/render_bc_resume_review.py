from pathlib import Path
import sys,json,html
H=Path(__file__).resolve().parents[1];sys.path.insert(0,str(H/'tools/deps'))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd,numpy as np
runs={'B0 without Overset':H/'cases/SP_B_split0_fixed/b0_top_direction_20261103_053542','C0 with Overset':H/'cases/SP_C_split0_overset/c0_top_direction_20261103_050724'}
fig,axs=plt.subplots(2,2,figsize=(12,8))
for (label,p),color in zip(runs.items(),['#277da8','#d65b31']):
 w=pd.concat([pd.read_csv(p/(g+'_final_wall.csv')) for g in ['main','flap']])
 x=w['X (m)']/1.19;cp=w['Pressure (Pa)']/162000
 axs[0,0].scatter(x,cp,s=4,label=label,color=color,alpha=.65)
 mask=(x>.72)&(x<.9);axs[0,1].scatter(x[mask],cp[mask],s=6,label=label,color=color,alpha=.65)
 axs[1,0].scatter(x,w['Wall Y+'],s=4,label=label,color=color,alpha=.65)
 h=pd.read_csv(p/'history.csv');axs[1,1].plot(h['time_s']-h['time_s'].iloc[-1],100*(h['CD']/h['CD'].iloc[-25:].mean()-1),label=label,color=color)
for ax in axs.flat:ax.grid(alpha=.2)
axs[0,0].set(xlabel='x/c',ylabel='Cp (piezometric pressure / q)',title='Native wall pressure — matched boundary conditions');axs[0,0].invert_yaxis();axs[0,0].legend()
axs[0,1].set(xlabel='x/c',ylabel='Cp',title='Hinge / interface neighbourhood');axs[0,1].invert_yaxis()
axs[1,0].set(xlabel='x/c',ylabel='Wall y+',yscale='log',title='Local resolution remains a quantitative uncertainty')
axs[1,1].set(xlabel='Time relative to final checkpoint (s)',ylabel='CD / final25 mean -1 (%)',title='Force settling (different saved physical times)');axs[1,1].set_ylim(-.3,.3);axs[1,1].legend()
fig.suptitle('B0/C0 baseline accepted for kinematic POC only — no grid/time convergence claim',fontsize=12)
fig.tight_layout();fig.savefig(H/'reports/BC_resume_audit_20261103.png',dpi=150);plt.close(fig)
a=json.loads((H/'audit/C0_KINEMATIC_BASE_ACCEPTANCE_20261103.json').read_text())
r=json.loads((H/'audit/bc_resume_review_20261103/review.json').read_text())
rows=''
for k,v in r['cases'].items():
 f=v['force_windows'];rows+=f'<tr><td>{k}</td><td>{f["CL_hydro"]["mean25"]:.9f}</td><td>{f["CD"]["mean25"]:.9f}</td><td>{f["Mh_Nm"]["mean25"]:.6f}</td><td>{max(x["p95_last_over_first"] for n,x in v["residuals"].items() if n!="Y-momentum"):.3g}</td></tr>'
body='<html><meta charset="utf-8"><title>BC native audit</title><style>body{font:17px system-ui;max-width:1050px;margin:35px auto;padding:20px}td,th{padding:10px;border-bottom:1px solid #aaa}img{width:100%}</style><h1>B0/C0 — native numerical audit</h1><p>C0 accepted as the base for frozen-flow kinematic POC. Quantitative force and energy validation remains open.</p><p>Both checkpoint field arrays were re-exported in STAR2606 and matched against the saved exports. Times and iterations preserved; no solver steps or reset. Physical B/C boundary conditions, material properties,URF,dt,inner iteration count and spatial/time schemes match.</p><table><tr><th>Case</th><th>CL mean25</th><th>CD mean25</th><th>Mh Nm</th><th>Worst p95 residual final/first</th></tr>'+rows+'</table><p>C0/B0 difference:CL-0.304%,CD+0.762%. C0 all333939 mesh cells audited,zero Overset errors/difficult interpolation,min volume9.12875e-12m3. Cavitation margin about27.75kPa,above required10kPa.</p><img src="BC_resume_audit_20261103.png"><h2>Limits retained</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in a['uncertainty'])+'</ul><h2>Next test</h2><p>'+html.escape(a['next_experiment'])+'</p></html>'
(H/'reports/BC_RESUME_NUMERICAL_AUDIT_20261103.html').write_text(body,encoding='utf8')
print(str(H/'reports/BC_resume_audit_20261103.png'))
