import json,csv,math,datetime,base64
from pathlib import Path
from html import escape
Q=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
def read(p,d=None):
 try:return json.loads(p.read_text(encoding="utf-8-sig"))
 except (OSError,ValueError):return d
def num(v):
 if v is None:return "—"
 if isinstance(v,bool):return "Tak" if v else "Nie"
 if isinstance(v,int):return str(v)
 return f"{v:.5g}" if isinstance(v,float) else escape(str(v))
def rows(p):
 try:
  with p.open() as f:return [{k:float(v) if v else None for k,v in r.items()} for r in csv.DictReader(f) if None not in r]
 except (OSError,ValueError):return []
def event(p,title,detail):
 return {"time":datetime.datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(timespec="seconds"),"work":title,"finding":detail}
def panel():
 state=read(Q/"status.json",{"activity":"Budowa quasi-2D","live":True});events=read(Q/"work_log.json",[])
 meshes=[];runs=[];force_rows=[];images=[]
 for d in sorted(Q.glob("M*")):
  if not d.is_dir():continue
  m=read(d/"measurement.json",{});top=read(d/"topology_audit.json",{})
  if m:
   a=m.get("metrics",m);a.update(read(d/"mesh_timing.json",{}))
   values=[d.name,a.get("cell_count"),a.get("mesh_time_s"),a.get("min_cell_quality"),a.get("min_volume_change"),a.get("max_skewness_angle_deg"),100*top["area_fraction_at_least_15_quad_layers"] if top else None,top.get("single_layer_topology")]
   meshes.append("<tr>"+"".join("<td>"+num(x)+"</td>" for x in values)+"</tr>")
   events.append(event(d/"mesh_timing.json" if (d/"mesh_timing.json").exists() else d/"mesh.sim","Siatka "+d.name,f'{a.get("cell_count")} komórek. Audyt jakości i topologii zapisany.'))
  for r in sorted(d.glob("*/history.csv"),key=lambda p:(not p.parent.name.startswith("H0"),p.parent.name)):
   data=rows(r);setup=read(r.parent/"setup.json",{});done=read(r.parent/"completed.json",{})
   if not data:continue
   last=data[-1];n=len(data);t=last.get("physical_time_s",0);wall=last.get("wall_seconds",0);speed=setup.get("speed_m_s")
   status="Ukończono próbę" if done and done.get("guard_passed") else done.get("status","W trakcie")
   vals=[d.name+"/"+r.parent.name,speed,setup.get("dt_s"),n,t,wall,wall/n,wall/t*1.19/18/60 if t and speed else None,last.get("max_convective_CFL"),status]
   runs.append("<tr>"+"".join("<td>"+num(x)+"</td>" for x in vals)+"</tr>")
   vals=[d.name+"/"+r.parent.name,last.get("Fx_slice_N"),last.get("Fz_slice_N"),last.get("CD"),last.get("CL_total"),last.get("CL_buoyancy_subtracted"),last.get("foil_mean_yplus"),last.get("foil_min_yplus"),last.get("foil_max_yplus")]
   force_rows.append("<tr>"+"".join("<td>"+num(x)+"</td>" for x in vals)+"</tr>")
   if done:events.append(event(r.parent/"completed.json",d.name+" / "+r.parent.name,f'{n} kroków, t={t:.6g} s, {wall:.1f} s pracy solvera. To próba rozruchowa.'))
  img=Q/"plots"/(d.name+"_mesh.png")
  if img.exists():images.append('<details><summary>Rzeczywista siatka '+escape(d.name)+' — profil, LE i TE</summary><img style="width:100%" alt="Siatka '+escape(d.name)+'" src="data:image/png;base64,'+base64.b64encode(img.read_bytes()).decode()+'"></details>')
 conclusions=read(Q/"conclusions.json",[])
 log="".join("<tr><td>"+escape(e.get("time",""))+"</td><td><b>"+escape(e.get("work",""))+"</b><br>"+escape(e.get("finding",""))+"</td></tr>" for e in sorted(events,key=lambda x:x["time"],reverse=True))
 h='<section id="quasi2d"><h2>2.4 · Quasi-2D — aktualna kampania</h2><p class="badge">'+escape(state["activity"])+'</p><p>Profil 012, camber 2,5%, cięciwa 1,19 m, zanurzenie 2 m. Jedna warstwa na szerokość 0,02 m, symetria z obu boków; Sref = 0,0238 m². Siły dotyczą tego wycinka. Dla sił na metr rozpiętości dzielimy N przez 0,02 m. Współczynniki używają ρ=1000 kg/m³ i qS=½ρU²Sref.</p>'
 if conclusions:h+="<ul>"+"".join("<li>"+escape(x)+"</li>" for x in conclusions)+"</ul>"
 h+='<div style="overflow:auto"><table><tr><th>Siatka</th><th>Komórki</th><th>Siatkowanie [s]</th><th>min quality</th><th>min volume change</th><th>max skew [°]</th><th>15 regularnych warstw [%]*</th><th>Jedna warstwa przez span</th></tr>'+''.join(meshes)+'</table></div><p class="muted">*Konserwatywny audyt połączeń komórek: co najmniej 15 kolejnych czworokątów od ściany. Nieregularne komórki przejściowe kończą zliczanie. Nie jest to pole PrismLayerNumber, którego directed sweep nie zachowuje. M01: 1,95 s generowania źródła i 20,55 s ponownego wyciągania; brak jednego pomiaru całego pierwszego siatkowania.</p>'
 h+='<h3>Wydajność i krok czasowy</h3><div style="overflow:auto"><table><tr><th>Przebieg</th><th>U [m/s]</th><th>dt [s]</th><th>Kroki</th><th>t [s]</th><th>Solver [s]</th><th>s/krok</th><th>min / c/U</th><th>CFL max, koniec</th><th>Status</th></tr>'+''.join(runs)+'</table></div>'
 h+='<h3>Końcowe wartości rozruchowe — nie wyniki ustalone</h3><div style="overflow:auto"><table><tr><th>Przebieg</th><th>Fx wycinka [N]</th><th>Fz wycinka [N]</th><th>CD</th><th>CL z wyporem</th><th>CL bez nominalnego wyporu</th><th>y+ średnie</th><th>y+ min</th><th>y+ max</th></tr>'+''.join(force_rows)+'</table></div><p>Wypór odniesienia: 22,7182 N. Przy U=0 CL/CD nie są definiowane. Średnie y+ jest ważone polem ściany. Czasy dotyczą solvera i raportowania, bez uruchamiania licencji, siatkowania i końcowego zapisu.</p>'
 img=Q/"plots/mesh_comparison.png"
 if img.exists():h+='<img style="width:100%" alt="Porównanie historii rozruchowych" src="data:image/png;base64,'+base64.b64encode(img.read_bytes()).decode()+'">'
 img=Q/'plots/Cp_startup.png'
 if img.exists():h+='<details><summary>Porównanie ciśnienia na profilu podczas rozruchu</summary><img style="width:100%" alt="Cp podczas rozruchu" src="data:image/png;base64,'+base64.b64encode(img.read_bytes()).decode()+'"></details>'
 img=Q/'plots/GPU_long_comparison.png'
 if img.exists():h+='<img style="width:100%" alt="Dłuższe próby GPU i różnica sił" src="data:image/png;base64,'+base64.b64encode(img.read_bytes()).decode()+'">'
 h+='<p>Rozdzielenie CFL: M03 GPU przy t=0,2 s — globalne 42,95; maksymalne w interfejsie (0,01 &lt; αw &lt; 0,99) 1,402 dla pełnego kroku czasu. Włączone subkroki VOF; to nie wartość CFL pojedynczego subkroku. Od t=0,16 do 0,20 s CL wzrosło o 3,87%, CD zmieniło się o −0,15%.</p>'
 h+=''.join(images)
 h+='<p>Koszt na c/U jest ekstrapolacją zmierzonej wydajności, nie czasem osiągnięcia zbieżności. Dotychczasowe 3D C003: 20,05 s/krok przy dt=10⁻⁵ s; 36,8 h na c/U. Redukcja wymiaru zmienia zakres modelowanej fizyki: brak wirów końcowych i oporu indukowanego pełnego płata.</p><h3>Dziennik quasi-2D</h3><table>'+log+'</table><p><code>'+escape(str(Q))+'</code></p></section>'
 return h,state
