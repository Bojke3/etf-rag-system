# 21-09-2026 — Ocenjivanje četiri konfiguracije: sudija radi, osa embedinga je kontaminirana

Grana: **`main`**. Nastavak na
[`21-09-2026 Kontrolni run masine, skripta za metrike, ocenjivanje u toku.md`](21-09-2026%20Kontrolni%20run%20masine,%20skripta%20za%20metrike,%20ocenjivanje%20u%20toku.md).

---

## Trenutno stanje

Prvi put su odgovori ocenjeni **po kvalitetu**, a ne samo po pretrazi. Ocenjen je po jedan run iz
svake od četiri konfiguracije: **237 od 240 odgovora**, trajalo 4 h 20 min (02:40 → 07:00).

**Popravka sudije je uspela** — raspodela ocena koristi ceo raspon i odustajanje više ne prolazi
kao dobar odgovor.

**Ali glavni nalaz nije rezultat nego problem:** najkrupnija razlika je pala na osu koja je
pomešana sa mašinom, pa se ne može pripisati embedingu. Test koji bi to razrešio je predložen i
**nije pokrenut** — odluka korisnika.

---

## Šta je pokrenuto

Sudija `llama4:latest` (digest `bf31604e25c2`) preko SSH-a na `rticuda`, profil **revizija 3** —
kratko obrazloženje pa red `OCENA: <broj>`. Metrike `rouge,llm_judge`.

Runovi: `c101_r01`, `c103_r01`, `c105_r01`, `c107_r01` — svaki kao **zaseban proces**, jer
`score_benchmark_run.py` upisuje fajl tek na kraju i ne ume da nastavi. Time bi pad tunela odneo
najviše jedan run. Tunel nije pao ni jednom.

**Brzina: 65 s po odgovoru**, ne 49 s kako je procenjeno iz ranijih merenja. Serverova grafička je
i dalje otpala, pa llama4 ide 100% na procesoru; razlika u odnosu na procenu je verovatno u dužini
obrazloženja. **Posledica za planiranje: preostalih 16 runova nije ~16 h nego ~17.5 h.**

---

## Rezultati

```
konf   ocenjeno   prosek   raspodela ocena
c101     59/60     2.41    0:11  1:10  2:14  3:2   4:12  5:10
c103     58/60     2.48    0:14  1:6   2:13  3:1   4:11  5:13
c105     60/60     2.95    0:10  1:5   2:14  3:1   4:9   5:21
c107     60/60     3.02    0:7   1:9   2:11  3:2   4:11  5:20
```

Za poređenje, stara rubrika na `dev_base_c001_r05`: prosek 3.12, ali **40 od 60 odgovora zalepljeno
na tačno 4.0**, bez ijedne 1 i bez ijedne 5.

### Prosek po očekivanom ponašanju

| očekivano ponašanje | n | prosek |
|---|---|---|
| `answer` | 205 | 2.70 |
| `partial_answer` | 16 | 2.50 |
| `abstain` | 12 | 3.08 |
| `clarify` | 4 | 3.25 |

---

## Polazni kvar je otklonjen — dokaz

Sudija je 18-09 davao **4.0** odgovoru „nisam pronašao odgovor u kontekstu" na pitanju koje je
tražilo odgovor. To je bio kvar koji bi obesmislio celo poređenje, jer lošija pretraga ne proizvodi
netačan odgovor nego baš takvo odustajanje.

Pretraženo je svih 237 ocenjenih odgovora: **6 odustajanja na pitanjima sa
`expected_behavior=answer`.**

```
ocene: 1.0 ×3,  2.0 ×3      prosek 1.50
```

Pod starom rubrikom isti obrazac je nosio 4.0. Popravka je, dakle, potvrđena na punom runu, a ne
samo na 9 probnih odgovora.

---

## Neuspela parsiranja: 3 od 240 (1.25%)

Sva tri imaju isti uzrok — sudija napiše obrazloženje i **nikad ne stigne do reda `OCENA:`**:

| run | pitanje | greška |
|---|---|---|
| `c101` | `REAL_024` | nije vratio broj |
| `c103` | `REAL_048` | **udario u granicu tokena** |
| `c103` | `REAL_050` | nije vratio broj |

Kod ih ne izmišlja — `parse_score` odbija i upisuje grešku umesto ocene, pa se neocenjen odgovor ne
provlači kao nula. To je ispravno ponašanje, ali znači da se odgovor gubi iz proseka.

**Popravka pre velikog prolaza:** dići `max_tokens` u `judge_profile.json` sa 300 na ~500.
Obrazloženje je ograničeno na „najviše dve rečenice", ali sudija to povremeno prekorači i ostane bez
prostora za samu ocenu. Na 1.200 odgovora 1.25% je ~15 neocenjenih.

Izmena menja `prompt_sha256`? **Ne** — `max_tokens` nije deo prompta, pa heš ostaje isti i već
ocenjeni runovi ostaju uporedivi. To je jeftina popravka.

---

## Glavni nalaz: efekat je pao na kontaminiranu osu

| poređenje | šta se menja | razlika |
|---|---|---|
| `c101` → `c103` | chunking (MiniLM, **ista mašina**) | **+0.07** |
| `c105` → `c107` | chunking (bge-m3, **ista mašina**) | **+0.07** |
| `c101` → `c105` | embedding (**različita mašina**) | **+0.54** |
| `c103` → `c107` | embedding (**različita mašina**) | **+0.54** |

