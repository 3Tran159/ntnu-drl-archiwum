from pathlib import Path
p=Path(r"F:\ntnu\phase2_012_20261029\build_dashboard.py")
s=p.read_text(encoding="utf-8")
s=s.replace('stages=[];sections=[]','stages=[];sections=[]\nobservations=read(P/"observations.json",{})')
s=s.replace('plots=chart(rows,"Fx_half_N"', 'note += "<ul>"+"".join("<li>"+esc(t)+"</li>" for t in observations.get(name,[]))+"</ul>"\n    plots=chart(rows,"Fx_half_N"')
s=s.replace('+chart(rows,"foil_mean_yplus","Średnie y+ po powierzchni","–","#7951bd")','+(chart(rows,"foil_mean_yplus","Średnie y+ po powierzchni","–","#7951bd") if u else chart(rows,"max_velocity_m_s","Maksymalna prędkość pasożytnicza","m/s","#7951bd"))')
p.write_text(s,encoding="utf-8")
print("Hydrostatic findings added to phase-2 HTML")
