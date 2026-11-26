from pathlib import Path
import json,datetime,csv,html,os
h=Path(__file__).resolve().parents[1]
def read(name):
 p=h/'validation'/name
 return json.loads(p.read_text(encoding='utf8')) if p.exists() else None
def esc(v):return html.escape(str(v))
def number(v,n=6):return f'{v:.{n}g}' if isinstance(v,(float,int)) else '—'
def link(path,label):
 return '<a href="'+esc(os.path.relpath(path,h).replace('\\','/'))+'">'+esc(label)+'</a>'
results=[]
for p in sorted((h/'validation').glob('SP_*stabilized_result*.json')):
 results.append(json.loads(p.read_text(encoding='utf8')))
result_by={r['case']:r for r in results if r.get('static_angle_deg',0)==0}
motion=read('SP_C_motion_verified.json')
rows=[]
rows.append('<tr><td>C01 · VOF</td><td>0° · profil oryginalny</td><td>309441</td><td>0,3156595</td><td>0,00700232</td><td>—</td><td>—</td><td>—</td><td>34,324*</td><td>Chroniona referencja</td></tr>')
for name,title in [('SP_A_original_singlephase','Oryginalny profil · jednofazowy'),('SP_B','Klapka 0° · bez Overset'),('SP_C','Klapka 0° · Overset')]:
 r=result_by.get(name)
 if not r:rows.append(f'<tr><td>{name}</td><td>{title}</td><td colspan="7">W toku / brak zaakceptowanego wyniku</td><td>Oczekuje</td></tr>');continue
 moment=number(r.get('moment_mean_Nm')) if name!='SP_A_original_singlephase' else '—'
 vals=[name,title,r['cells'],number(r['CL_mean']),number(r['CD_mean']),number(r['Fx_mean_N']),number(r['Fz_mean_N']),moment,number(r['pabs_min_all_accepted_Pa']/1000,5),link(r['checkpoint'],'Zapisany .sim')]
 rows.append('<tr>'+''.join('<td>'+str(x)+'</td>' for x in vals)+'</tr>')
for angle in [2,-2,5,-5]:
 r=next((r for r in results if r.get('case')=='SP_C' and r.get('static_angle_deg')==angle),None)
 if r:
  vals=['SP_C',f'Klapka {angle:+g}°',r['cells'],number(r['CL_mean']),number(r['CD_mean']),number(r['Fx_mean_N']),number(r['Fz_mean_N']),number(r['moment_mean_Nm']),number(r['pabs_min_all_accepted_Pa']/1000,5),link(r['checkpoint'],'Zapisany .sim')]
  rows.append('<tr>'+''.join('<td>'+str(x)+'</td>' for x in vals)+'</tr>')
 else:rows.append(f'<tr><td>SP_C</td><td>Klapka {angle:+g}°</td><td colspan="7">Oczekuje na sprawdzenie poprzedniego etapu</td><td>Nie rozpoczęto</td></tr>')
meshrows=[]
for key in ['SP_B','SP_C']:
 r=read(key+'_mesh_verified.json')
 if r:meshrows.append('<tr>'+''.join('<td>'+str(v)+'</td>' for v in [key,r['cells'],r.get('negative_volume_cells',0),r.get('unclosed_cells',0),number(r['min_volume_m3']),number(r['min_cell_quality']),number(r['min_face_validity'])])+'</tr>')
progress=[]
for folder in [h/'cases/SP_B_split0_fixed',h/'cases/SP_C_split0_overset']:
 p=max(folder.rglob('progress.txt'),key=lambda p:p.stat().st_mtime,default=None)
 if p:progress.append('<li>'+esc(p.parent.name)+': '+esc(p.read_text(encoding='utf8').strip())+'</li>')