Hijerarhijski chunking daje `+0.07`, i to dvaput isto, na oba embedinga. To je **čisto poređenje** —
obe konfiguracije u svakom paru su sa iste mašine.

Embedding naizgled daje `+0.54`, takođe dvaput isto. **Ali `c101`/`c103` su prikupljeni na serveru,
a `c105`/`c107` na Macu.** Efekat osam puta veći od efekta chunkovanja pao je tačno na jedinu osu
koja je pomešana sa mašinom.

### Zašto to nije paranoja

Kontrolni run `c101ctrl` (ista konfiguracija kao `c101`, ali sa Maca) već je pokazao da Mac daje
**viši ROUGE** od servera — 0.1735 naprema rasponu 0.1460–0.1602 sa servera. Sada Mac konfiguracije
daju i **više ocene sudije**. Dva nezavisna merenja pokazuju isti smer.

To **ne dokazuje** da je `+0.54` uticaj mašine. Dokazuje da se iz postojećih podataka
**ne može razlikovati** uticaj embedinga od uticaja mašine.

### Test koji to razrešava, i zašto nije pokrenut

Oceniti `c101ctrl` istim sudijom i uporediti:

- ocena **~2.41** (kao `c101` sa servera) → mašina ne utiče, `+0.54` je zaista embedding
- ocena **~2.95** (kao `c105` sa Maca) → ceo `+0.54` je mašina, poređenje embedinga pada

Jedan run, 60 odgovora, ~65 min. Nijedan drugi test ne daje ovaj odgovor.

**Predloženo 21-09, korisnik odlučio da se ne pokreće.** Zabeleženo ovde da odluka bude vidljiva, a
ne da se izgubi: dok se ovo ne izmeri, **razlika između MiniLM-a i bge-m3 ne sme se prijaviti kao
rezultat embedinga.**

Poređenje po osi **chunkovanja** je netaknuto i može se koristiti.

---

## Šta ovi brojevi još ne znače

**Jedno ponavljanje po konfiguraciji.** Ocenjen je samo `r01` iz svake. Varijansa između ponavljanja
nije poznata, pa se ne zna da li je `+0.07` iznad šuma. Za `c101` postoji pet prikupljenih runova —
ocenjivanje još dva dalo bi tu meru.

**Nema poređenja sa ljudskom ocenom.** Sudija koji sledi kriterijume nije isto što i sudija koji je
u pravu. `judge_profile.json` to i traži: *„verify human agreement before freezing paper results."*
Bez ručne provere uzorka od ~20 odgovora, ocene se ne smeju zamrznuti za rad.

**Ocena 3 je retka** — 2, 1, 1 i 2 pojavljivanja po runu, dok su 0, 2, 4 i 5 česte. Sudija
polarizuje. Nije nužno kvar (rubrika opisuje 3 kao usku kategoriju), ali vredi proveriti pri ručnom
poređenju.

**Prosek po očekivanom ponašanju** pokazuje da `abstain` (3.08) i `clarify` (3.25) prolaze bolje od
`answer` (2.70). Verovatno zato što je lakše ispuniti „reci da nema podatka" nego izneti tražene
činjenice — ali n je 12 odnosno 4, premalo za zaključak.

---

## Šta ostaje

### Traži odluku

1. **Kontaminirana osa embedinga.** Razrešava se ocenjivanjem `c101ctrl` (~65 min). Dok se ne
   uradi, u radu se prijavljuje kao ograničenje, a razlika MiniLM/bge-m3 se ne tumači.
2. **Preostalih 16 runova** — ~17.5 h na serveru u ovom stanju. Ima smisla tek posle popravke
   `max_tokens` i odluke o tački 1.

### Posao bez odluke

3. **`max_tokens` 300 → ~500** u `judge_profile.json`. Ne menja `prompt_sha256`, pa ne obezvređuje
   već ocenjene runove.
4. **Ručna provera slaganja** na ~20 odgovora.
5. **`known_issue`:** `JUDGE_SYSTEM` još sadrži red „Vrati tačno jedan broj … bez objašnjenja", koji
   protivreči novom promptu. Merenje je izvršeno sa njim, pa je namerno ostavljen; čistiti uz
   ponovno ocenjivanje.
6. **Skripta za ocenjivanje** je ad-hoc, u scratchpad-u. Ako se ide na preostalih 16 runova, vredi
   je uneti kao `scripts/score_matrix.sh`.
7. **Drugi generator** — `c102`, `c104`, `c106`, `c108` ne postoje.

---

## Kako proveriti ove brojeve

```bash
venv/bin/python - <<'PY'
import json, glob, collections, statistics
for run in ('c101','c103','c105','c107'):
    f = sorted(glob.glob(f'benchmarking/runs/dev_combined_{run}_r01/scores/*llm_judge*.json'))
    res = json.load(open(f[-1]))['results']
    sc = [(r['scores'].get('llm_judge') or {}).get('score') for r in res]
    ok = [s for s in sc if s is not None]
    print(run, f'{len(ok)}/{len(sc)}', round(statistics.mean(ok), 2),
          dict(sorted(collections.Counter(ok).items())))
PY
```

Obrazloženja sudije čuvaju se uz svaku ocenu u `samples[0].raw_response`, pa se svaka pojedinačna
ocena može pročitati i osporiti.
