# 21-09-2026 — Kontrolni run mašine, skripta za metrike, ocenjivanje u toku

Grana: **`main`** (`hierarchical-benchmark` je umergovana). Nastavak na
[`20-09-2026 c107 kompletan, c105 ponovo lokalno, otvoreno pitanje masine.md`](20-09-2026%20c107%20kompletan,%20c105%20ponovo%20lokalno,%20otvoreno%20pitanje%20masine.md).

---

## Trenutno stanje

**Korak 1 je kompletan i na `main`-u:** 4 konfiguracije × 5 ponavljanja = 20 runova,
**1.200 odgovora, 0 grešaka, 0 odsečenih konteksta**, 2 presečena odgovora.

**Ocenjivanje je pokrenuto i radi u ovom trenutku** (od 02:40). Po jedan run iz svake
konfiguracije, procena završetka oko **06:00**. Detalji i kako se proverava — niže.

Serverova grafička je i dalje otpala; provereno 21-09 u 00:38 UTC, opterećenje 0.23, kartica se ne
prijavljuje. Sve generisanje posle 19-09 je zato išlo lokalno.

---

## Glavni nalaz: mašina menja odgovore, ali malo

Pušten je kontrolni run `diag_machine_c101_r01` (oznaka `c101ctrl`) — konfiguracija `c101`
prikupljena **lokalno**, da se uporedi sa pet istih runova sa servera. Svrha: utvrditi da li se
generisanje na dve mašine razlikuje više nego što se ponavljanja razlikuju međusobno.

### Pretraga — identična, kako je i moralo

| | doc-hit@5 | MRR | kontekst |
|---|---|---|---|
| `c101` server, 5 runova | 0.981 | 0.735 | 5.126 |
| `c101ctrl` Mac, 1 run | **0.981** | **0.735** | 5.126 |

Provereno i strože od metrika: **istih pet pasusa, istim redosledom, u svih 60 pitanja.** Time je
potvrđeno i da je postavka bila fiksirana, i da mašina ne dira pretragu. Sve metrike pretrage u
radu su mašinski nezavisne.

### Dužina odgovora — unutar raspona

```
server, 5 runova : 235, 213, 254, 228, 216   (raspon 213–254)
Mac              : 219                        ← unutar
```

### ROUGE-L — van raspona

```
server, 5 runova : 0.1602, 0.1540, 0.1590, 0.1571, 0.1460   (raspon 0.1460–0.1602)
Mac              : 0.1735                                    ← iznad svih pet
```

Odstupanje **3.2 standardne devijacije** od serverske sredine. Pomak je širok, ne od par ispada:
Mac je viši na 38 od 60 pitanja, medijana razlike po pitanju `+0.0067`. Tri najveća rasta ipak nose
46% ukupne razlike, dakle rep raspodele dosta doprinosi.

### Kako ovo treba čitati

**Merljivo jeste. Primetno nije.** Apsolutna razlika je `+0.018` na osnovici od `0.155`, dakle
~12%, a medijana po pitanju `+0.0067`. Ono „3.2 sigme" je izjava o **preciznosti merenja, ne o
veličini efekta** — pet serverskih runova je izuzetno usaglašeno (st. dev. `0.0057`), pa i sitan
pomak ispadne mnogo sigmi.

Pročitana su dva odgovora jedan pored drugog. `REAL_010` (pitanje sa najvećim rastom ROUGE-a u
celom runu):

> **Server:** „Da, možete se identifikovati na prijemnom ispitom i kasnije tijekom studija pasošem,
> ako nema lične karte koja je isteka."
> **Mac:** „Da, možete identifikovati se na prijemnom ispitom pomoću pasoša ako nije važeća lična
> karta."

Druge reči, isti smisao, oba tačna. `REAL_003` je rečitiji: oba odgovora **greše na isti način** —
oba pogrešno tumače Član 32 i oba kreću u izmišljenu računicu.

**Zaključak koji se sme izvući:** mašina menja *kako* je odgovor sročen; po pročitanim primerima ne
menja *da li* je tačan. **Zaključak koji se NE sme izvući:** da uticaja nema. To nije izmereno —
jedini pravi test je da sudija oceni i kontrolni run i uporedi sa serverskim, a to još nije urađeno.

