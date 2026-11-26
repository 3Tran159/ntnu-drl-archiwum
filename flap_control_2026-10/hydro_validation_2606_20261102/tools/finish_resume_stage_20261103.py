"""Review the prepared pose and record the session; no solver launch."""
from pathlib import Path
import csv,datetime,hashlib,html,json,re,shutil
H=Path(__file__).resolve().parents[1];R=H.parent
P=H/'cases/SP_C_split0_overset/static_plus2_prepared_20261103_085250'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,d):
 tmp=p.with_suffix(p.suffix+'.review.tmp');tmp.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8');tmp.replace(p)
status=read(P/'status.json');state=read(H/'NIGHT_QUEUE_STATE.json')
assert status['status']=='static_pose_prepared' and status['pose_steps']==10 and status['hydrodynamic_steps']==0
assert abs(status['saved_time_s']-.67)<1e-10 and status['flow_solvers_frozen'] is False
assert state.get('active') is None and state['jobs']['prepare_static_plus2_20261103']['state']=='completed'
with (P/'pose_preparation.csv').open() as f:rows=list(csv.DictReader(f))
assert len(rows)==10 and all(r['flow_solved']=='false' for r in rows)
assert all(abs(float(r['angle_deg'])-.2*int(r['step']))<.001 for r in rows)
audits=[]
for tag in ['initial']+['pose_'+str(i) for i in range(1,11)]+['prepared']:
 text=(P/('full_audit_'+tag+'.txt')).read_text()
 values={k:float(v) for k,v in re.findall(r'(total|active|inactive|acceptors|errors|difficult_interpolation|min_volume|min_quality|max_acceptor_size_ratio)=([-+.eE0-9]+)',text)}
 assert values['total']==333939 and values['errors']==values['difficult_interpolation']==0 and values['min_volume']>0 and values['min_quality']>0
 assert values['active']+values['inactive']+values['acceptors']==333939 and values['acceptors']>0
 audits.append(values)
