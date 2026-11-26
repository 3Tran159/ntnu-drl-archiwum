from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,csv,hashlib,math,datetime,re,html
R=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
g=json.loads((R/'geometry/geometry.json').read_text())
polys=json.loads((R/'geometry/profile_polygons.json').read_text())
im=Image.new('RGB',(1200,500),'white');d=ImageDraw.Draw(im)
def xy(p):return (70+p[0]*850,310-p[1]*850)
for name,color in [('main',(45,88,130)),('flap',(220,111,40))]:
 d.polygon([xy(p) for p in polys[name]],fill=color)
h=xy((g['hinge_x_m'],g['hinge_z_m']))
d.line((h[0]-10,h[1],h[0]+10,h[1]),fill='black',width=2);d.line((h[0],h[1]-10,h[0],h[1]+10),fill='black',width=2)
d.text((35,25),'NACA 66-012 modified — native exported profile',font=font,fill='black')
d.text((35,60),'Rounded flap nose and matching recess; hinge x/c = 0.80; span = 0.02 m',font=small,fill='black')
d.text((35,445),'Geometry preview. Coarse PoC clearance; no hinge or servo hardware.',font=small,fill='black')
im.save(R/'visualization/geometry_native_profile.png')
if not (R/'audit/transient_pass.json').exists():
 print('GEOMETRY_PREVIEW_READY; CFD results not yet complete')
 raise SystemExit(0)
motion=list(csv.DictReader((R/'runs/motion_check.csv').open()))
transient=list(csv.DictReader((R/'runs/transient.csv').open()))
frames=sorted((R/'visualization').glob('frame_*.png'))[:21]
assert len(frames)==21 and len(motion)==100 and len(transient)==30
annotated=[]
for k,p in enumerate(frames):
 im=Image.open(p).convert('RGB');canvas=Image.new('RGB',(im.width,im.height+62),'white');canvas.paste(im,(0,62));d=ImageDraw.Draw(canvas)
 t=k*.01;delta=0 if k==0 else float(motion[k*5-1]['measured_deg'])
 d.text((18,8),f'STAR-CCM+ 2606 | moving overset mesh | t = {t:.3f} s | flap = {delta:+.2f} deg',font=font,fill=(20,35,50))
 d.text((18,35),'Native modified profile. Playback slowed 8x. Flow solver frozen during this motion test.',font=small,fill=(60,70,80))
 annotated.append(canvas)
annotated[0].save(R/'visualization/flap_motion.gif',save_all=True,append_images=annotated[1:],duration=80,loop=0)
strip=Image.new('RGB',(1200,3*397),'white')
for row,k in enumerate([0,5,15]):
 strip.paste(annotated[k].resize((1200,794)).resize((600,397)),(300,row*397))
