import json
from html import escape
def render_panel(root):
    rows=[]
    for folder in sorted(root.glob("coarse012_C*")):
        f=folder/"measurement.json"
        if not f.exists():
            rows.append("<tr><td>"+escape(folder.name)+"</td><td colspan='6'>Pomiar jeszcze niedostępny</td></tr>");continue
        d=json.loads(f.read_text());m=d["metrics"]
        invalid=sum(m.get(k,0) or 0 for k in ["NegativeVolumeCells","UnclosedCells","DegeneratedFeCells"])
        rows.append("<tr><td>%s</td><td>%s</td><td>%d</td><td>%.3g</td><td>%.3g</td><td>%.2f°</td><td>%.3f%%</td></tr>"%(escape(d["case_id"]),f'{m["cell_count"]:,}',invalid,m.get("min_cell_quality",float("nan")),m.get("min_volume_change",float("nan")),m.get("max_skewness_angle_deg",float("nan")),100*m.get("foil_area_fraction_full_15_prism_layers",float("nan"))))
    if not rows:return ""
    return """<section class="panel" id="geometry012"><h2>Aktualna geometria: 012 — zweryfikowana w NX i STAR</h2>
<p>Grubość 11,998%, wygięcie 2,500%, rozpiętość 11 m. Zapis: <code>F:\\ntnu\\geometry_012_20261029</code>.
S<sub>half</sub> = 5,450434 m². Oryginalne HF_v2.prt i HF_v2.x_t zawierają profil 010 i pozostały zachowane.</p>
<h3>Nowe siatki diagnostyczne dla profilu 012</h3><div class="scroll"><table><thead><tr>
<th>Case</th><th>Komórki</th><th>Ujemne / otwarte / zdegenerowane</th><th>Min. quality</th><th>Min. volume change</th><th>Max. skewness</th><th>Pełne 15 pryzm — pole</th>
</tr></thead><tbody>"""+''.join(rows)+"""</tbody></table></div>
<p class="muted">Siatki wygenerowane, solver nieuruchomiony. y+, siły i przydatność do NWAR pozostają do sprawdzenia. Starsze wykresy i przypadki A/B/D poniżej dotyczą profilu 010.</p></section>"""
