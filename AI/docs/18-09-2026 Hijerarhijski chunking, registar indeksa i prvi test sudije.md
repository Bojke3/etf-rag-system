# 18-09-2026 — Hijerarhijski chunking, registar indeksa i prvi test sudije

Grana: **`hierarchical-benchmark`** (5 commita, **pushovano** na `origin`).
PR nije otvoren: https://github.com/Bojke3/etf-rag-system/pull/new/hierarchical-benchmark

---

## Trenutno stanje

Sva četiri indeksa za matricu 2×2 postoje i verifikovana su. Hijerarhijski chunking radi kroz
benchmark kolektor, što ranije nije bilo moguće. Ponavljanje runova (`--repeat-from`) je
popravljeno — bilo je polomljeno za **svaki** postojeći run na macOS-u.

Ništa još nije prikupljeno po novom protokolu. Ocenjen je jedan probni run da se vidi kako se
sudija ponaša.

---

## Šta je urađeno

### 1. Čišćenje repoa
- `data - Copy/` (205 fajlova) — bajt-identičan duplikat `data/chunks_v1_c1024_o150`, obrisan.
- `models - Copy/vectorstore/` — **nije bio smeće**: jedini verzionisani primerak baseline indeksa
  nad kojim su izvršena svih 5 c001 runova. Preimenovan u `models/vectorstore_c001_c1024_o150`.
- Lokalni `models/vectorstore/` obrisan — bio je iz **drugog OCR prolaza** (samo 77/205 chunkova
  se poklapalo sa `chunks_v1`), nijedan run ga nije koristio.

### 2. Registar indeksa (`models/registry.json` + `src/embedding/registry.py`)
`vector_store_path` i `embedding_model` su bile nezavisne vrednosti. Provera dimenzije hvata
bge-m3 (1024) protiv MiniLM (384), ali `all-MiniLM-L6-v2` i `paraphrase-multilingual-MiniLM-L12-v2`
su **oba 384-dimenziona** — učitavaju tuđi indeks bez greške i vraćaju tiho pogrešne susede.
Stari `.env` je bio podešen tačno tako.

Sada `verify_pairing()` odbija nespojiv par pre čitanja vektora. Pozvano iz
`scripts/benchmark_execution.py` i `web/app.py`. Indeks koji nije u registru se propušta uz
upozorenje, pa ad-hoc indeksi rade.

### 3. Hijerarhijski chunking kroz kolektor
Tri odvojene prepreke:

1. `stages.chunk_documents` piše jedan `.txt` po chunku — nema gde da smesti `parent_chunk_id`,
   `level` ni `page`. Dodat **`chunk_snapshot_with_strategy`** koji nad istim zamrznutim tekstom
   pušta bilo koju strategiju i piše `chunks.jsonl`.
2. `process_documents.py` je **tiho ispuštao `--strategy`** kad je ulaz extraction snapshot —
   `--strategy hierarchical` je vraćao flat chunkove bez upozorenja. Popravljeno; flat i dalje ide
   starim `.txt` putem da ostane bajt-identičan `chunks_v1`.
3. `benchmark_execution.py` je odbijao sve osim flat. Sada bira artefakte po strategiji i vezuje
   `ParentAwareRetriever`. **Odbija da padne na legacy flat indeks** kad je tražena strategija
   hijerarhijska — inače bi dobio kompletan, ubedljiv run koji meri flat pod hijerarhijskom etiketom.

Takođe: `index_documents.detect_mode` je gledao samo postojanje manifesta, sada gleda sadržaj
(`chunks` vs `chunks_file`). `index_documents` u strategijskom modu sada piše manifest indeksa.

### 4. Ponavljanje runova popravljeno
`--repeat-from` i `--verify-run` su pucali za **svaki** postojeći run na ovoj mašini. Uzrok:
provenance heširа sirove bajtove, a deo heševa je snimljen na Windowsu iz CRLF radnog stabla dok
su blobovi u gitu LF. `benchmark.json` se nikad nije mogao poklopiti.

- `.gitattributes` normalizuje tekst na LF da novi zapisi ne odlutaju isto.
- `match_kind()` prihvata poklapanje nađeno posle popravke preloma reda i **prijavljuje ga** kao
  izuzetak (`input_match_exceptions`), umesto da padne ili ćuti.
