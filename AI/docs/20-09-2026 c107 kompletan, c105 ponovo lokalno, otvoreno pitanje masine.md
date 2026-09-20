# 20-09-2026 — `c107` kompletan, `c105` ponovo lokalno, otvoreno pitanje mašine

Grana: **`hierarchical-benchmark`**. Nastavak na
[`19-09-2026 Popravka SSH porta, kolona cut i novi protokol sudije.md`](19-09-2026%20Popravka%20SSH%20porta,%20kolona%20cut%20i%20novi%20protokol%20sudije.md).

---

## Trenutno stanje

| konfiguracija | stanje | mašina |
|---|---|---|
| `c101` MiniLM + flat | **5/5 kompletno** | server (GPU još radio) |
| `c103` MiniLM + hijerarhijski | **5/5 kompletno** | server (GPU još radio) |
| `c105` bge-m3 + flat | **prikuplja se** | Mac |
| `c107` bge-m3 + hijerarhijski | **5/5 kompletno** | Mac |

Serverova grafička je i dalje otpala — provereno 20-09 u 21:18 UTC, opterećenje 0.09, dakle
mašina je prazna a kartica se i dalje ne prijavljuje. Zato se sve dalje prikuplja lokalno.

---

## Šta je urađeno

### `c107` prikupljen u celosti, lokalno

Pet runova, **300 od 300 odgovora uspešno, 0 grešaka, 0 odsečenih konteksta**. Nijedan run nije
morao ni na drugi pokušaj. Trajalo tri sata, ~35 s po pitanju.

Digest modela je identičan serverovom (`6577803aa9a0`), a `run_config.json` beleži
`backend.execution=local`, pa svaki run sam kaže sa koje je mašine.

**Kontekst je najtešnji od svih konfiguracija:** maksimum **21.263** znaka pri budžetu 22.000 —
737 znakova rezerve. Staje, ali bez prostora. Ako se ikad menja `top_k` ili strategija, ovo je
konfiguracija koja prva probija budžet.

**Jedan presečen odgovor**, uhvaćen kolonom `cut` dodatom juče: `c107_r04` / `REAL_049` je udario
u `num_predict=2048`. Ali nije reč o predugačkom legitimnom odgovoru — model je počeo da izmišlja
dodatna pitanja i da na njih odgovara:

> „…**Pitanje:** Da li se može koristiti stari naziv Radio komunikacije umesto novog naziva Radio
> komunikacije?"

Dakle degenerisano generisanje. Da kolona `cut` nije postojala, sudija bi to ocenio kao loš
odgovor i pripisao ga konfiguraciji `c107`.

### `c105` se prikuplja ispočetka, ceo na Macu

Runovi `c105` sa servera **premešteni su u `benchmarking/runs/_superseded_ssh/`**, nisu obrisani.
`build_run_index.py` preskače foldere čije ime počinje sa `_`, pa ne ulaze u `INDEX.md`. Premeštaj
je `git mv`, dakle potpuno reverzibilan, a sirovi zapisi nisu ni u čemu izmenjeni.

| premešten run | stanje u trenutku sklanjanja |
|---|---|
| `dev_combined_c105_r01` | 60/60 uspešno |
| `dev_combined_c105_r02` | 60/60 uspešno, ali generisan dok je serveru već otkazivala grafička (medijana 100.5 s) |
| `dev_combined_c105_r03` | 0/60 — 60 grešaka posle pada tunela |
| `dev_combined_c105_r05` | 6/60, prekinut |

Razlog: da svih pet ponavljanja jedne konfiguracije budu sa **iste mašine**. Mešanje mašina unutar
jedne konfiguracije ubacilo bi razliku između mašina u raspon koji se u radu prijavljuje kao
varijansa između ponavljanja.

`r01` i `r02` ostaju validni runovi i mogu se koristiti kao zasebno, serversko poređenje.

Oznake `c101`–`c108` su sve zauzete u `docs/TELFOR_RUN_MATRIX.md` (parni brojevi rezervisani za
drugi generator), pa nije bilo slobodne oznake za „c105 sa Maca" — otuda premeštanje umesto nove
oznake.

---

## Otvoreno pitanje koje mora u rad: mašina kao neizmerena promenljiva

**Ovo je najvažnija stavka ovog izveštaja.**

Posle ovog prikupljanja matrica izgleda ovako:

| | flat | hijerarhijski |
|---|---|---|
| **MiniLM** | `c101` **server** | `c103` **server** |
| **bge-m3** | `c105` **Mac** | `c107` **Mac** |

Osa embedinga se **poklapa sa osom mašine**. Svaka razlika između MiniLM-a i bge-m3 može biti i
razlika između servera i Maca, i to se iz postojećih podataka **ne može razdvojiti**.

### Šta mašina ne dira

Pretraga se **uvek** izvršava lokalno, u oba režima; server je oduvek radio samo generisanje.
Zato su `doc-hit@5`, `MRR`, veličine konteksta i sam prompt koji odlazi modelu **identični bez
obzira na mašinu**. Ta polovina poređenja nije ugrožena.

### Šta mašina dira

Samo **tekst odgovora**. Isti model i isti digest, ali različit računski backend — Metal na Macu,
CUDA/CPU na serveru. Različita jezgra i redosled sabiranja u pokretnom zarezu daju blago drugačije
logite; gde su dva tokena bliska po verovatnoći, izbor može da se prevagne. To povlači ocene
sudije i ROUGE, dakle glavni rezultat.

Efekat je **verovatno mali** u odnosu na šum koji već postoji zbog `temperature=0.7` — ponavljanja
se ionako međusobno razlikuju. Problem nije veličina nego to što je **sistematski**, poklopljen sa
merenom osom, i **neizmeren**.