**Za rad:** ograničenje se prijavljuje pošteno — „generisanje je izvršeno na dve mašine; pretraga je
identična, ROUGE pokazuje pomak reda 0.018". Ne sme se napisati „provereno, nema razlike".

Kontrolni run **nije deo matrice** — nosi zasebnu oznaku `c101ctrl` da ga `summarize_matrix.py` ne
spoji sa `c101` kao šesto ponavljanje.

---

## Skripta za metrike (`scripts/summarize_matrix.py`)

Do sada su metrike računate ad-hoc, u različitim sesijama, bez zapisane konvencije — zbog čega je
juče pola sata potrošeno na lažnu uzbunu o imenima dokumenata. Sada postoji skripta.

```bash
venv/bin/python scripts/summarize_matrix.py            # markdown
venv/bin/python scripts/summarize_matrix.py --latex    # za rad
venv/bin/python scripts/summarize_matrix.py --per-run  # po pojedinacnom runu
```

Ugrađene su dve stvari namerno:

**Konvencija je u kodu i u ispisu.** Metrike se računaju isključivo nad pitanjima sa
`expected_behavior=answer` (52 od 60), i **svaka tabela to piše u zaglavlju**. Ostalih 8 traži
uzdržavanje ili pojašnjenje i za njih ne postoji dokument koji je trebalo dohvatiti.

**Upozorenje kad se pretraga razlikuje između ponavljanja.** Pretraga je deterministička, pa
razlika nije šum nego znak da nešto nije bilo fiksirano. Skripta to ispiše i kaže da se takvi
brojevi ne smeju prijavljivati dok se ne objasne.

Rezultat je u `docs/MATRIX_RESULTS.md`, generisan komandom:

| Config | Embedding | Chunking | doc-hit@5 | MRR | Kontekst med/max | Odgovor tok. |
|---|---|---|---|---|---|---|
| `c101` | MiniLM-L6 | flat | 0.981 | 0.735 | 5.126 / 5.128 | 229 |
| `c103` | MiniLM-L6 | hierarchical | 0.942 | **0.825** | 17.880 / 20.908 | 230 |
| `c105` | bge-m3 | flat | **1.000** | 0.804 | 5.127 / 5.128 | 205 |
| `c107` | bge-m3 | hierarchical | 0.962 | 0.739 | 14.980 / 21.263 | 208 |

Vrednosti su **tačne, ne proseci sa šumom** — pretraga je deterministička, pa je identična u svih
pet ponavljanja svake konfiguracije.

**Obrazac se ne ponavlja na oba embedinga:** kod MiniLM-a hijerarhijski diže MRR (0.735 → 0.825),
kod bge-m3 ga spušta (0.804 → 0.739). **Ne tumačiti dok ne stignu ocene kvaliteta.**

6 novih testova, **82/82 prolazi**.

---

## Ocenjivanje koje trenutno radi

Pokrenuto 02:40, po jedan run iz svake konfiguracije:
`c101_r01` → `c103_r01` → `c105_r01` → `c107_r01`. 240 odgovora, ~49 s po odgovoru, procena **~3.3 h**,
dakle gotovo oko **06:00**.

Sudija je **llama4 na reviziji 3** (obrazloženje pa `OCENA: <broj>`), preko SSH-a. Digest i
`prompt_sha256` su provereni pri pokretanju.

### Zašto run-po-run, a ne sve odjednom

`score_benchmark_run.py` **skuplja ocene u memoriji i upisuje fajl tek na kraju** — nema međuupisa
ni nastavka. Gore od toga: `LLMJudgeMetric` hvata grešku po odgovoru, pa **pad tunela ne ruši proces
nego svaki preostali odgovor upiše kao grešku**, i na kraju uredno napiše fajl koji izgleda gotov.
To je isti obrazac koji nas je prevario kod `c105_r03`.

Zato svaki run ide kao **zaseban proces** i pravi svoj fajl — pad tunela odnese najviše jedan run.
Posle svakog runa skripta ispisuje **koliko je odgovora stvarno ocenjeno**, ne koliko ih ima.

Pokretačka skripta je ad-hoc, u scratchpad-u, nije u repou. Ako se pokaže dobrom, vredi je uneti
kao `scripts/score_matrix.sh`.