- `validate_inputs` razrešava preimenovan direktorijum indeksa tako što u registru traži fajl
  **čiji se heš poklapa** sa zabeleženim. Fajl drugačijih bajtova i dalje pada. Sirovi zapisi
  runova se **ne prepisuju**.

Dva skrivena baga u ponavljanju hijerarhijskih runova:
- `apply_repeat_settings` je hardkodirao `chunk_strategy='flat_baseline'` — ponavljanje
  hijerarhijskog runa bi prikupljalo flat rezultate pod hijerarhijskom etiketom.
- `verify_saved_inputs` nije znao za roditeljske pasuse (namerno nisu u ugrađenim metapodacima),
  pa bi svaki hijerarhijski run prijavio "izmenjen indeksirani tekst".

### 5. Izgrađeni indeksi c003 i c004

| | flat | hijerarhijski |
|---|---|---|
| **MiniLM** | c001 | **c003** (novo) |
| **bge-m3** | c002 | **c004** (novo) |

Oba hijerarhijska: 51 roditelj, 176 dece, 0 siročadi, 167/176 dece ima `Član N.`, sva imaju stranu.
Iz **istog zamrznutog snapshota** `data/extracted_v1` — bez ijednog OCR poziva, za 40 ms.
c003 i c004 imaju **bajt-identične** `metadatas` i `parents` fajlove; razlikuju se samo vektori,
što dokazuje da je chunkovanje konstantno duž embedding ose.

---

## Šta je testirano

- **75/75 testova prolazi** (bilo 70; dodata 3 nova + 2 za strategijsko chunkovanje).
- `python -m src.embedding.registry` → 4 konfiguracije, 0 problema.
- `--verify-run baseline_context8k` → svih 60 pitanja, svež retrieval reprodukuje sačuvani,
  heš indeksa `b3e799a8` se poklapa.
- End-to-end hijerarhijski retrieval kroz kolektorov kod: `ParentAwareRetriever`,
  `effective_strategy: hierarchical`, deca od ~400 znakova zamenjena roditeljima 2300–4300.
- Flat put nepromenjen (regresija): isti skor 0.697, ista imena fajlova.
- c003 rebuild reprodukovao sva tri heša identično — build je determinističan.

---

## Merenja koja menjaju plan

### Budžet konteksta
Hijerarhijski na `top_k=5`, preko svih 60 pitanja: medijana 18.056 znakova, **maksimum 20.908**.
Flat na `top_k=5`: maksimum 5.128, **nikad nije odsecan**.

| budžet | odseca |
|---|---|
| 8.000 (dosadašnji) | 11 od 60 pitanja, baca 2.1 od 5 pasusa |
| 20.000 | i dalje 11 od 60 |
| **21.000** | **0** |

Odabrano: **22.000 znakova, `num_ctx=16384`**. Mereno 2.44 znaka po tokenu (ne 3.5 kako piše u
komentarima configa), pa je to ~9.016 tokena konteksta + prompt + 2.048 za odgovor ≈ 11.164,
uz ~5.200 tokena rezerve.

### Hardver servera (`rticuda.etf.bg.ac.rs`) — ranije nigde zabeleženo
**RTX 3080 Ti, 12 GB VRAM. i7-11700K (8 jezgara/16 niti). 125 GB RAM.**

| model | veličina | prompt | generisanje | gde |
|---|---|---|---|---|
| `mistral:latest` | 4.4 GB | 921 tok/s | **162 tok/s** | GPU (stane cela) |
| `llama4:latest` | 67 GB | 37.8 tok/s | 4.06 tok/s | 85%/15% CPU/GPU |
| `mistral-large` | 73 GB | 2.4 tok/s | **0.57 tok/s** | CPU |

`ollama ps` potvrđuje: llama4 je `85%/15% CPU/GPU`. Brzina mistral-large se poklapa sa
propusnošću DDR4 (≈42 GB/s ÷ 73 GB = 0.58 tok/s, izmereno 0.57).

**Posledica: mistral-large nije upotrebljiv** — ~72 h po runu, 15 dana za 5 ponavljanja.
Predloženo `mistral:latest` + `qwen3.5:latest` (6.6 GB, oba na GPU) → ~12 min po runu.