### Kako se zatvara — jedan kontrolni run

Ne treba ponavljati ništa veliko. Dovoljno je pustiti **`c101_r06` lokalno** — konfiguraciju za
koju već postoji pet runova sa servera.

- flat je brz, ~21 s po pitanju → **oko 25 minuta**
- pretraga je identična, pa je **svaka razlika isključivo generisanje**
- porede se raspodela dužina odgovora i ROUGE; radi lokalno, ne treba ni sudija ni server

Ako `r06` legne unutar raspona tih pet sa servera, u radu se piše da je uticaj mašine **izmeren i
ispod razlike između ponavljanja**. Ako ne legne, to se sazna za 25 minuta umesto posle 2400
ocenjenih odgovora.

Run se označava jasno kao **kontrola**, ne kao šesto ponavljanje matrice.

---

## Drugo otvoreno pitanje: kako se broji pogodak pretrage

Pokušano je poređenje `c103` naspram `c107`, ali izračun **ne reprodukuje brojeve iz prethodne
sesije** (`c101` 0.966 umesto 0.981, `c103` 0.898 umesto 0.942). Uzrok nije greška u računu nego
stvarna dvosmislenost u podacima:

```
referenca:   Pravilnik_o_OAS_preciscen_jun_2023.pdf
u pretrazi:  Pravilnik o osnovnim akademskim studijama    ← isti propis?
             Pravilnik_o_OAS_preciscen_jun_2023           ← ili samo ovo?
```

„OAS" i „osnovne akademske studije" su isti propis, ali **dva zasebna dokumenta u indeksu**. Da li
se dohvatanje jednog računa kao pogodak kad je referenca drugo — to je metodološka odluka koja
sama pomera `doc-hit` za 4–5 procentnih poena.

Prethodna sesija je to računala ad-hoc i **skripta nije u repou**, pa se ne može utvrditi koja je
konvencija korišćena. **Nijedan broj za pretragu se zato ne sme citirati dok se ovo ne odluči i
dok skripta ne bude commitovana.**

---

## Izmenjeni fajlovi

| Fajl | Šta |
|---|---|
| `benchmarking/runs/dev_combined_c107_r01…r05` | **novo** — 300 odgovora |
| `benchmarking/runs/_superseded_ssh/` | **novo** — serverski `c105` runovi + objašnjenje |
| `scripts/run_matrix_step1.sh` | `EXECUTION` (ssh/local), `ONLY` filter, preskakanje gotovih runova, brojanje stvarnih uspeha umesto `wc -l` |
| `benchmarking/runs/INDEX.md` | regenerisan |

Commit: `c8cfd7b`.

---

## Šta ostaje

### Traži odluku

1. **Konvencija za pogodak pretrage** (OAS naspram „osnovne akademske studije"). Dok se ne odluči,
   nema metrika pretrage.
2. **Kontrolni run `c101_r06` lokalno** — zatvara pitanje mašine za 25 minuta.

### Posao bez odluke

3. **Skripta za metrike i zbirnu tabelu** — ne postoji, a sad je jasno da nije opciona. Prosek i
   standardna devijacija po konfiguraciji, spremno za LaTeX.
4. **Ocenjivanje** — nijedan run iz matrice nije ocenjen. Sudija je na reviziji 3 (obrazloženje pa
   ocena), ali pun run još nije prošao, nema poređenja sa ljudskom ocenom i stabilnost nije merena.
   Sudija mora na server jer llama4 ima 67 GB, a serveru je otkazala grafička — procenu vremena
   treba izmeriti ponovo.
5. **`known_issue` u `judge_profile.json`** — `JUDGE_SYSTEM` još sadrži red „Vrati tačno jedan broj
   … bez objašnjenja", koji protivreči novom promptu. Namerno ostavljen jer je merenje izvršeno sa
   njim; čisti se pri prvom ponovnom ocenjivanju.
6. **`c101_r03` / `REAL_008`** — presečen odgovor iz ranije. Odluka pri ocenjivanju.
7. **PR za `hierarchical-benchmark`** nije otvoren.

---

## Važno za nastavak

**Vremena izvršavanja se ne smeju prijavljivati kao rezultat.** Runovi su prikupljeni na dve
mašine, a deo serverskih dok je grafička već otkazivala. Ako brzina treba radu, meri se ponovo u
jednom prolazu na jednoj mašini.

**Mašina mora biti prijavljena u radu**, bez obzira na ishod kontrolnog runa. `run_config.json`
beleži `backend.execution`, pa se za svaki run zna gde je generisan.

**Onih 39 commita sa `.local` adresom** ostaju nepripisani na GitHubu. Svesna odluka: prepisivanje
istorije bi pokvarilo `git_revision` zapisan u `provenance.json` za 19 runova, što je skuplje od
kozmetike. Identitet je od 19-09 podešen, pa se ne ponavlja.

---

## Kako nastaviti

```bash
# stanje svih runova (broj redova NIJE broj uspeha)
venv/bin/python scripts/build_run_index.py && cat benchmarking/runs/INDEX.md

venv/bin/python -m pytest tests -q          # 76

# prikupljanje lokalno, jedna konfiguracija
EXECUTION=local ONLY="c105" bash scripts/run_matrix_step1.sh &
caffeinate -i -m -w $! &

# stanje servera
ssh andrijat@rticuda.etf.bg.ac.rs "uptime; nvidia-smi; ollama ps"
```

`caffeinate` ne sprečava uspavljivanje kad se zatvori poklopac — laptop mora ostati otvoren i na
punjaču.
