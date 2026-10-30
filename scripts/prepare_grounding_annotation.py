"""Prepare offline, blinded human context-support forms and summarize exported ratings.

No API calls. Run `python scripts/prepare_grounding_annotation.py prepare`.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import random
import sys

if __package__:
    from .evaluate_grounding import load_inputs, norm
else:
    from evaluate_grounding import load_inputs, norm

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "human_context_support_v1"
LABELS = ("fully_supported", "partly_supported", "unsupported", "no_claims")
TITLES = {"fully_supported": "Potpuno podržan", "partly_supported": "Delimično podržan",
          "unsupported": "Nepodržan", "no_claims": "Bez činjeničnih tvrdnji"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_fingerprint(records):
    return digest([{k: row[k] for k in ("blind_id", "question", "answer", "context")} for row in sorted(records, key=lambda r: r["blind_id"])])


def make_payload(records, annotator, sample_hash, subset_hash, seed=6821):
    ordered = sorted(records, key=lambda r: r["blind_id"])
    random.Random(seed + (1 if annotator == "B" else 0)).shuffle(ordered)
    return {"protocol": PROTOCOL, "annotator": annotator, "sample_sha256": sample_hash,
            "subset_sha256": subset_hash, "items": [{k: row[k] for k in ("blind_id", "question", "answer", "context")} for row in ordered]}


def build_key(records, seed=6821):
    overlap = []
    for cell in sorted({r["cell"] for r in records}):
        pool = sorted([r for r in records if r["cell"] == cell], key=lambda r: r["blind_id"])
        random.Random(f"{seed}:human-grounding:{cell}").shuffle(pool)
        overlap += [r["blind_id"] for r in pool[:5]]
    return {"protocol": PROTOCOL, "sample_sha256": sample_fingerprint(records), "seed": seed,
            "a_ids": sorted(r["blind_id"] for r in records), "b_ids": sorted(overlap),
            "items": {r["blind_id"]: {k: r[k] for k in ("run", "question_id", "cell")} for r in records}}


def validate_ratings(data, key, records, annotator):
    ids = key[annotator.lower() + "_ids"]
    if (data.get("protocol") != PROTOCOL or data.get("annotator") != annotator
            or data.get("sample_sha256") != key["sample_sha256"]
            or data.get("subset_sha256") != digest(ids)):
        raise ValueError(f"Ratings {annotator}: wrong protocol, annotator or frozen sample.")
    grades = data.get("grades")
    if not isinstance(grades, dict) or set(grades) != set(ids):
        raise ValueError(f"Ratings {annotator}: every assigned answer must be rated exactly once ({len(ids)} total).")
    lookup = {r["blind_id"]: r for r in records}
    for bid, grade in grades.items():
        if not isinstance(grade, dict) or grade.get("label") not in LABELS:
            raise ValueError(f"Invalid rating: {bid}.")
        note, evidence = grade.get("note"), grade.get("evidence")
        if not isinstance(note, str) or not isinstance(evidence, str):
            raise ValueError("Notes and evidence must be strings.")
        if grade["label"] in {"partly_supported", "unsupported"} and not note.strip():
            raise ValueError(f"Explain unsupported/contradicted claims in the note: {bid}.")
        if evidence.strip() and norm(evidence) not in norm(lookup[bid]["context"]):
            raise ValueError(f"Evidence must be an exact single excerpt from the delivered context: {bid}.")
    return grades


def kappa(a, b):
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum(a.count(label) * b.count(label) for label in LABELS) / n ** 2
    return (po - pe) / (1 - pe) if pe < 1 else None


def distributions(grades, key):
    groups = {"overall": list(grades)}
    for bid in grades:
        groups.setdefault(key["items"][bid]["cell"], []).append(bid)
    report = {}
    for group, ids in groups.items():
        counts = {label: sum(grades[i]["label"] == label for i in ids) for label in LABELS}
        with_claims = len(ids) - counts["no_claims"]
        report[group] = {"n": len(ids), "counts": counts,
                         "proportions_all_answers": {k: v / len(ids) for k, v in counts.items()},
                         "answers_with_claims": with_claims,
                         "fully_supported_fraction_among_answers_with_claims": counts["fully_supported"] / with_claims if with_claims else None}
    return report


def summarize(root, output, a_path, b_path=None):
    key = read(output / "analysis_key_private.json")
    records, _ = load_inputs(root, root / "benchmarking/grounding/analysis_key_DO_NOT_OPEN_BEFORE_ANNOTATION.json")
    if sample_fingerprint(records) != key["sample_sha256"]:
        raise ValueError("Source answers/context changed after the forms were frozen.")
    a = validate_ratings(read(a_path), key, records, "A")
    result = {"protocol": PROTOCOL, "primary_annotator": "A", "primary_distributions": distributions(a, key),
              "interpretation": "Human answer-level context support categories; not atomic-claim faithfulness. Descriptive stratified sample; 20 answers/configuration. No-claim cases reported separately. A is the predefined primary rater; B independently checks a predefined 30-answer subset. Report agreement before discussion, and retain both original exports. Do not treat 120 answers as 120 independent questions across cells."}
    disagreements = []
    if b_path:
        b = validate_ratings(read(b_path), key, records, "B")
        ids = key["b_ids"]
        x, y = [[grades[i]["label"] for i in ids] for grades in (a, b)]
        matrix = {label: {other: sum(i == label and j == other for i, j in zip(x, y)) for other in LABELS} for label in LABELS}
        result["independent_overlap_agreement"] = {"n": len(ids), "exact_agreement": sum(i == j for i, j in zip(x, y)) / len(ids),
                                                   "cohen_kappa": kappa(x, y), "confusion_matrix_A_rows_B_columns": matrix}
        result["secondary_subset_distributions"] = distributions(b, key)
        disagreements = [{"blind_id": i, **key["items"][i], "A": a[i], "B": b[i]} for i in ids if a[i]["label"] != b[i]["label"]]
        write(output / "disagreements.json", disagreements)
    write(output / "summary.json", result)
    lines = ["# Human context-support evaluation", "", "Primary rater A; categories describe entire answers, not fractions of supported claims.", "",
             "| Configuration | n | Fully supported | Partly supported | Unsupported | No factual claims |",
             "|---|---:|---:|---:|---:|---:|"]
    for name, group in result["primary_distributions"].items():
        lines.append("| " + " | ".join([name, str(group["n"])] + [str(group["counts"][label]) for label in LABELS]) + " |")
    if b_path:
        agreement = result["independent_overlap_agreement"]
        lines += ["", f"Independent overlap: n={agreement['n']}; exact agreement={agreement['exact_agreement']:.3f}; Cohen kappa={agreement['cohen_kappa']}. Disagreements: {len(disagreements)}."]
    else:
        lines += ["", "Secondary independent review is not yet available."]
    lines += ["", result["interpretation"]]
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


HTML = r'''<!doctype html>
<html lang="sr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ručna provera podrške u kontekstu</title>
<style>
body{font:16px system-ui;margin:0;background:#f2f5f8;color:#17212e}main{max-width:1300px;margin:auto;padding:20px}header,.box{background:white;padding:18px;border-radius:10px;margin-bottom:16px;border:1px solid #dce2e9}h1{font-size:24px;margin:0 0 8px}h2{font-size:18px;margin:0 0 10px}button,select{padding:9px;margin:4px;border:1px solid #b8c4d2;border-radius:6px;background:white;cursor:pointer}button.primary{background:#174e87;color:white}button:disabled{opacity:.45;cursor:default}.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.grid{display:grid;grid-template-columns:1fr 1.25fr;gap:16px}.text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}.context{max-height:650px;overflow:auto;background:#f8fafc;padding:14px;white-space:pre-wrap}textarea{box-sizing:border-box;width:100%;min-height:75px;padding:10px;font:inherit;border:1px solid #b8c4d2;border-radius:6px}label.choice{display:block;padding:10px;border:1px solid #dce2e9;margin:8px 0;border-radius:6px}small,.muted{color:#526477}#message{font-weight:600}details li{margin:8px 0}.error{color:#a62020}.success{color:#21623c}@media(max-width:800px){.grid{grid-template-columns:1fr}}progress{width:180px}input[type=radio]{margin-right:8px}
</style><main>
<header><h1>Ručna provera podrške u kontekstu — ocenjivač <span id="who"></span></h1>
<p>Pročitaj odgovor i kontekst koji je model dobio. Proveravaj podršku u tom tekstu; ne koristi prethodne ocene, očekivani odgovor ni spoljno znanje.</p>
<details open><summary><b>Kriterijum ocenjivanja — pročitaj pre početka</b></summary><ul>
<li><b>Potpuno podržan:</b> sve bitne činjenične tvrdnje i zaključak imaju podršku u kontekstu, direktno ili jasnim izvođenjem iz konteksta i eksplicitnih podataka iz pitanja.</li>
<li><b>Delimično podržan:</b> postoji podržan deo odgovora, ali i bar jedna bitna nepotkrepljena ili protivrečna tvrdnja, pogrešno obrazloženje ili izmišljen uslov; glavni zaključak ipak ima podršku.</li>
<li><b>Nepodržan:</b> glavni odgovor/zaključak nema dovoljnu podršku ili protivreči kontekstu. Tačni sporedni detalji ne menjaju ovu oznaku. Ako nema direktnog zaključka, a postoje bitne podržane i nepodržane tvrdnje, koristi „delimično podržan”. Ako nijedna bitna tvrdnja nije podržana, koristi „nepodržan”.</li>
<li><b>Bez činjeničnih tvrdnji:</b> samo uzdržavanje, traženje pojašnjenja ili preporuka, bez tvrdnji o propisima. „Nisam našao odgovor u kontekstu” samo po sebi ne računa se kao regulatorna tvrdnja. Ako odgovor ipak navede pravilo, koristi ostale oznake.</li>
<li>Ne ocenjuj stil, dužinu, relevantnost ili potpunost. Ako je odgovor nerelevantan, ali su sve njegove tvrdnje potkrepljene, može biti potpuno podržan. Ova provera je odvojena od ranijih ocena kvaliteta 0–5.</li>
<li>Čitaj nove odredbe posle „briše se i umesto njega...”; stari tekst citiran radi brisanja ne dokazuje da pravilo i dalje važi. Ako je primenljivost nejasna, označi nedostatak podrške i objasni neizvesnost.</li>
<li>Ne popravljaj nečitljive formule spoljnim znanjem. Razlikuj stečene i preostale ESPB, potreban i dovoljan uslov, upis i nastavak studija. U računima koristi samo jasno pravilo i eksplicitne podatke pitanja.</li>
<li>Za delimično podržan/nepodržan odgovor obavezno napiši koju tvrdnju kontekst ne podržava ili joj protivreči. Opcionalno kopiraj jedan tačan odlomak kao dokaz; nemoj spajati odlomke sa „...”.</li>
</ul><p>Ocenjujte nezavisno, pre razgovora o pojedinačnim ocenama. Ocenjivač A ocenjuje 120 odgovora; B nezavisno proverava unapred izabranih 30 (5 po konfiguraciji). Modeli i konfiguracije su sakriveni.</p></details>
<div class="toolbar"><b id="progressText"></b><progress id="progress"></progress><button id="export" class="primary">Preuzmi JSON ocene</button><button id="import">Učitaj svoje JSON ocene</button><input id="file" type="file" accept=".json" hidden></div>
<p class="muted" id="storage"></p><p id="message" role="status"></p>
</header>
<div class="box toolbar"><button id="prev">← Prethodni</button><span id="position"></span><button id="next">Sledeći →</button><button id="unfinished">Prvi neocenjeni</button><label>Idi na <select id="jump"></select></label></div>
<div class="box"><h2>Pitanje</h2><div id="question" class="text"></div></div>
<div class="grid"><section><div class="box"><h2>Odgovor modela</h2><div id="answer" class="text"></div></div><div class="box"><h2>Tvoja ocena podrške</h2><div id="choices"></div><label>Napomena — obavezna za delimično podržan/nepodržan odgovor<textarea id="note" placeholder="Koja tvrdnja nema podršku? Da li nedostaje dokaz ili joj kontekst protivreči?"></textarea></label><label>Dokaz iz konteksta — opciono, kopiraj jedan neprekinuti odlomak<textarea id="evidence" placeholder="Može ostati prazno, posebno kada dokaz nedostaje."></textarea></label><p id="validation" class="error"></p></div></section>
<section class="box"><h2>Tačno dostavljeni kontekst</h2><p class="muted">Prikazan je ceo kontekst bez skraćivanja. Možeš označiti i kopirati relevantan tekst.</p><div id="context" class="text context"></div></section></div>
</main><script type="application/json" id="data">__DATA__</script><script>
'use strict';
const data=JSON.parse(document.getElementById('data').textContent);
const names={fully_supported:'Potpuno podržan',partly_supported:'Delimično podržan',unsupported:'Nepodržan',no_claims:'Bez činjeničnih tvrdnji'};
const $=id=>document.getElementById(id), normal=s=>s.trim().split(/\s+/u).join(' ');
const storageKey=data.protocol+':'+data.annotator+':'+data.sample_sha256+':'+data.subset_sha256;
let grades={},position=0,storageOk=true;
function errorFor(item,g){if(!g||!Object.hasOwn(names,g.label))return 'Izaberi oznaku.';if(typeof g.note!=='string'||typeof g.evidence!=='string')return 'Neispravan format ocene.';if(['partly_supported','unsupported'].includes(g.label)&&!g.note.trim())return 'Dodaj kratko obrazloženje.';if(g.evidence.trim()&&!normal(item.context).includes(normal(g.evidence)))return 'Dokaz nije jedan tačan odlomak konteksta; kopiraj ga ponovo ili ostavi prazno.';return '';}
function message(text,bad=false){$('message').textContent=text;$('message').className=bad?'error':'success';}
try{const saved=JSON.parse(localStorage.getItem(storageKey)||'null');if(saved&&saved.grades)grades=saved.grades;if(Number.isInteger(saved?.position)&&saved.position>=0&&saved.position<data.items.length)position=saved.position;}catch(e){storageOk=false;}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify({grades,position}));}catch(e){storageOk=false;}$('storage').textContent=storageOk?'Unosi se automatski čuvaju u ovom pregledaču. Redovno preuzimaj JSON, obavezno pre zatvaranja ili promene računara.':'Pregledač ne dozvoljava automatsko čuvanje. Obavezno preuzimaj JSON da ne izgubiš unose.';}
function refresh(){const done=data.items.filter(i=>!errorFor(i,grades[i.blind_id])).length;$('progressText').textContent=done+' / '+data.items.length+' završeno';$('progress').max=data.items.length;$('progress').value=done;for(let i=0;i<data.items.length;i++)$('jump').options[i].textContent=(i+1)+(!errorFor(data.items[i],grades[data.items[i].blind_id])?' ✓':'');$('validation').textContent=grades[data.items[position].blind_id]?errorFor(data.items[position],grades[data.items[position].blind_id]):'';}
function render(){const item=data.items[position],g=grades[item.blind_id]||{};for(const field of ['question','answer','context'])$(field).textContent=item[field];$('position').textContent=(position+1)+' / '+data.items.length+' · '+item.blind_id;$('note').value=g.note||'';$('evidence').value=g.evidence||'';for(const input of document.querySelectorAll('input[name=label]'))input.checked=input.value===g.label;$('jump').value=position;$('prev').disabled=position===0;$('next').disabled=position===data.items.length-1;refresh();persist();}
function update(){const label=document.querySelector('input[name=label]:checked')?.value||'';grades[data.items[position].blind_id]={label,note:$('note').value,evidence:$('evidence').value,updated_at:new Date().toISOString()};persist();refresh();}
for(const [value,title] of Object.entries(names)){const label=document.createElement('label');label.className='choice';const radio=document.createElement('input');radio.type='radio';radio.name='label';radio.value=value;radio.addEventListener('change',update);label.append(radio,document.createTextNode(title));$('choices').append(label);}
data.items.forEach((_,i)=>{const option=document.createElement('option');option.value=i;option.textContent=i+1;$('jump').append(option);});
$('who').textContent=data.annotator;$('note').addEventListener('input',update);$('evidence').addEventListener('input',update);
$('prev').onclick=()=>{if(position>0){position--;render();}};$('next').onclick=()=>{if(position<data.items.length-1){position++;render();}};$('jump').onchange=()=>{position=Number($('jump').value);render();};$('unfinished').onclick=()=>{const p=data.items.findIndex(i=>errorFor(i,grades[i.blind_id]));if(p<0)message('Sve ocene su završene. Preuzmi JSON.');else{position=p;render();}};
$('export').onclick=()=>{const out={protocol:data.protocol,annotator:data.annotator,sample_sha256:data.sample_sha256,subset_sha256:data.subset_sha256,exported_at:new Date().toISOString(),grades};const blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='grounding_ocene_'+data.annotator+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);message('JSON je preuzet. Dozvoljen je izvoz delimičnih ocena za rezervnu kopiju.');};
$('import').onclick=()=>$('file').click();$('file').onchange=async()=>{try{const f=$('file').files[0];if(!f)return;const incoming=JSON.parse(await f.text());for(const key of ['protocol','annotator','sample_sha256','subset_sha256'])if(incoming[key]!==data[key])throw Error('Fajl pripada drugom ocenjivaču ili uzorku.');if(!incoming.grades||Array.isArray(incoming.grades)||typeof incoming.grades!=='object')throw Error('Neispravan grades objekat.');const ids=new Set(data.items.map(i=>i.blind_id));for(const [id,g] of Object.entries(incoming.grades)){if(!ids.has(id)||!g||typeof g.note!=='string'||typeof g.evidence!=='string'||(g.label!==''&&!Object.hasOwn(names,g.label)))throw Error('Neispravna ocena ili ID.');}if(!confirm('Učitane ocene zameniće trenutne unose ovog obrasca. Prethodno preuzmi rezervnu kopiju. Nastaviti?'))return;grades=incoming.grades;render();message('Ocene su učitane.');}catch(e){message(e.message,true);}finally{$('file').value='';}};
render();
</script></html>'''


def prepare(root, output):
    records, _ = load_inputs(root, root / "benchmarking/grounding/analysis_key_DO_NOT_OPEN_BEFORE_ANNOTATION.json")
    key = build_key(records)
    output.mkdir(parents=True, exist_ok=True)
    key_path = output / "analysis_key_private.json"
    if key_path.exists() and read(key_path) != key:
        raise ValueError("Existing forms use a different frozen sample. Use a new --output directory.")
    write(key_path, key)
    for annotator in ("A", "B"):
        ids = key[annotator.lower() + "_ids"]
        payload = make_payload([r for r in records if r["blind_id"] in ids], annotator, key["sample_sha256"], digest(ids))
        encoded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        (output / f"ocenjivac_grounding_{annotator}.html").write_text(HTML.replace("__DATA__", encoded), encoding="utf-8")
    print(f"Prepared A: 120 answers; B: 30 independent overlap answers. Output: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "summarize"))
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--a", type=Path)
    parser.add_argument("--b", type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    output = (args.output or root / "benchmarking/grounding/human").resolve()
    if args.command == "prepare":
        prepare(root, output)
    elif args.a is None:
        parser.error("summarize requires --a; provide --b when the independent 30-answer review is complete")
    else:
        summarize(root, output, args.a, args.b)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