### Lokalna mašina (nije do kraja izmereno)
Mac je **Apple M5, 24 GB**, ollama 0.24.0 instaliran, sa `mistral:latest` (ID `6577803aa9a0`,
**identičan serverovom**) i `qwen3.5:9b` (ID `6488c96fa5fa`, identičan serverovom
`qwen3.5:latest`). Merenje brzine lokalno je **prekinuto i nije izvršeno** — to je otvoreno
pitanje, vidi Sledeće korake.

---

## Prvi test sudije

Ocenjen `dev_base_c001_r05` (60 odgovora koje je dao `mistral:latest`, sudija llama4 preko SSH).
Trajanje ~19 min, ~16 s po odgovoru → svih 2400 odgovora ≈ 11 sati.

**Prosek: 3.12/5.** Raspodela: `0.0`→9, `2.0`→6, `3.0`→4, `4.0`→40, greška→1. **Nema 1.0 ni 5.0.**

**Radi:** REAL_001 (odgovor tvrdi 42 umesto 55) dobio **0.0**. Prompt potvrđuje da kriterijumi
(`Obavezne činjenice`, `Tvrdnje koje treba izbeći`) **stižu** do sudije — septembarski problem sa
praznim kriterijumima više ne postoji.

**Ne radi:** nagrađuje odustajanje. REAL_002 je pitanje na koje je trebalo odgovoriti, sa dve
tražene činjenice; sistem je rekao *"nisam pronašao odgovor u kontekstu"* i dobio **4.0**.
Takvih slučajeva **2, oba 4.0** (mali uzorak, ali dosledan).

To je opasno baš za ovo istraživanje: lošija pretraga ne daje pogrešan odgovor nego
*"nema u kontekstu"*. Ako to vredi 4.0, poređenje konfiguracija gubi smisao.

Uzrok: rubrika u `src/evaluation/llm_judge.py` kaže sudiji da **prizna** opravdano uzdržavanje,
ali nigde ne kaže da je odustajanje **promašaj** kada se odgovor očekivao. `expected_behavior` mu
se već šalje, samo ga ne koristi u tom smeru.

Sitnica: `required_facts` se u fajlu sa ocenama prikazuje kao `None` iako je poslat — greška u
prepisivanju u izveštaj, ne utiče na ocenjivanje.

---

## Izmenjeni fajlovi

| Fajl | Šta |
|---|---|
| `models/registry.json`, `models/README.md` | registar 4 indeksa, heševi, poznati problemi |
| `src/embedding/registry.py` | **nov** — `verify_pairing`, `resolve`, `audit` |
| `src/data/stages.py` | **nov** `chunk_snapshot_with_strategy` |
| `scripts/process_documents.py` | strategija se više ne ispušta na snapshotu |
| `scripts/benchmark_execution.py` | strategijski artefakti + `ParentAwareRetriever` |
| `scripts/benchmark_provenance.py` | `match_kind`, `relocated_index_file`, `recorded_strategy`, `recorded_index` |
| `scripts/index_documents.py` | `detect_mode` po sadržaju manifesta; manifest u strategijskom modu |
| `.gitattributes` | **nov** — LF svuda |
| `docs/TELFOR_RUN_MATRIX.md` | **nov** — 8 konfiguracija, tačne komande |
| `docs/BENCHMARK_RUN_REGISTER.md` | dopuna o chunking osi i budžetu |
| `.env`, `.env.example` | ispravan par enkoder/indeks; SSH bez tajni |

---

## Dogovoreni plan testiranja

Pun opis sa komandama: **`docs/TELFOR_RUN_MATRIX.md`**. Ovde je suština i, važnije, **zašto** je
tako odlučeno — da se sledeća sesija ne vraća na iste rasprave.

### Šta se menja, šta stoji

Tri ose po dve vrednosti → **8 konfiguracija × 5 ponavljanja = 40 runova**, 2400 generisanja.

| Osa | A | B |
|---|---|---|
| embedding | `all-MiniLM-L6-v2` | `BAAI/bge-m3` |
| chunkovanje | `flat_baseline` | `hierarchical` |
| generator | `mistral:latest` | **nije odlučeno** (vidi otvorena pitanja) |

