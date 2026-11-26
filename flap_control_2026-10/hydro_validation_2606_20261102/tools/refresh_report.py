from pathlib import Path
import sys,json,csv,html,datetime,statistics,re
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools/deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
O=R/'reports';O.mkdir(exist_ok=True)
def readj(p):
 try:return json.loads(p.read_text())
 except:return {}
def rows(p):
 try:return list(csv.DictReader(p.open(encoding='utf-8-sig')))
 except:return []
def link(p,label=None):return '<a href="'+html.escape(str(p.relative_to(R)).replace('\\','/'))+'">'+html.escape(label or p.name)+'</a>'
def image(p):return '<img src="'+html.escape(str(p.relative_to(R)).replace('\\','/'))+'">' if p.exists() else ''
def fmt(v):
 try:return f'{float(v):.7g}'
 except:return str(v)
def table(data,cols):
 return '<table><tr>'+''.join('<th>'+html.escape(c)+'</th>' for c in cols)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(fmt(r.get(c,'')))+'</td>' for c in cols)+'</tr>' for r in data)+'</table>'
blocks=[];evidence=[];summary=[]
for case in sorted((R/'cases').glob('SP_*')):
 mesh=readj(case/'mesh_summary.json');piece=['<h2>'+html.escape(case.name)+'</h2>']
 if mesh:piece += [table([mesh],['cells','min_cell_quality','min_face_validity','min_volume_m3']),image(case/'mesh_foil.png'),image(case/'mesh_hinge.png')]
 for d in sorted(case.rglob('steady_init_*')):
  st=readj(d/'initialization_status.json');hist=rows(d/'steady_iterations.csv')
  if not st:continue
  piece += ['<h3>Inicjalizacja stacjonarna: '+d.name+'</h3><p>'+html.escape(st.get('status',''))+'. To iteracje numeryczne, nie historia czasu fizycznego.</p>',link(d/'steady_iterations.csv','Pełna historia iteracji')]
  if hist:
   piece.append(table([hist[-1]],['iteration','CL_hydro','CD','p_absolute_min_Pa','mass_imbalance_relative','yplus_mean','yplus_max']))
   fig,axs=plt.subplots(1,3,figsize=(12,3.4),layout='constrained');x=[float(a['iteration']) for a in hist]
   for ax,key,ylabel in zip(axs,['CL_hydro','CD','p_absolute_min_Pa'],['CL hydrodynamiczne','CD','p_abs min [Pa]']):
    ax.plot(x,[float(a[key]) for a in hist],lw=1.4);ax.set(xlabel='Iteracja stacjonarna',ylabel=ylabel);ax.grid(alpha=.25)
   axs[2].axhline(12339.214766776897,c='r',ls='--',lw=1,label='próg 12.339 kPa');axs[2].legend(fontsize=8)
   p=O/(case.name+'_'+d.name+'.png');fig.savefig(p,dpi=160);plt.close(fig);piece.append(image(p))
  evidence.append(dict(case=case.name,path=str(d),kind='steady_initialization',status=st))
 for d in sorted(case.rglob('smoke_*')):
  st=readj(d/'status.json');meta=readj(d/'metadata.json');hist=rows(d/'history.csv')
  if not st:continue
  piece += ['<h3>Transient: '+d.name+'</h3><p><b>'+html.escape(st.get('status',''))+'</b>; '+str(st.get('steps',0))+' kroków. Krótki smoke test nie potwierdza niezależności od siatki ani kroku czasu.</p>']
  if hist:piece += [table([hist[-1]],['time_s','CL_hydro','CD','Fx_N','Fz_N','Mh_Nm','p_absolute_min_Pa','safety_reserve_Pa']),link(d/'history.csv','CSV wszystkich kroków i lokalizacji minimum ciśnienia')]
  if (d/'checkpoint.sim').exists():piece += ['<p>'+link(d/'checkpoint.sim','Zapis .sim — sprawdź status powyżej przed użyciem')+'</p>']
  evidence.append(dict(case=case.name,path=str(d),kind='transient_smoke',status=st,metadata=meta))
  if st.get('status')=='smoke_passed_not_converged' and hist:
   summary.append(dict(case=case.name,source=str(d),status='smoke_passed_not_converged',cells=meta.get('cells'),CL_hydro=statistics.mean(float(a['CL_hydro']) for a in hist[-10:]),CD=statistics.mean(float(a['CD']) for a in hist[-10:]),pmin=min(float(a['p_absolute_min_Pa']) for a in hist),training_approved=False))
 for d in sorted(case.glob('motion_*')):
  st=readj(d/'motion_status.json');err=d/'motion_error.txt'
  piece += ['<h3>Ruch: '+d.name+'</h3>']
  if st:piece += [table([st],['mechanics_passed','steps','max_angle_error_deg','min_quality','max_difficult_interpolation_cells']),image(d/'flap_motion.gif')]
  elif err.exists():piece += ['<p class="warn">'+html.escape(err.read_text())+'</p>']
  else:piece += ['<p>Test w toku lub brak potwierdzonego wyniku.</p>']
  evidence.append(dict(case=case.name,path=str(d),kind='motion_only',status=st,error=err.read_text() if err.exists() else None))
 blocks.append(''.join(piece))
