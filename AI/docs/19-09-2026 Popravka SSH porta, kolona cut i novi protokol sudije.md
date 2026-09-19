# 19-09-2026 — Popravka SSH porta, kolona `cut` i novi protokol sudije

Grana: **`hierarchical-benchmark`**, 3 commita, **nije pushovano**. Nastavak na
[`19-09-2026 Prikupljanje korak 1 - 12 od 20 runova, pad servera.md`](19-09-2026%20Prikupljanje%20korak%201%20-%2012%20od%2020%20runova,%20pad%20servera.md).

---

## Trenutno stanje

Prikupljanje **nije pomereno**: i dalje 12 od 20 runova koraka 1, ista ona koja su bila jutros.
Ova sesija nije prikupljala nego je otklonila dva uzroka kvara i jedan kvar u ocenjivanju koji bi,
da je ostao, obesmislio celo poređenje konfiguracija.

Ništa ne radi u pozadini. Radno stablo je čisto, **76/76 testova prolazi** (bilo 75).

---

## Šta je urađeno

### 1. Pad runova zbog SSH porta — pronađen pravi uzrok

Jučerašnja popravka (`a4af919`, čekanje na oslobađanje porta) **nije rešila problem**, samo ga je
sakrila. Pravi uzrok je u `src/llm/ssh_tunnel.py`: proba pre otvaranja tunela radi `bind()` **bez
`SO_REUSEADDR`**, pa pada i kad port drži samo `TIME_WAIT` od HTTP konekcija prethodnog runa.
Nijedan proces tada ne drži port, a `lsof -sTCP:LISTEN` — koji `run_matrix_step1.sh` koristi — to
ne može da vidi, pa vrati „slobodno" i run svejedno padne.

Dokaz iz logova: `c105_r03` završio u 01:35:12, `c105_r04` pao u 01:35:27 i 01:35:43 (oba unutar
30 s), `c105_r05` startovao u 01:36:04 i **prošao**. `net.inet.tcp.msl = 15000`, dakle `TIME_WAIT`
traje 30 s. Isto je oborilo 17 runova u 3 sekunde u 22:26.

**Popravljeno:** `SO_REUSEADDR` se postavlja **samo na POSIX-u**. Na Windowsu ostaje
`SO_EXCLUSIVEADDRUSE`, jer bi tamo `SO_REUSEADDR` dozvolio vezivanje preko živog listenera —
upravo ono što proba sprečava.

Provereno na samoj klasi `SSHTunnel`:

| stanje porta 11435 | ponašanje |
|---|---|
| `TIME_WAIT` od prethodnog runa | proba prolazi, ide na ssh |
| živ listener | proba odbija: `Local port ... already in use` |

`wait_for_free_port` u `run_matrix_step1.sh` **nije menjan** — provera živog listenera je i dalje
ispravna, samo više nije jedina odbrana.

### 2. Kolona `cut` u registru runova

`benchmarking/runs/README.md` proglašava `done_reason` kapijom kvaliteta, ali
`scripts/build_run_index.py` ga uopšte nije čitao. `INDEX.md` je za `dev_combined_c101_r03` pisao
`60/60, Errors 0, Truncated 0` — a u tom runu je `REAL_008` presečen na `num_predict=2048` i stoji
nedovršen usred reči.

`truncated` pokriva **ulaz** (da li je kontekst stao), `cut` pokriva **izlaz** (da li je odgovor
stigao do kraja). Runovi koji nisu beležili `done_reason` daju `None` i **ne** računaju se —
nepoznato nije isto što i presečeno.

Presečeni odgovori u celom repou, sada vidljivi u `INDEX.md`:

| run | pitanje |
|---|---|
| `dev_combined_c101_r03` | `REAL_008` — **jedini u aktuelnoj matrici** |
| `baseline_context8k` | `REAL_002` |
| `dev_base_c001_r02` | `REAL_051` |

### 3. Sudija — kvar nije bio u rubrici nego u protokolu