Nepromenjeno u svim granama: istih 60 pitanja (`finalna_pitanja.json`), `top_k=5`,
budžet konteksta 22.000 znakova, `num_ctx=16384`, temperatura 0.7 / top_p 0.9, `zero_shot` prompt,
5 ponavljanja.

Oznake runova: `dev_combined_c101_r01` … `c108_r05`. Indeksi zadržavaju oznake `c001`–`c004` iz
`models/registry.json`; runovi koriste poseban opseg `c1xx` da se dve stvari ne mešaju.

### Odluke i razlozi

**Sve se prikuplja iznova.** Postojećih 10 runova se ne koristi kao grana matrice. Odluka
korisnika: "nek budu tu i višak, uzećemo šta nam treba". Time otpada rasprava da li se run na
`num_ctx=8192` sme porediti sa runom na 16384. Stari runovi ostaju kao zasebno, validno poređenje
embedinga na starom budžetu.

**`top_k=5` za obe strategije, budžet dovoljan da se ništa ne odseca.** Ovo je predlog korisnika i
bolji je od prvobitnog predloga da se izjednači `top_k` (8 za flat, 2 za hijerarhijski), zbog
asimetrije ishoda:

- Ako **flat pobedi** — zaključak je gotov i jači nego iz izjednačenog poređenja, jer je flat
  pobedio uprkos tome što je dobio ~3,5 puta manje teksta (5.100 naspram 17.300 znakova).
- Ako **hijerarhijski pobedi** — tek tada treba kontrolna grana: flat sa većim `top_k`, da se
  odvoji "bolje sečenje" od "više teksta".

Dodatni runovi se plaćaju **samo ako ih rezultat zatraži**. Odbačena je varijanta `top_k=20` za
flat kao kontrola — to nije čista kontrola nego druga vrsta hendikepa (15 nebitnih pasusa unosi
šum, pa se ne zna da li flat pada zbog sečenja ili zbog šuma).

**Posledica koju treba prijaviti u radu:** na istom `top_k` dve strategije isporučuju bitno
različitu količinu teksta. To je svojstvo strategije, ne greška postavke, ali mora u tabelu
rezultata zajedno sa brojem isporučenih pasusa (kolektor ga snima po pitanju u `diagnostics`).

Formulacija za rad: *"Za obe strategije `top_k=5`, uz budžet konteksta postavljen tako da nijedna
nije odsecana; svaka isporučuje svojih pet najboljih pasusa u celini."*

**Budžet 22.000, ne 20.000** — mereno, ne procenjeno: hijerarhijski maksimum je 20.908 znakova, a
na budžetu 20.000 i dalje se odseca 11 od 60 pitanja. Na 21.000 nijedno. Uzeto 22.000 sa rezervom.

**`num_ctx=16384`** — 22.000 znakova je ~9.016 tokena pri izmerenih **2.44 znaka po tokenu**
(komentari u configu tvrde 3.5, što je pogrešno za srpski sa mistralovim tokenizerom). Plus prompt
i 2.048 za odgovor ≈ 11.164 tokena, ostaje ~5.200 rezerve. Na starom `num_ctx=8192` prompt se ne
bi uklopio i **Ollama bi ga tiho odsekla na serveru**, što je gore od kontrolisanog odsecanja.

**Sudija je jedan i fiksan, ne unakrsan.** Razmatrano je da svaki generator ocenjuje onaj drugi.
Odbačeno: tada svaki generator dobija **drugog sudiju**, pa se ne može razlikovati "bolji
generator" od "blaži ocenjivač" — sudija postaje promenljiva baš na osi koja se meri. Ostaje
`llama4:latest` rezervisan samo za ocenjivanje. Kod to i štiti: `judge_execution.py:42` odbija da
oceni run čiji je generator iste porodice kao sudija, pa llama4 ne može istovremeno biti generator
i sudija.

**Redosled izvršavanja:** prvo prikupiti **sve** runove, pa tek onda oceniti sve odjednom. Svako
prebacivanje između generatora i sudije košta ~30 s učitavanja modela od 67 GB.

### Procena vremena

| faza | trajanje |
|---|---|
| jedan run, generator na GPU | ~12 min |
| 40 runova | ~8 h |
| ocenjivanje svih 2400 odgovora (llama4, ~16 s/odgovor) | ~11 h |

---