timestamp=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
body=f'''<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>NTNU — raport kampanii klapki</title><style>body{{font:16px/1.5 system-ui,sans-serif;color:#243442;background:#f3f6f8;margin:0}}main{{max-width:1200px;margin:30px auto;padding:26px;background:white;border-radius:12px}}h1,h2{{color:#124b69}}h1{{font-size:28px}}h2{{font-size:21px;margin-top:32px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #dbe3e8}}th{{background:#edf3f6}}.scroll{{overflow-x:auto}}img{{max-width:100%;height:auto;border:1px solid #dbe3e8}}.note{{background:#fff3d9;padding:14px;border-left:4px solid #d89622}}small{{color:#5b6c76}}code{{overflow-wrap:anywhere}}a{{color:#146c94}}</style><main>
<h1>NTNU · ruchoma klapka — kampania hydrodynamiczna</h1><p>Stan na <b>{timestamp}</b>. STAR-CCM+ 2606.0002, build 21.04.009-R8. Kampania aktywna; raport jest aktualizowany z zapisanych plików.</p>
<p>NACA 66-012 modified z rodzimej geometrii C01; zawias x/c = 0,80, oś +y, szczelina nominalna 2,5 mm, rozpiętość 0,02 m. U = 18 m/s, ρ = 1000 kg/m³, μ = 0,001 Pa·s, Re = 2,142·10⁷, SST URANS.</p>
<div class="note">Wyniki służą ocenie mechaniki i stabilizacji przepływu. Nie potwierdzono niezależności od siatki ani kroku czasu. Nie zatwierdzono danych do treningu. W04, kampania falowa i DRL nie są uruchamiane w tym zadaniu.</div>
<h2>Wyniki i stan przypadków</h2><div class="scroll"><table><tr><th>Przypadek</th><th>Wariant</th><th>Komórki</th><th>CL</th><th>CD</th><th>Fx [N]</th><th>Fz [N]</th><th>Mh [Nm]</th><th>pmin abs. [kPa]</th><th>Stan / plik</th></tr>{''.join(rows)}</table></div>
<p><small>CL odejmuje wypór hydrostatyczny; siły Fz i moment zawiasowy obejmują pełne obciążenie ciśnieniem. Moment raportowany na samej klapce, względem osi +y. Średnie z ostatniego okna 0,05 s; pmin jest minimum z całego zaakceptowanego przebiegu. *C01: minimum na płacie w zapisanym punkcie odniesienia, nie minimum z nowej historii URANS.</small></p>
<h2>Kontrola siatki 2,5D</h2><div class="scroll"><table><tr><th>Wariant</th><th>Komórki</th><th>Ujemne objętości</th><th>Niedomknięte</th><th>Vmin [m³]</th><th>Jakość min.</th><th>Face validity min.</th></tr>{''.join(meshrows)}</table></div>
<p>Końcowe komórki leżą w jednej warstwie między y = 0,01 i 0,03 m; centroidy mają y = 0,02 m. Naprawa wykorzystuje natywne wyciągnięcie przekroju i korektę orientacji ścian. Nie usuwano wadliwych komórek w celu ukrycia błędów.</p>
<p>Ustawiono 48 warstw przy profilu i 24 przy łuku zawiasu. Są to parametry generatora. Automatyczna detekcja warstw w siatkach directed/extruded ma ograniczenia opisane w dokumentacji STAR; sam wskaźnik Prism Layer Number nie potwierdza pełnej liczby warstw. Kontrolowane są też geometria warstw i y+ po uruchomieniu przepływu.</p>
'''
if motion:
 body+=f'''<h2>Ruch i łączność Overset</h2><p>Przeszedł test {motion['steps']} kroków, od −5° do +5°, czas fizyczny 0,2 s przy zamrożonym przepływie. Maksimum błędnych komórek Overset: {motion['max_overset_error_cells']:g}; trudnych interpolacji: {motion['max_difficult_interpolation_cells']:g}. Najmniejsza objętość podczas ruchu: {motion['min_volume_m3']:.4g} m³. Interpolacja Linear quasi2D.</p><p>{link(motion['checkpoint'],'Plik .sim po pełnym teście ruchu')} · {link(motion['animation'],'Animacja natywnej siatki')}</p><img src="reports/flap_gap25mm_native_motion.gif" alt="Natywna animacja ruchu w szczelinie"><p><small>Zbliżenie na zawias i szczelinę, odtwarzanie spowolnione. To test mechaniki; przepływ hydrodynamiczny był zamrożony.</small></p><img src="reports/flap_native_geometry_range.png" alt="Rodzima geometria i zakres wychyleń">'''
body+='<h2>Historie czasowe</h2>'
for key in ['SP_A','SP_B','SP_C']:
 p=h/f'reports/{key}_stabilized_history.png'
 if p.exists():body+=f'<img src="reports/{key}_stabilized_history.png" alt="Historia {key}">'
body+='''<h2>Kryteria i ograniczenia</h2><ul><li>Statyczny URANS: dt = 2 ms po kontroli kontynuacji oryginalnego płata z dt = 0,4 ms. Co najmniej 0,2 s, trzy kolejne stabilne okna po 0,05 s; limit przebiegu 1 s.</li><li>Zmiana średnich: CL &lt; 0,5%, CD &lt; 1%; rozstęp w oknie odpowiednio &lt; 1% i &lt; 2%. Względny bilans masy &lt; 10⁻⁴. To kontrola stabilizacji sił, nie pełna walidacja hydrodynamiczna.</li><li>Woda 20°C: ciśnienie pary 2339,215 Pa; wymagany zapas 10 kPa, czyli pabs &gt; 12339,215 Pa. Badanie ciśnienia nie zastępuje modelu kawitacji.</li><li>W SP_B wystąpiły lokalne obniżenia ciśnienia daleko od płata, przy górnej granicy x ≈ 27–37 m, z ≈ 7,7–7,8 m. Minimum na samym płacie pozostawało wyższe. Wymaga to uwagi przy dalszej ocenie zbieżności; zachowano konserwatywne minimum globalne.</li><li>A/B zawiera wpływ zmiany geometrii i siatki. B/C ocenia dodatkowy wpływ Overset i jego siatki. A/C01 jest pomostem do VOF na oryginalnej siatce; nie wymaga się identycznych współczynników.</li><li>Jednofazowy model nie potwierdza braku wentylacji ani wpływu powierzchni swobodnej. Referencyjna wysokość ciśnienia z = 2 m została zachowana.</li></ul><h2>Bieżące obliczenia i kolejność</h2>'''
body+='<ul>'+''.join(progress)+'</ul><p>Po sprawdzeniu przypadku 0°: +2°, −2°, +5°, −5°. Testy sinusoidalne dopiero po poprawnych przypadkach statycznych. Nieudane i niedokończone próby pozostają diagnostyką.</p>'
body+='<p>Praca na F:\\ntnu\\flap_control. Oryginalne C01/W01/W03 i procesy PRE_W04 pozostają poza zakresem zmian tego zadania. '+link(h.parent/'HOME_RESUME_INSTRUCTIONS.md','Instrukcja wznowienia')+'</p></main></html>'
(h/'CAMPAIGN_REPORT_PL.html').write_text(body,encoding='utf8')
with (h/'validation/campaign_results.csv').open('w',newline='',encoding='utf-8-sig') as f:
 fields=['case','static_angle_deg','status','cells','CL_mean','CD_mean','Fx_mean_N','Fz_mean_N','moment_mean_Nm','pabs_min_all_accepted_Pa','checkpoint','training_approved']
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(results)
print(json.dumps(dict(report=str(h/'CAMPAIGN_REPORT_PL.html'),accepted_static_results=len(results),at=timestamp)))