Polazni problem iz zapisa 18-09: odustajanje je nagrađivano. Na pitanje sa
`expected_behavior=answer` odgovor *„nisam pronašao odgovor u kontekstu"* dobijao je **4.0**.

**Dopuna rubrike nije pomogla.** Isprobane četiri formulacije nad `REAL_002`, uključujući potpuno
doslovnu („ako nije iznesena nijedna obavezna činjenica, ocena je 0"):

| formulacija | `REAL_002` | `REAL_004` | `REAL_001` |
|---|---|---|---|
| A trenutna (revizija 2) | 4.0 | 4.0 | 0.0 |
| B tvrda direktiva | 4.0 | 4.0 | 0.0 |
| C izmenjena skala `0 =` | 4.0 | 4.0 | 0.0 |
| D oboje | greška (nije vratio broj) | 4.0 | 0.0 |

**Pravi uzrok.** Uz zahtev za golim brojem i `max_tokens=32`, ocena **uopšte nije zavisila od
kriterijuma** koje šaljemo. Nad istim odgovorom:

| šta je promenjeno u zapisu | ocena |
|---|---|
| ništa (`expected_behavior = answer`) | 4.0 |
| `expected_behavior` obrnut na `abstain` | 4.0 |
| obavezne činjenice **potpuno uklonjene** | 4.0 |

Isti model, isti odgovor, ali sa prostorom da obrazloži:

> „Odgovor sistema nije izneo obavezne činjenice… Očekivano ponašanje bilo je da se odgovori na
> pitanje na osnovu dostupnih dokaza, što nije učinjeno. **OCENA: 1**"

Model ume da uradi posao; u režimu golog broja ga prosto ne radi.

**Izmena:** `JUDGE_PROMPT` traži kratko obrazloženje pa red `OCENA: <broj>`. Nova `parse_score()`
čita poslednji takav red, a i dalje prihvata go broj da bi ocene snimljene starim protokolom
ostale čitljive. Profil ide na **reviziju 3**: `max_tokens` 32 → 300, nov `prompt_sha256`, stari
sačuvan u `supersedes_prompt_sha256`.

Obrazloženja se čuvaju u `raw_response` uz svaku ocenu — korisno za rad, jer se može pokazati
*zašto* je nešto dobilo ocenu.

---

## Šta je testirano

- **76/76 testova prolazi** (dodat `test_judge_reads_the_verdict_line_after_its_reasoning`).
- `parse_score` prihvata `OCENA: 1`, obrazloženje + `OCENA: 5`, go broj `0` i ` 4.5 `;
  odbija `OCENA: 9`, `Score: 4`, `10`, `5.9`, prazan odgovor i obrazloženje bez ocene.
- Proba tunela provereno na klasi: `TIME_WAIT` prolazi, živ listener odbija.
- **Novi protokol sudije, uzorak preko celog raspona starih ocena** (9 odgovora iz
  `dev_base_c001_r05`, pravi llama4 preko SSH):

| pitanje | stara | nova |
|---|---|---|
| `REAL_002` | 4.0 | **1.0** |
| `REAL_008` | 3.0 | 1.0 |
| `REAL_037` | 3.0 | 2.0 |
| `REAL_005` | 2.0 | 0.0 |
| `REAL_022` | 2.0 | 2.0 |
| `REAL_003` | 0.0 | 0.0 |
| `REAL_001` | 0.0 | 1.0 |
| **`REAL_004`** | 4.0 | **5.0** |
| `REAL_028` | greška | 5.0 |

  Presudan je `REAL_004`: dobar odgovor je otišao **gore**. Da je rubrika prosto stroža, i on bi
  pao. Stara raspodela je imala 40 od 60 odgovora zalepljenih na tačno 4.0.

- **Integraciona provera kroz pravi kod** (`LLMJudgeMetric` + `judge_profile.json` + server, bez
  oglednih skripti): `REAL_002` → 1.0, `REAL_004` → 5.0, obrazloženja sačuvana, bez grešaka.

---

## Izmenjeni fajlovi

| Fajl | Šta |
|---|---|
| `src/llm/ssh_tunnel.py` | `SO_REUSEADDR` na POSIX-u; Windows grana nepromenjena |
| `scripts/build_run_index.py` | kolona `cut` (`done_reason != stop`) + objašnjenje u zaglavlju |
| `benchmarking/runs/INDEX.md` | regenerisan, sa kolonom `cut` |
| `src/evaluation/llm_judge.py` | nov `JUDGE_PROMPT`, `parse_score()`, rubrika dopunjena očekivanim ponašanjem |
| `benchmarking/judge_profile.json` | revizija 3, `max_tokens` 300, nov heš, `known_issue` |
| `tests/test_diagnostic_evaluation.py` | nov test za čitanje reda sa ocenom |
| `AI/docs/11-09-2026session.md` | preimenovan iz `9-11-2026session.md` (sadržaj nepromenjen) |

Commiti: `3b4ebc3`, `266f73f`, `6c5de1b`.

---

## Merenja koja menjaju plan

### Serverova grafička je otpala i to nije tuđe opterećenje

Provereno više puta tokom dana, poslednji put u 16:03 UTC:

```
nvidia-smi: Unable to determine the device handle for GPU0: 0000:03:00.0: Unknown Error
            No devices were found
load average: 0.40    (mašina prazna, nijedan model učitan)
```

Jutrošnji zapis je ostavio otvorenim da li je uzrok GPU ili tuđe opterećenje. **Sada je zatvoreno:**
opterećenje je 0.40, a brzina je i dalje 20× niža. Uzrok je isključivo grafička. Poruka navodi PCI
adresu, dakle kartica je na magistrali ali drajver ne uspostavlja vezu — traži restart ili ponovno
učitavanje `nvidia` modula, dakle root, dakle Andrija ili administrator.

| | `mistral:latest` |
|---|---|
| server na GPU (18-09) | 162 tok/s |
| server sada, CPU | **7.8 tok/s** |

### Mac je brži od servera dok je ovako

Mereno **pravim promptovima iz postojećih runova**, ne sintetičkim:

| | prompt | generisanje | ukupno po pitanju |
|---|---|---|---|
| flat (2.650 tok) | 235 tok/s | 25.0 tok/s | **~35 s** |
| hijerarhijski (7.827 tok) | 224 tok/s | 22.2 tok/s | **~67 s** |

Preostalih 8 runova: **~7 h lokalno** prema **~22 h na serveru** u ovom stanju. Digest modela je
identičan (`6577803aa9a0`), a `run_config.json` već beleži `backend.execution`, pa se razlika
mašine sama zapisuje.

### Ocenjivanje je poskupelo

~22 s → **~49 s po odgovoru**. Za svih 2400 to je red veličine 15 h → **33 h** na serveru bez
grafičke. Meriti ponovo kad dođe red na ocenjivanje.

---

## Šta ostaje

### Odluka koja blokira

1. **Gde se prikupljaju preostala 8 runova** — lokalno (~7 h) ili se čeka server. Ovo je jedino
   što stvarno stoji na putu. Runovi: `c105_r03` (ponoviti u celosti, ima 60 grešaka),
   `c105_r04` (nikad nije startovao), `c105_r05` (nastavlja se od 7. pitanja),
   `c107_r01`…`r05` (nijedan nije startovan).

### Otvoreno oko sudije

2. **Pun run nije ponovo ocenjen** — odluka korisnika da se odloži. Ne znamo novu raspodelu preko
   svih 60, ni koliko odgovora eventualno ne uspe da se isparsira. U ogledu je jedna varijanta
   jednom vratila nešto što nije broj; kod to prijavi kao grešku umesto da izmisli ocenu, ali na
   2400 odgovora i 2% znači ~50 neocenjenih.
3. **Nema poređenja sa ljudskom ocenom.** Sudija koji sledi kriterijume nije isto što i sudija
   koji je u pravu. To traži i sam `judge_profile.json` („verify human agreement before freezing
   paper results"). Za rad treba ručno oceniti uzorak od ~20 odgovora i uporediti.
4. **Stabilnost nije merena** — `temperature=0`, `seed=42`, `samples=1` bi trebalo da budu
   ponovljivi, ali to nije provereno pod promenljivim opterećenjem servera.
5. **`known_issue` u profilu:** `JUDGE_SYSTEM` još sadrži red *„Vrati tačno jedan broj od 0 do 5,
   bez objašnjenja"*, koji protivreči novom promptu. **Namerno ostavljen** — merenje revizije 3
   izvršeno je sa tim tekstom, pa bi izmena unela u repo nešto što nije izmereno. Čistiti pri
   prvom ponovnom ocenjivanju, uz ponovnu proveru na istih 9 odgovora.

### Sitnije

6. **`c101_r03` / `REAL_008`** — presečen odgovor. Dizanje `num_predict` ne dolazi u obzir usred
   matrice (taj run bi bio na drugoj postavci od ostalih 19). Odluka pri ocenjivanju: izuzeti to
   pitanje iz proseka ili ponoviti run.
7. **`run_matrix_step1.sh:86`** i dalje ispisuje `wc -l` kao „done, N answers" — ista metrika zbog
   koje je `c105_r03` jednom prijavljen kao gotov. `INDEX.md` sada govori istinu, ali poruka u toku
   serije i dalje obmanjuje.
8. **Ponovno pokretanje serije otvara tunel i za 12 gotovih runova.** Kolektor ih preskače (ne
   duplira odgovore), ali svaki i dalje podiže i ruši tunel.
9. **3 commita nisu pushovana**; PR za `hierarchical-benchmark` nije otvoren.
10. **Nema regresionog testa za `TIME_WAIT`** — zavisi od mrežnog steka mašine i ume da bude
    nestabilan, pa je svesno izostavljen.

---

## Važno za nastavak

**Vremena iz runova se ne smeju koristiti kao rezultat.** Sve posle ~23:00 18-09 mereno je na
serveru sa otpalom grafičkom. Razlika između `c101` (medijana 2.0 s) i `c105_r02` (100.5 s) je
stanje servera, ne konfiguracija. Ako brzina treba radu, meri se ponovo u jednom prolazu na jednoj
mašini.

**Prosek 3.12/5 iz probnog runa ne znači ono što je izgledalo.** Onih 40 odgovora sa ocenom 4.0
nisu je dobili zato što zadovoljavaju kriterijume — pod starim protokolom kriterijumi nisu ni
ulazili u ocenu. Dobro je što je to izašlo na probnom runu, a ne posle 40.

**Ocene iz revizije 1 nisu uporedive sa novim.** Svaki fajl u `scores/` nosi svoj `prompt_sha256`,
pa se razlikuju bez nagađanja.

---

## Kako nastaviti

```bash
# tacno stanje svih runova (broj redova NIJE broj uspeha)
venv/bin/python scripts/build_run_index.py && cat benchmarking/runs/INDEX.md

# testovi
venv/bin/python -m pytest tests -q          # 76

# stanje servera pre bilo cega
ssh andrijat@rticuda.etf.bg.ac.rs "uptime; nvidia-smi; ollama ps"

# nastavak prikupljanja na serveru — preskace gotove runove
bash scripts/run_matrix_step1.sh &
caffeinate -i -m -w $! &
```

`caffeinate` ne sprečava uspavljivanje kad se zatvori poklopac — laptop mora ostati otvoren i na
punjaču.

Za lokalno generisanje: `scripts/run_matrix_step1.sh` je pisan za `--execution ssh`. Prelazak na
lokalno traži izmenu skripte (`--execution local`) i mora se zabeležiti kao razlika u postavci,
jer bi `c105`/`c107` tada bili sa druge mašine nego `c101`/`c103`.
