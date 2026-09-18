# 19-09-2026 — Prikupljanje korak 1: 12 od 20 runova, pad servera

Grana: **`hierarchical-benchmark`**, pushovano. Nastavak na
[`18-09-2026 Hijerarhijski chunking, registar indeksa i prvi test sudije.md`](18-09-2026%20Hijerarhijski%20chunking,%20registar%20indeksa%20i%20prvi%20test%20sudije.md).

---

## Trenutno stanje

Prikupljanje je **prekinuto na zahtev korisnika**, u 01:49. Ništa ne radi u pozadini: skripta,
kolektor, SSH tunel i `caffeinate` su ugašeni, port 11435 je slobodan.

**12 od 20 runova je kompletno** i ispravno. Dve konfiguracije su gotove u celosti.

Korak 2 (mistral-large) **nije pokretan** — korisnik je izričito tražio da se ne dira.

---

## Šta je urađeno

### Pokrenuta matrica, korak 1

4 konfiguracije × 5 ponavljanja sa `mistral:latest` kao generatorom, `top_k=5`,
budžet 22.000 znakova, `num_ctx=16384`.

| Run | Uspešno | Odsečeno | Status |
|---|---|---|---|
| `dev_combined_c101_r01` … `r05` | 60/60 | 0 | **konfiguracija kompletna** |
| `dev_combined_c103_r01` … `r05` | 60/60 | 0 | **konfiguracija kompletna** |
| `dev_combined_c105_r01`, `r02` | 60/60 | 0 | kompletni |
| `dev_combined_c105_r03` | **0/60** | — | 60 grešaka, treba ponoviti |
| `dev_combined_c105_r05` | 6/60 | 0 | prekinut, nastavlja se |
| `dev_combined_c105_r04` | — | — | nikad nije startovao |
| `dev_combined_c107_r01` … `r05` | — | — | nisu startovali |

Konfiguracije: `c101` MiniLM+flat, `c103` MiniLM+hijerarhijski, `c105` bge-m3+flat,
`c107` bge-m3+hijerarhijski.

**`context_truncated` je `false` u svakom pitanju svakog runa.** Budžet od 22.000 znakova je tačno
odmeren — hijerarhijski isporučuje svih 5 pasusa u celini (do 20.460 znakova), flat takođe.

### Nove skripte

- **`scripts/run_matrix_step1.sh`** — pušta seriju. Svaka postavka koja bira konfiguraciju
  prosleđuje se kroz env promenljive u samoj komandi, pa nijedna izmena `.env`-a ne može pogrešno
  označiti run.
- **`scripts/build_run_index.py`** — pravi `benchmarking/runs/INDEX.md` čitajući iz svakog runa,
  ne iz ručno održavane liste.
- **`benchmarking/runs/README.md`** — uputstvo za snalaženje u folderu rezultata.

---

## Greške i šta je iz njih naučeno

### 1. Trka za SSH port — oborila 17 runova za 3 sekunde

Prva serija je pala skoro cela:

```
Error: Local port 11435 is already in use; change SSH_LOCAL_PORT.
```

Svaki run otvara svoj tunel na istom lokalnom portu. `ssh` proces prethodnog runa još se gasio kad
je sledeći pokušao da se poveže. Moj ponovni pokušaj išao je **odmah**, na isti zauzet port, pa je
i on pao — i tako redom kroz celu seriju, za manje od tri sekunde.