### Šta pogledati ujutru

```bash
cat benchmarking/runs/_logs/score_four.log          # tok, i koliko je stvarno oceneno po runu

# raspodela ocena i greske u parsiranju
venv/bin/python - <<'PY'
import json, glob, collections
for run in ('c101','c103','c105','c107'):
    f = sorted(glob.glob(f'benchmarking/runs/dev_combined_{run}_r01/scores/*llm_judge*.json'))
    if not f: print(run, 'nema fajla'); continue
    res = json.load(open(f[-1]))['results']
    sc = [(r['scores'].get('llm_judge') or {}).get('score') for r in res]
    print(run, 'ocenjeno', sum(1 for s in sc if s is not None), '/', len(sc),
          '| prosek', round(sum(s for s in sc if s is not None)/max(1,sum(1 for s in sc if s is not None)),2),
          '|', dict(sorted(collections.Counter(sc).items(), key=lambda x: (x[0] is None, x[0]))))
PY
```

Tri stvari koje odlučuju da li se ide dalje:

1. **Koliko odgovora nije uspelo da se isparsira.** Ako ih je mnogo, protokol treba doterati pre
   preostalih 16 runova.
2. **Raspodela ocena.** Stara je imala 40 od 60 zalepljenih na 4.0. Ako se to ponovi, sudija i
   dalje ne radi.
3. **Poređenje četiri konfiguracije po kvalitetu**, prvi put.

---

## Izmenjeni fajlovi

| Fajl | Šta |
|---|---|
| `scripts/summarize_matrix.py` | **nov** — zbirna tabela, markdown/LaTeX/po-runu |
| `tests/test_summarize_matrix.py` | **nov** — 6 testova |
| `docs/MATRIX_RESULTS.md` | **nov** — generisana tabela koraka 1 |
| `benchmarking/runs/diag_machine_c101_r01` | **nov** — kontrolni run, oznaka `c101ctrl` |

Commiti: `b766b8a` (skripta), `c9c59d3` (tabela), `cd07a8a` (ispravka izveštaja),
`22edc04` (merge u `main`).

---

## Šta ostaje

1. **Rezultat noćašnjeg ocenjivanja** — tri provere gore. Prvo to, pa tek onda preostalih 16 runova
   (~16 h).
2. **Ručna provera slaganja.** Oceniti ~20 odgovora sam i uporediti sa sudijom. `judge_profile.json`
   to i traži („verify human agreement before freezing paper results"). Bez toga se ocene ne smeju
   zamrznuti za rad.
3. **Pitanje mašine** — ostaje otvoreno. Najjeftiniji način da se razreši je još 2–3 kontrolna runa,
   da se porede dve raspodele umesto raspodele i jedne tačke (~40 min). Alternativa: oceniti
   kontrolni run sudijom i uporediti ocene, ne ROUGE.
4. **`known_issue` u `judge_profile.json`** — `JUDGE_SYSTEM` još sadrži red „Vrati tačno jedan broj
   … bez objašnjenja", koji protivreči novom promptu. Namerno ostavljen jer je merenje izvršeno sa
   njim; čisti se pri prvom ponovnom ocenjivanju.
5. **`c101_r03`/`REAL_008` i `c107_r04`/`REAL_049`** — presečeni odgovori. Za `REAL_049` je
   utvrđeno da je degenerisano generisanje (model je počeo da izmišlja dodatna pitanja), ne odsečen
   dobar odgovor. Odluka pri ocenjivanju.
6. **Drugi generator** — cela desna kolona matrice (`c102`, `c104`, `c106`, `c108`) ne postoji.

---

## Važno za nastavak

**Vremena izvršavanja se ne prijavljuju kao rezultat.** Dve mašine, a deo serverskih runova je
prikupljen dok je grafička već otkazivala.

**Osa embedinga se poklapa sa osom mašine** (`c101`/`c103` server, `c105`/`c107` Mac). Poređenje po
osi **chunkovanja** je čisto — `c101` naspram `c103` i `c105` naspram `c107` su unutar iste mašine.
Poređenje po osi **embedinga** nije.

**Mac mora ostati otvoren i na punjaču** dok ocenjivanje traje — tunel ide sa njega, a `caffeinate`
ne pomaže kad se zatvori poklopac.