strip.save(R/'visualization/motion_extremes.png')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest()
source=Path('E:/ntnu_mesh_optimization_20261030/clean_c01_campaign_20261101/C01_warm_M13_steady_rho1000_air1p2_20261101/final.sim')
expected='9af4857b948e0494088b5421f8ede100e66344fc2631cc00030406640d7cc295'
assert sha(source)==expected and sha(R/'input_copy.sim')==expected
passed=json.loads((R/'audit/motion_pass.json').read_text())
case=R/'FlapPOC_2606_working.sim';assert case.stat().st_size>100000
cells=int((R/'audit/cell_count.txt').read_text())
summary=dict(at=datetime.datetime.now().astimezone().isoformat(),version='STAR-CCM+ 2606.0002, 21.04.009-R8',cells=cells,geometry=g,geometry_clearance=json.loads((R/'audit/geometry_clearance.json').read_text()),motion=passed,transient=json.loads((R/'audit/transient_pass.json').read_text()),forces={n:dict(min=min(float(r[n]) for r in transient),max=max(float(r[n]) for r in transient),last=float(transient[-1][n])) for n in ['Fx_N','Fz_N','Mh_Nm']},case=str(case),case_sha256=sha(case),source_C01_sha256=expected,source_C01_unchanged=True,reference_copy_unchanged=True,old_campaign_queues_modified=False,legacy_W07_lambda92p5_launched=False)
(R/'audit/final_test_report.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
rows=''.join(f'<tr><td>{n}</td><td>{summary["forces"][n]["min"]:.6g}</td><td>{summary["forces"][n]["max"]:.6g}</td><td>{summary["forces"][n]["last"]:.6g}</td></tr>' for n in summary['forces'])
report=f'''<!doctype html><html lang="pl"><meta charset="utf-8"><title>Test ruchomej klapki NACA 66 012 modified w STAR CCM 2606</title>
<style>body{{font:17px Arial,sans-serif;max-width:1000px;margin:40px auto;color:#1d2b38;line-height:1.5}}h1{{font-size:30px}}h2{{font-size:23px;margin-top:32px}}img{{max-width:100%;border:1px solid #ddd}}table{{border-collapse:collapse;width:100%}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}code{{font-size:14px}}.ok{{padding:18px;background:#e6f5ea;border-left:5px solid #268448}}</style>
<h1>Test ruchomej klapki NACA 66 012 modified w STAR CCM 2606</h1>
<p class="ok">Ruch siatki i krótki transient w spokojnej wodzie zakończone. Gotowy case: <a href="FlapPOC_2606_working.sim">FlapPOC_2606_working.sim</a>. To demonstrator mechaniki; siły są orientacyjne.</p>
<h2>Geometria i model</h2><p>Profil pochodzi z natywnej geometrii istniejącego NACA 66-012 modified. Zawias leży na lokalnej linii szkieletowej przy x/c = 0,80: x = {g['hinge_x_m']:.9f} m, z = {g['hinge_z_m']:.9f} m. Oś jest równoległa do rozpiętości, w kierunku +y. Klapka obejmuje około 20% cięciwy i ma zaokrąglony nos o promieniu {g['nose_radius_m']*1000:.2f} mm, dopasowaną wnękę i powiększony prześwit promieniowy {g['gap_m']*1000:.2f} mm. Najmniejsza odległość części w geometrycznej kontroli −5°…+5° wyniosła {summary['geometry_clearance']['minimum_separation_m']*1000:.2f} mm.</p>
<p>Układ quasi-2D ma rozpiętość 0,02 m i płaszczyzny symetrii na bokach. Ruch sztywny klapki obsługuje osobny region overset. Siatka ma {cells:,} komórek, bez warstw pryzmatycznych. Jednofazowa woda ma gęstość 1000 kg/m³ i lepkość 0,001 Pa s. Prędkość 1 m/s, model laminarny i mała domena służą wyłącznie testowi mechaniki. Nie odpowiadają docelowemu badaniu 18 m/s z VOF i SST.</p>
<img src="visualization/geometry_native_profile.png" alt="Natywny profil z klapką">
<h2>Test ruchu siatki</h2><p>Najpierw wykonano 100 kroków po 0,002 s przy zamrożonym solverze przepływu. Kąt zadany: δ = 5° sin(2πt/0,2 s). Jeden pełny cykl obejmuje oba skrajne wychylenia. Obrót kontrolowano przez odczyt transformacji ruchu po stronie solvera dla wirtualnego punktu związanego sztywno z klapką. Klatki rzeczywistej siatki potwierdzają kierunek ruchu i oba skrajne wychylenia. Nie używano średnich z aktywnych powierzchni overset jako znacznika położenia.</p>
<table><tr><th>Kontrola</th><th>Wynik</th></tr><tr><td>Maksymalna różnica transformacji i kąta zadanego</td><td>{passed['max_angle_error_deg']:.6g}°</td></tr><tr><td>Minimalna objętość komórki</td><td>{passed['min_volume_m3']:.6g} m³</td></tr><tr><td>Minimalna jakość komórki</td><td>{passed['min_quality']:.6g}</td></tr><tr><td>Minimalna face validity</td><td>{passed['min_face_validity']:.6g}</td></tr></table>
<p><a href="runs/motion_check.csv">Pełny zapis testu ruchu</a>. Animacja pokazuje klatki z rzeczywistej siatki STAR, odtwarzane osiem razy wolniej.</p><img src="visualization/flap_motion.gif" alt="Rzeczywisty ruch siatki overset">
<h2>Krótki transient</h2><p>Po przejściu testu ruchu odblokowano przepływ i wykonano 30 kroków, łącznie 0,06 s, z maksymalnie 8 iteracjami wewnętrznymi. Fx i Fz obejmują obie części profilu. Moment Mh dotyczy tylko klapki i jest liczony względem zawiasu. Dodatnie kierunki to +x, +z i moment wokół +y. Siły dotyczą warstwy o rozpiętości 0,02 m, bez przeliczania na pełną rozpiętość.</p>
<table><tr><th>Raport</th><th>Minimum</th><th>Maksimum</th><th>Ostatnia próbka</th></tr>{rows}</table><p><a href="runs/transient.csv">Przebiegi Fx, Fz i Mh</a>. Tak krótki rozruch nie daje ustalonych sił ani walidacji hydrodynamicznej.</p>
<h2>Pliki i następny krok</h2><p>Gotowy plik zatrzymuje kontynuację po osiągnięciu t = 0,4 s. Zawiera ruch, raporty i scenę <b>Flap POC mesh motion</b>. Pliki mesh_ready i motion_passed zachowują wcześniejsze punkty kontrolne. Geometria, makra i dzienniki są w podfolderach geometry, macros, runs i audit.</p>
<p>Dopiero po ocenie tej mechaniki należy przenieść geometrię i ruch na dokładniejszą siatkę. Dalsze porównanie calm–wave musi korzystać z tej samej nowej siatki i spójnej fizyki. C01 pozostaje oryginalnym odniesieniem dotychczasowej kampanii. Fale, DRL i model zastępczy nie były uruchamiane w tym etapie.</p>
<h2>Ochrona istniejących obliczeń</h2><p>Oryginalny C01 i jego odrębna kopia zachowały SHA-256 <code>{expected}</code>. Nie zmieniano C01, W01, W03 ani istniejących kolejek. Nie uruchomiono wykluczonej starej W07 λ = 92,5 m. Próby PoC korzystały wyłącznie z CPU; przydział zwiększono do 4 procesów po zgodzie użytkownika.</p>
<p>Data raportu: {summary['at']}. <a href="audit/final_test_report.json">Dane kontroli i sumy plików</a>.</p></html>'''
(R/'REPORT_PL.html').write_text(report,encoding='utf8')
print(json.dumps(summary,indent=2))