**Popravljeno** (commit „Ceka se oslobadjanje SSH porta izmedju runova"): čeka se oslobađanje
porta pre svakog pokušaja (do 60 s), ponovni pokušaj ima pauzu od 15 s.

### 2. Brojanje redova umesto uspeha — moja greška u izveštavanju

Prijavio sam korisniku da je `c105_r03` gotov jer `answers.jsonl` ima 60 redova. Imao je 60 redova
**grešaka**, nula uspešnih odgovora. Tunel je pukao nasred runa i svih 60 pitanja je palo za nula
sekundi.

Dva pravila koja iz ovoga slede, sada zapisana u `benchmarking/runs/README.md`:

1. Broj redova nije broj odgovora — pri nastavku runa pokušaj se dopisuje, važi poslednji.
2. `status: success` znači da je server vratio odgovor, ne da je odgovor tačan.

### 3. Prekid SSH tunela nasred runa

```
The SSH tunnel disconnected. Reconnect and resume with the same --run-id.
```

Ovo **nije** isti kvar kao prvi. Veza je pukla tokom rada, zaostali proces je držao port i oborio
i sledeći run. Nije popravljeno u kodu — tunel već ima `ServerAliveInterval=30`, pa je uzrok
mreža ili server, ne skripta. Runovi sa samim greškama se pri nastavku ponavljaju u celosti, tako
da nema polovičnih podataka.

### 4. Server je degradirao tokom noći

Ovo je najveći problem i **nije naš kvar**.

| Run | Početak | Medijana generisanja |
|---|---|---|
| `c101_r01` … `r05` | 21:57–22:30 | **2.0 s** |
| `c103_r01` … `r05` | 22:33–22:54 | 4.3–5.2 s |
| `c105_r01` | 22:59 | 3.6 s |
| `c105_r02` | 23:44 | **100.5 s** |
| `c105_r05` | 01:36 | **94.8 s** |

Između 22:59 i 23:44 brzina je pala **oko 30 puta**, uz isti model i isti prompt.

Provera servera u 23:42:

```
load average: 9.85    8 users    (16 niti)
nvidia-smi: Unable to determine the device handle for GPU0: Unknown Error
            No devices were found
```

Grafička se više ne prijavljuje, a mašina je pod tuđim opterećenjem. Ne može se tvrditi koje je od
toga uzrok, ali posledica je ista.

**Posledica za rad: merenja vremena su kontaminirana.** Brzina generisanja se ne sme koristiti kao
rezultat — razlika između `c101` i `c105` je stanje servera, ne konfiguracija. Ako brzina treba
radu, mora se meriti ponovo, na praznoj mašini, u jednom prolazu.

**Sadržaj odgovora nije ugrožen.** Sporost ne menja tekst odgovora; `status=success` i
`context_truncated=false` važe i za spore runove.

---

## Prvi rezultati

`c101` i `c103` su obe kompletne sa po 5 ponavljanja — pun par za poređenje chunkovanja.
Pretraga je deterministička, pa je ista u svih 5 ponavljanja.

| Konfiguracija | doc-hit@5 | MRR | kontekst |
|---|---|---|---|
| `c101` MiniLM + flat | **0.981** | 0.735 | 4.958 zn. |
| `c103` MiniLM + hijerarhijski | 0.942 | **0.825** | 17.243 zn. |
| `c105` bge-m3 + flat (3 ponavljanja) | **1.000** | 0.804 | 5.108 zn. |

Razmena koja se vidi: hijerarhijski **bolje rangira** (MRR 0.825 naprema 0.735 — tačan pasus
dolazi više gore), ali **češće promaši dokument** (0.942 naprema 0.981). Manja deca preciznije
pogađaju pitanje, ali ponekad promaše ceo dokument.

Dužina odgovora je praktično ista u sve tri konfiguracije (229 / 230 / 235 tokena) — tri i po puta
veći kontekst **nije** proizveo duže odgovore.

**Ovo su metrike pretrage, ne kvaliteta.** Da li su odgovori tačni još nije mereno.

---

## Šta ostaje

### Za prikupljanje

1. **`c105_r03`** — ponoviti u celosti (ima 60 grešaka).
2. **`c105_r04`** — nikad nije startovao.
3. **`c105_r05`** — nastavlja se od 7. pitanja.
4. **`c107_r01` … `r05`** — bge-m3 + hijerarhijski, nijedan nije startovan.

Ukupno **8 runova**. Ponovno pokretanje `scripts/run_matrix_step1.sh` preskače gotove i uzima
samo ove — ne duplira odgovore.

Pre pokretanja **proveriti server**: ako je i dalje ~100 s po pitanju, to je 10+ sati. Alternativa
je generisati lokalno (vidi ispod).

### Otvoreno od ranije

5. **Rubrika sudije** — odustajanje kada je `expected_behavior="answer"` dobija 4.0 umesto niske
   ocene. Nije popravljeno. Ocenjen je samo jedan probni run, pa je izmena i dalje jeftina.
6. **Drugi generator** — `mistral-large` je izmeren: 7.6 min za jedno pitanje na malom promptu,
   ~13 min na punom budžetu, dakle ~13 h po runu. Dogovoreno je da se koristi tek u koraku 2 i
   samo na pobedničkoj konfiguraciji, po izričitom odobrenju.
7. **Lokalno generisanje** — Mac ima `mistral:latest` sa **istim digestom** (`6577803aa9a0`) kao
   server. Nije mereno koliko M5 treba po pitanju. Ako je brži, generisanje može lokalno, bez
   SSH-a i bez tuđeg opterećenja — ali runovi bi tada bili sa druge mašine nego `c101`/`c103`, što
   se mora zabeležiti kao razlika u postavci.
8. **Skripta za zbirnu tabelu** za rad (prosek i standardna devijacija po konfiguraciji). Ne
   postoji.
9. **PR za granu** `hierarchical-benchmark` nije otvoren.

---

## Kako nastaviti

```bash
# stanje svih runova, tacno (broj redova nije broj uspeha)
venv/bin/python scripts/build_run_index.py && cat benchmarking/runs/INDEX.md

# provera servera pre nego sto se bilo sta pusti
ssh andrijat@rticuda.etf.bg.ac.rs "uptime; ollama ps; nvidia-smi"

# nastavak prikupljanja — preskace gotove runove
bash scripts/run_matrix_step1.sh
```

Serija se pokreće sa `caffeinate` vezanim za njen PID, inače Mac zaspi i tunel padne:

```bash
bash scripts/run_matrix_step1.sh &
caffeinate -i -m -w $! &
```

`caffeinate` ne sprečava uspavljivanje kad se zatvori poklopac — laptop mora ostati otvoren i na
punjaču.

Logovi su u `benchmarking/runs/_logs/` (nisu u gitu), po jedan po runu, plus `FAILED.txt`.
Objašnjenje strukture foldera rezultata je u `benchmarking/runs/README.md`.