refs=readj(R/'validation/methodological_references.json')
refhtml=''.join('<li><a href="'+html.escape(a['url'])+'">'+html.escape(a['author']+' ('+str(a['year'])+')')+'</a>: '+html.escape(a['applicability'])+'</li>' for a in refs.get('references',[]))
now=datetime.datetime.now().astimezone().isoformat()
body='''<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>NTNU — model hydrodynamiczny klapki</title><style>body{font:16px/1.6 system-ui;color:#172b3b;max-width:1180px;margin:32px auto;padding:0 20px;background:#f8fafc}h1,h2,h3{line-height:1.25}h2{border-top:2px solid #d8e2eb;padding-top:24px;margin-top:35px}table{border-collapse:collapse;display:block;overflow:auto;font-size:14px;margin:18px 0}td,th{border:1px solid #d8e2eb;padding:8px;text-align:left;white-space:nowrap}th{background:#e8eff5}img{max-width:100%;height:auto;background:white;border:1px solid #d8e2eb;margin:16px 0}a{color:#12659a}.warn{padding:15px;background:#fff1cf;border-left:4px solid #dd9a13}code{overflow-wrap:anywhere}</style><h1>NTNU — ruchoma klapka, etap hydrodynamiki</h1>'''
body+='<p>Aktualizacja: '+now+'</p><p class="warn"><b>Model w weryfikacji.</b> Żadne wyniki z tego etapu nie są zatwierdzone do treningu. W04, fale, DRL i model zastępczy nie zostały uruchomione przez to zadanie. Niepowodzenia poniżej pozostają oznaczone jako odrzucone.</p>'
body+='<p>STAR-CCM+ 2606.0002 (21.04.009-R8), CPU, Microsoft MPI. U = 18 m/s, ρ = 1000 kg/m³, μ = 0.001 Pa·s, Re = 2.142×10⁷, SST k–ω, rozpiętość 0.02 m. Zawias x/c = 0.80 na lokalnej linii szkieletowej; profil pochodzi z oryginalnej geometrii C01.</p>'
body+='<p>Minimalny luz w geometrycznym przeglądzie co 0.1° od −5° do +5°: 2.49717 mm. To sprawdzenie geometrii; poprawność Overset wymaga osobnego testu siatki w ruchu.</p>'+image(O/'geometry_native_gap25mm.png')
body+='<h2>Porównanie i konwencje</h2><p>Referencja C01 w VOF: CL = 0.31565950495122014, CD = 0.007002316911710474, 309441 komórek, t = 4.6992 s. SP_A zachowuje oryginalną siatkę i profil w wodzie jednofazowej. SP_B wprowadza podział i szczelinę bez Overset. SP_C dodaje Overset do tej samej geometrii. Różnica A/B obejmuje niepewność zmienionej siatki; B/C musi być oceniona razem z niepewnością interpolacji i dyskretyzacji. Most A/C01 izoluje wpływ modelu powierzchni swobodnej przy tej samej siatce, dopiero po kontroli zbieżności czasowej.</p>'
body+='<p>Fx i Fz obejmują ciśnienie statyczne z hydrostatyką. CL_hydro = (Fz − wypór)/(0.5ρU²S), CD = Fx/(0.5ρU²S), S = 0.0238 m². Moment dodatni wokół +y: dla profilu podzielonego tylko klapka; dla SP_A cały profil, więc tych momentów nie porównuje się bezpośrednio.</p>'
body+=table(summary,['case','status','cells','CL_hydro','CD','pmin']) if summary else '<p>Brak zakończonego, poprawnego testu URANS do tabeli porównawczej.</p>'
body+='<p>Próg przesiewowy kawitacji: p_abs &gt; 2339.214767 + 10000 = 12339.214767 Pa (20°C). Rezerwa bezpieczeństwa to różnica względem tego progu. Zgodność p_abs = p_piezometryczne + p_ref + ρg(2−z) i gęstość są sprawdzane przed testem. Model jednofazowy nie weryfikuje wentylacji; h_clear względem z = 2 m jest wyłącznie wartością wirtualną.</p>'
body+=''.join(blocks)
body+='<h2>Pozostałe warunki dopuszczenia</h2><p>Poprawny stationary 0° dla A/B/C, kontrola rzeczywistej rozdzielczości szczeliny i pryzmatów, ruch ±5° bez błędów Overset, ograniczona czułość siatki i Δt. Następnie statyczne ±2°/±5°, a po ich przejściu ruch ±2° przy dwóch częstotliwościach. Testy falowe oraz trening wymagają kolejnego etapu. Duże wartości y+ w lokalnych miejscach i wszystkie przypadki rozbieżności wymagają wyjaśnienia przed dopuszczeniem danych.</p><h2>Źródła i ograniczenia walidacji</h2><ul>'+refhtml+'</ul></html>'
(R/'REPORT_HYDRO_PL.html').write_text(body,encoding='utf8')
(R/'validation/stage_evidence.json').write_text(json.dumps(dict(updated_at=now,training_approved=False,runs=evidence,comparison=summary),indent=2),encoding='utf8')
print(json.dumps({'report':str(R/'REPORT_HYDRO_PL.html'),'evidence_runs':len(evidence),'passed_smokes':len(summary)}))