## Šta ostaje za sledeću sesiju

### Otvorena pitanja — traže odluku pre pokretanja

1. **Drugi generator nije izabran.** Korisnik je tražio `mistral-large`; merenja pokazuju da na
   ovom serveru daje 0.57 tok/s → ~72 h po runu, 15 dana za 5 ponavljanja. Korisnik je taj nalaz
   dva puta osporio, pa je dogovoreno da se izmeri **jedno pravo pitanje** — to merenje
   **nije izvršeno** (prekinuto). Dok se ne izvrši, osa generatora je otvorena.
   Predlog koji stoji: `qwen3.5:latest` (6.6 GB, staje na GPU, druga porodica od mistrala, već je
   na listi kandidata u run registru). Šta god da se izabere, treba zabeležiti i digest.

2. **Gde se generiše — lokalno ili na serveru.** Mac ima `mistral:latest` i `qwen3.5:9b` sa
   **identičnim ID-evima** kao server. Ako M5 bude uporediv po brzini, generisanje može lokalno,
   bez SSH tunela i bez zavisnosti od Andrijinog naloga. llama4 sudija svakako mora na server —
   67 GB ne staje u 24 GB. Merenje nije urađeno.
   *Zabeleženo pre merenja, da se posle ne pametuje:* očekivanje je da M5 bude uporediv ili brži
   za `mistral:latest`, jer model staje i na jednom i na drugom mestu.

3. **Rubrika sudije.** Dopuniti da odustajanje kada je `expected_behavior="answer"` nije 4.0.
   **Sada je pravi trenutak** — ocenjen je tačno jedan run. Izmena menja `prompt_sha256`, pa traži
   ponovno ocenjivanje svega; posle 40 runova to je 11 sati.

### Posao koji ne traži odluku

4. **Prikupljanje 40 runova** po `docs/TELFOR_RUN_MATRIX.md`. Commit posle svake konfiguracije
   (8 commita, ne 40), da pad na 30. runu ne odnese ništa.
5. **Skripta za zbirnu tabelu** — prosek i standardna devijacija po konfiguraciji, spremno za
   LaTeX. Ne postoji. Ima smisla tek kad se vidi kakve ocene izlaze.
6. **PR za `hierarchical-benchmark`** i merge u `main`. Grana je pushovana, PR nije otvoren.
7. **Sitnica:** `required_facts` se u fajlu sa ocenama prikazuje kao `None` iako je poslat sudiji.
   Greška u prepisivanju u izveštaj, ne utiče na ocene, ali zbunjuje pri čitanju.

### Preporučeni redosled

1. Izmeriti jedno pitanje lokalno i na serveru → zatvara pitanja 1 i 2.
2. Dopuniti rubriku sudije, pa **ponovo oceniti `dev_base_c001_r05`** i uporediti jedan-na-jedan:
   REAL_002 mora da padne, REAL_001 (0.0) i REAL_004 (4.0) moraju da ostanu gde jesu.
3. Potvrditi drugi generator i njegov digest.
4. Otvoriti PR i umergovati u `main` pre prikupljanja, da runovi budu vezani za stabilan kod.
5. Pokrenuti matricu, pa oceniti sve odjednom.

## Kako nastaviti

```bash
venv/bin/python -m pytest tests -q                      # 75 testova
venv/bin/python -m src.embedding.registry               # 4 konfiguracije, 0 problema
venv/bin/python scripts/benchmark_provenance.py --verify-run benchmarking/runs/baseline_context8k
```

Konfiguracija se zadaje **env promenljivama u samoj komandi** — one pobeđuju `.env`, pa nema
rizika da run bude označen kao jedno a pokrenut kao drugo:

```bash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 \
VECTOR_STORE_PATH=./models/vectorstore_c003_hier \
CHUNK_STRATEGY=hierarchical \
venv/bin/python scripts/collect_benchmark_answers.py --execution ssh --model mistral:latest \
    --top-k 5 --context-max-chars 22000 --num-ctx 16384 --run-id dev_combined_c103_r01 --label c103
```

SSH ključ je postavljen (`andrijat@rticuda.etf.bg.ac.rs`, ed25519). Lozinka nije nigde sačuvana.
Nalog je Andrijin i deljen — vredi tražiti zaseban nalog.