cp=P/'SP_C_plus2_prepared_NOT_SOLVED_2606.sim';before=cp.stat()
with cp.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
after=cp.stat();assert before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
log=Path(state['jobs']['prepare_static_plus2_20261103']['log']).read_text(encoding='utf8',errors='replace')
assert any('Saving:' in line and str(cp) in line and 'complete (' in line for line in log.splitlines())
assert 'Server process exited with code : 0' in log or re.search(r'Server process exited with code\s*:\s*0',log)
info=(H/'audit/static_plus2_checkpoint_info_20261103.txt').read_text(encoding='utf8')
assert re.search(r'Time\s+0.67',info) and re.search(r'Iter\s+11570',info)
at=datetime.datetime.now().astimezone().isoformat()
result=dict(at=at,status='PREPARED_NOT_SOLVED',accepted_as_prepared_pose=True,angle_deg=2,saved_time_s=.67,iteration=11570,source_hydrodynamic_time_s=.65,hydrodynamic_steps=0,pose_steps=10,flow_solvers_frozen=False,dt_s=.002,inner_iterations=40,maximum_next_time_s=.72,checkpoint=str(cp),bytes=after.st_size,sha256=digest,native_save_complete=True,native_metadata_verified=True,native_full_reopen_verified=False,mesh_cells=333939,final_native_audit=audits[-1],maximum_error_cells=0,maximum_difficult_interpolation_cells=0,minimum_cell_volume_m3=min(x['min_volume'] for x in audits),minimum_cell_quality=min(x['min_quality'] for x in audits),training_approved=False,quantitative_validation=False,notes=['Flow fields retained/interpolated from C0; approximate warm start, not a +2degree solution.','Mesh clock advanced by0.020s through frozen-flow pose steps; do not use those forces or times as a hydrodynamic result.','Review temporal restart treatment and settling in the next bounded diagnostic.','No remesh, initialization, solution clearing or time reset.'])
write(H/'audit/STATIC_PLUS2_PREPARATION_REVIEW_20261103.json',result);write(P/'work_review.json',result)
cfg=read(H/'NIGHT_QUEUE.json');cfg['accept_new_jobs']=False;write(H/'NIGHT_QUEUE.json',cfg)
review=read(H/'WORK_CURRENT_REVIEW.json')
review.update(at=at,status='HOLD_PLUS2_PREPARED_NOT_SOLVED',current_run=str(P),current_case_checkpoint={'path':str(cp),'bytes':after.st_size,'sha256':digest,'saved_time_s':.67},last_decision='C0 accepted for kinematics only. Full +/-5degree sweep passed. Static +2degree pose prepared and native save/metadata verified; zero hydrodynamic steps. Local queue is HOLD with no pending jobs.',next='First +2degree bounded hydrodynamic diagnostic from prepared checkpoint:dt0.002,40inner,max time0.720(25steps),review temporal restart,pressure,mass,residual and Overset before any continuation.',next_test='Review and run only the first +2degree hydrodynamic diagnostic in a new copy; no later angles queued.',obstacle='No mechanical blocker. +2degree hydrodynamic response remains uncomputed; formal grid/time,far-field and energy validation remain open.',static_preparation_review=str(H/'audit/STATIC_PLUS2_PREPARATION_REVIEW_20261103.json'))
write(H/'WORK_CURRENT_REVIEW.json',review)
motion=read(H/'audit/KINEMATIC_POC_REVIEW_20261103.json');accept=read(H/'audit/C0_KINEMATIC_BASE_ACCEPTANCE_20261103.json')
with (H/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=at,kind='resume_stage_complete_hold',static_preparation=result,next=review['next'],queue_accept_new_jobs=False))+'\n')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy2(R/'HOME_RESUME_INSTRUCTIONS.md',H/'audit'/('HOME_RESUME_INSTRUCTIONS_before_stage_close_'+stamp+'.md'))
instructions=f'''# NTNU CFD — stan po wznowieniu 03.11.2026

Aktualizacja: {at}. Kampania wznowiona na wyraźne polecenie użytkownika.
Lokalny kontroler pozostaje w HOLD, accept_new_jobs=false; brak oczekujących zadań.
Nie uruchamiaj drugiego kontrolera ani nie odtwarzaj ukończonych zadań.
Brak automatycznego startu po uruchomieniu Windows.

## Sprawdzone checkpointy

C0, przepływ 0°: {accept['source_C0']}
t=0.650 s; iteracja11560;333939 komórek;dt0.002s;40 iteracji wewnętrznych.
SHA256 c8b2396f2d087112d06045b06a6c62e93c4003eafde969aa8c8d0ca8120afc10.
B0: {H / 'cases/SP_B_split0_fixed/relocation_reopen_20261103_native_audit/B0_recovered_t050.sim'}
t=0.500s;iteracja6250;256750komórek.
SHA256 929e577dec199f8311ba46516ca388cb76b5417a2038cae1b309064fc5b1cfed.
Oba pliki otwarto natywnie w STAR2606; pola i raporty odtworzono i porównano z zapisanymi eksportami.
Żadnego resetu, inicjalizacji ani remeshingu.
Niezmienne kopie relokacyjne: {R / 'checkpoints/RELOCATION_20261103_073441'}.

POC ruchu: {motion['checkpoint']}
t=0.850s;iteracja11660;100 kroków ±5°;przepływ/turbulencja pozostają ZAMROŻONE.
SHA256 {motion['checkpoint_sha256']}.
Ten plik służy do demonstracji ruchu, NIE do kontynuacji rozwiązania przepływu.
Animacja: {motion['animation']}.

Przygotowane +2°: {cp}
t=0.670s;iteracja11570;ostatnie10kroków to wyłącznie ustawienie klapki.
SHA256 {digest};rozmiar {after.st_size} bajtów.
Pełny zapis i natywny odczyt metadanych potwierdzone; osobnego pełnego ponownego otwarcia tego nowego pliku nie wykonywano.
Pola startowe pochodzą z C0t0.650; są zachowane/interpolowane przy zmianie położenia.
Klapka stała+2°;solver przepływu i turbulencji odblokowany;URANS SST;dt0.002;40inner;
URFprędkości0.8/ciśnienia0.2;schematy drugiego rzędu;top EXTRAPOLATED.
STOP czasu ustawiony na0.720s. NIE wykonano żadnego kroku hydrodynamicznego +2°.

## Kontynuacja — najpierw przejmij bieżący stan

1. Odczytaj NIGHT_STATUS.json,NIGHT_QUEUE_STATE.json,WORK_CURRENT_REVIEW.json i NIGHT_QUEUE.json w {H}.
2. Sprawdź rzeczywiste procesy STAR/MPI/Python. Jeśli istnieje kontroler, przejmij jego stan. Nie uruchamiaj drugiego.
3. RESUME_CFD.cmd został już wykonany dla relokacji. Jest historycznym, zabezpieczonym launcherem C0; nie powtarzaj go w celu rozpoczęcia +2°.
4. Dla następnego testu utwórz osobną kopię przygotowanego +2° i otwórz ją w STAR2606.0002 build21.04.009-R8.
   Użyj maksymalnie8 CPU,MPI ms,cpubind off,bez GPU. Licencja istniejącej kampanii jest już zatwierdzona; nie wypisuj klucza.
5. Sprawdź t0.670,iterację11570,stały kąt2°,pola,odblokowane solvery oraz limit0.720. Nie remeshuj,nie inicjalizuj i nie resetuj czasu.
6. Przygotuj ograniczony test hydrodynamiczny 25kroków do0.720s na nowej kopii. Oceń wpływ historii czasowej po zamrożonym ustawieniu klapki.
   Te25kroków to diagnostyka startu, a nie automatyczna akceptacja sił. Historia hydrodynamiczna zaczyna się dopiero po0.670s.
7. Kontroluj full OversetErrorStatus=0,brak trudnej interpolacji,dodatnie objętości,k/omega,residuals,bilans masy,
   minimum ciśnienia bezwzględnego >12339.2147668Pa (20°C,pv2339.2147668Pa,+10kPa),siły i moment.
8. Dopiero po ocenie pierwszego testu rozważ wydłużenie stabilizacji. Żadne −2°,±5°,fale,surrogate ani DRL nie są teraz w kolejce.

## Decyzja naukowa

B0 CL0.32661098,CD0.007191107,Mh−12.16019Nm;C0 CL0.32561949,CD0.007245937,Mh−12.04007Nm.
Różnice C/B CL−0.304%,CD+0.762%. Nie optymalizować Overset dla dalszego zmniejszania tych różnic.
Warunki B/C i numeryka zgodne;kontrola residuals,pol i stabilności domknięta dla POC.
C0 zaakceptowane do KINEMATYKI,nie jako pełna ilościowa walidacja hydrodynamiczna/energetyczna.
Pozostają: różne siatkiB/C,brak formalnego testu siatki/dt,pamięć zaburzeń daleko od płata oraz lokalne wysokiey+.
Pełny ruch100kroków ±5° przeszedł sprawdzenia,zero błędów Overset;minV{motion['minimum_full_cell_volume_m3']}m³;
minQuality{motion['minimum_full_cell_quality']};minimalna szczelina ograniczona od dołu do2.289mm.
Donory potwierdzone przez poprawny natywny stencil każdego akceptora;odrębnej liczby unikalnych donorów nie eksportowano.

Raporty: {H / 'reports/RESUME_AND_MOTION_20261103.html'}
AudytB/C: {H / 'reports/BC_RESUME_NUMERICAL_AUDIT_20261103.html'}
Dashboard: {H / 'NIGHT_DASHBOARD.html'}
Makra i skrypty: {H / 'macros'} oraz {H / 'tools'};nie odtwarzaj makr ukończonych etapów.
Źródła geometrii: {H / 'geometry'};profil modified NACA66-012 zachowany,zawiasx/c0.80,szerokość0.02m,szczelina0.0025m.
U18m/s,rho1000,mu0.001,Re21420000,grawitacja i odniesienie ciśnienia bez zmiany.
C01VOF CL0.3156595/CD0.00700232 pozostaje odrębną referencją. C01,W01,W03,PRE_W04 i cudze kolejki nietknięte.
W czasie audytu działał odrębny W04 w STAR2602,uruchomiony przez inną kolejkę. Nie zarządzaj nim z tej kampanii.
'''
(R/'HOME_RESUME_INSTRUCTIONS.md').write_text(instructions,encoding='utf8')
e=html.escape
def link(path,label):return '<a href="'+e(str(Path(path).relative_to(H)).replace('\\','/').replace('reports/','',1) if Path(path).parent==H/'reports' else '../'+str(Path(path).relative_to(H)).replace('\\','/'))+'">'+e(label)+'</a>'
report=f'''<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NTNU CFD — wznowienie i ruch klapki</title><style>body{{font:17px system-ui;max-width:1050px;margin:30px auto;padding:20px;line-height:1.5}}table{{border-collapse:collapse}}td,th{{padding:9px;border-bottom:1px solid #aaa;text-align:left}}img{{max-width:100%}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style><h1>Wznowienie i ruch klapki — 03.11.2026</h1><p>Stan: <b>HOLD — +2° przygotowane, przepływ nieuruchomiony.</b> C0 przyjęte do kinematyki POC. Pełna walidacja ilościowa i energetyczna pozostaje oddzielnym etapem.</p>
<h2>Odtworzenie stanu i audyt 0°</h2><p>STAR2606 poprawnie odtworzył C0t0.650/iter11560 oraz B0t0.500/iter6250. Eksporty pól i raporty zgadzają się z historiami. Nie resetowano rozwiązania ani czasu.</p><table><tr><th>Przypadek</th><th>CL średnia25</th><th>CD średnia25</th><th>Mh [Nm]</th></tr><tr><td>B0 bez Overset</td><td>0.32661098</td><td>0.007191107</td><td>−12.16019</td></tr><tr><td>C0 z Overset</td><td>0.32561949</td><td>0.007245937</td><td>−12.04007</td></tr></table><p>C/B: CL−0.304%,CD+0.762%. Zgodne fizyka,warunki brzegowe,dt,URF,40 iteracji i schematy. Wewnątrz kroku residuals istotnie maleją; najgorszy95percentyl final/first≈1.70·10⁻⁴ (z wyłączeniem Y-momentum na poziomie błędu zaokrągleń). Siły i moment mają mały dryf; bilans masy C0≈2.98·10⁻⁹. Brak dawnych niefizycznych pików Cp przy interfejsie. Minimum ciśnienia absolutnego C0≈30.10kPa;zapas nad parowaniem≈27.76kPa>10kPa.</p><p>Stare duże różnice sił wiązały się z wykrytymi artefaktami lokalnego Overset oraz niedostateczną zbieżnością przy górnej granicy. Poprawiona konfiguracja usuwa te objawy. Nie przypisano osobnej liczby procentowej każdej przyczynie. Pozostałej różnicy B/C nie używano jako celu dalszego strojenia.</p><p>{link(H/'reports/BC_RESUME_NUMERICAL_AUDIT_20261103.html','Szczegółowy audyt B/C')}</p><img src="BC_resume_audit_20261103.png" alt="Cp,yplus i stabilność B/C">
<h2>Pełny ruch ±5°</h2><p>333939komórek;100kroków;dt0.002s;okres0.2s;czas zapisany0.850s. Ruch sztywny wokół zawiasu x/c0.80 na lokalnej linii szkieletowej;oryginalny modified NACA66-012 i szerokość quasi2D zachowane. Przepływ i turbulencja zamrożone przez cały test.</p><table><tr><td>Błędy Overset / trudna interpolacja</td><td>0 / 0 we wszystkich100 położeniach</td></tr><tr><td>Akceptory</td><td>1456–1492;każdy z poprawną natywną interpolacją</td></tr><tr><td>Minimum objętości komórki</td><td>{motion['minimum_full_cell_volume_m3']:.6g}m³</td></tr><tr><td>Minimum CellQuality / FaceValidity</td><td>{motion['minimum_full_cell_quality']:.6f} / 1.0</td></tr><tr><td>Maksymalny błąd kąta / centroidu klapki</td><td>{motion['max_angle_error_deg']:.3g}° / {motion['max_mesh_centroid_error_m']:.3g}m</td></tr><tr><td>Minimalna szczelina w całym zakresie</td><td>≥2.289mm;konserwatywne ograniczenie z geometrii STL</td></tr></table><p>Łączność sprawdzono w100 położeniach solvera;dodatnia szczelina jest ograniczona także między próbkami. Nie eksportowano osobnej liczby unikalnych donorów.</p><img src="../{e(str(Path(motion['animation']).relative_to(H)).replace(chr(92),'/'))}" alt="Animacja natywnej siatki klapki"><p>Animacja spowolniona:3.15s odtwarzania dla0.2s ruchu. Siły z zamrożonego testu nie służą analizie hydrodynamicznej.</p><p>{link(motion['checkpoint'],'Plik .sim z zakończonym POC ruchu')}</p>
<h2>Przygotowane +2°</h2><p>Osobne wczytanie rozwiązania C0t0.650;10kroków ustawienia klapki przy zamrożonym przepływie. Końcowo+2°,t0.670,iter11570,333939komórek. Kontrola pełnej siatki przy każdym położeniu i po zakończeniu:bez błędów Overset i ujemnych objętości. Solvery przepływu/turbulencji odblokowano dopiero do zapisu gotowego przypadku. Nie wykonano obliczeń hydrodynamicznych +2°.</p><p>{link(cp,'Przygotowany plik +2° — NOT SOLVED')}</p><pre>SHA-256: {digest}\nRozmiar: {after.st_size} bajtów</pre><p>Zapis natywny i odczyt metadanych zakończone poprawnie. Pola stanowią przybliżony warm start po przemieszczeniu siatki;historia czasowa wymaga kontroli przed analizą sił.</p>
<h2>Następny eksperyment i ograniczenia</h2><p>Na nowej kopii przygotowanego +2°:pierwszy ograniczony test do0.720s(25kroków,dt0.002,40inner),z kontrolą residuals,masy,ciśnienia,turbulencji i Overset. Nie jest to z góry wystarczający czas stabilizacji. Ocena wyników poprzedza dalsze kroki. Żadne kolejne warianty nie są oczekujące.</p><ul>{''.join('<li>'+e(x)+'</li>' for x in accept['uncertainty'][:4])}</ul><p>Różnice siatek i kroku czasowego nie mają jeszcze formalnej oceny niepewności. Dalekie pole zachowuje pamięć rozruchu. Pełna weryfikacja pozostaje wymagana przed analizą energetyczną;fale,surrogate i DRL nieuruchomione.</p><p>Jeden istniejący kontroler;limit8CPU,bez GPU;checkpointy,logi,CSV,makra i historia decyzji zachowane na F:. Kontroler przekazano bez nakładania procesów. solver_state i operation są spójne;czas ruchu oddzielony od czasu rozwiązania przepływu.</p><p>Inne kampanie niezmienione. Wykryty odrębny W04 działa w STAR2602 z innej kolejki;nie został uruchomiony ani zatrzymany w ramach tego zadania.</p><small>Raport:{e(at)}</small></html>'''
(H/'reports/RESUME_AND_MOTION_20261103.html').write_text(report,encoding='utf8')
print(json.dumps(result,indent=2))
