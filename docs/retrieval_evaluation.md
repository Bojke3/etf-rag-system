# Provera dokaza u vraćenom kontekstu

Ova provera odvaja pronalaženje dokaza od kvaliteta generisanog odgovora.
Skripta radi lokalno, bez LLM-a, API ključa, embedding modela ili ponovnog
generisanja. Čita postojeće `answers.jsonl` fajlove i zamrznuti izvorni tekst.
Ne menja benchmark, vektorske baze niti run-ove.

## Šta je pripremljeno

**Stanje 2026-09-28:** korisnik je pregledao i odobrio svih 60 oznaka u razgovoru.
Iz REAL_006 uklonjen je E02 na njegov zahtev; REAL_030 zadržava oba dokaza.
Izveštaj `benchmarking/retrieval_reports/reviewed_20260928.json` (i `.md`)
ponovo ocenjuje istih pet r01 run-ova bez opcije `--allow-draft`.
Odobrenje oznaka ne uklanja ograničenja opisane metrike, naročito OCR formula
u REAL_024/REAL_051 i mogućih neoznačenih alternativnih izvora.

- `benchmarking/retrieval_evidence.json`: predložene oznake dokaza za 60 pitanja.
  Sve početne oznake imaju `review_status: "draft"`; predložio ih je AI.
- `benchmarking/retrieval_evidence_review.md`: čitljiv pregled pitanja,
  očekivanih odgovora i tačnih izvornih pasusa za ljudsku proveru.
- `scripts/evaluate_retrieval.py`: validacija oznaka i provera njihovog prisustva.
- `benchmarking/retrieval_reports/draft_20260928.json` i `.md`: probni izveštaj
  za r01 konfiguracija c101, c103, c105, c107 i c109. To nisu potvrđeni rezultati
  za rad niti konačan izbor konfiguracije.

U glavnom zbiru su 52 pitanja sa `expected_behavior=answer`. Četiri pitanja sa
delimičnim odgovorom i jedno koje zahteva razjašnjenje imaju poseban zbir
`supported_part`: proverava se samo dokaz za potkrepljene tvrdnje/uslove.
Tri pitanja sa `abstain` ne ulaze u pokrivenost pozitivnih dokaza. Prisustvo ili
odsustvo označenog teksta ne ocenjuje ispravno uzdržavanje, traženje dopune niti
dokazuje da informacija ne postoji nigde u korpusu.

## Postupak pregleda oznaka i budućih izmena

Otvorite `benchmarking/retrieval_evidence_review.md`. Za svako pitanje proverite:

1. Da li svi navedeni pasusi zajedno zaista omogućavaju odgovor, uključujući
   uslove i izuzetke? Za računanje se označava pravilo, ne izračunati rezultat.
2. Da li neki pasus zahteva nepotreban okolni tekst? Preširoka oznaka može
   neopravdano smanjiti ocenu kratkih chunkova.
3. Da li postoji drugi važeći pasus koji podjednako dokazuje pravilo? Dodajte ga
   kao alternativu. Prvobitni nacrt nema iscrpno označene sve alternativne
   formulacije u starijim pravilnicima i prečišćenoj verziji.
4. Da li je izvorna formula ili negacija oštećena OCR-om? Posebno proverite
   REAL_024 i REAL_051 u originalnom PDF-u. Prisustvo oštećene formule nije dokaz
   njene čitljivosti. Nemojte odobriti takav dokaz kao dovoljan bez te provere.
5. Da li je izabrana odgovarajuća verzija pravila? Identična ili slična rečenica
   iz drugog dokumenta ne smatra se automatski prihvatljivom alternativom.

Ispravke idu u JSON, ne u generisani Markdown pregled. Možete i navesti ID pitanja
i željenu ispravku asistentu da ažurira koordinate i ponovo napravi pregled.
Tek nakon stvarnog pregleda postavite `review_status` na `approved` i upišite
`reviewed_by` (ime ili stabilna oznaka stvarnog recenzenta). To je evidencija
provere, ne dokaz koji skripta može sama da potvrdi. Zamrznite pregledane oznake
pre konačnog poređenja konfiguracija; ne prilagođavajte ih željenom pobedniku.

## Kako skripta proverava tekst

Koordinate `start` i `end` označavaju interval `[start, end)` u izvornom tekstu
nakon zamene svih uzastopnih belina jednim razmakom i uklanjanja belina sa krajeva.
Velika/mala slova, brojevi, negacije, dijakritici i interpunkcija ostaju isti.
Hash izvora i samog intervala sprečava tiho korišćenje promenjenog korpusa.
Putanje su relativne u odnosu na koren projekta. Promena LF/CRLF ne menja oznake.

Svako pitanje ima obavezne jedinice dokaza (`requirements`). Potrebna je bar jedna
potpuna alternativa po jedinici; svi pasusi unutar te alternative su obavezni.
Skripta mapira svaki chunk na jednoznačnu poziciju u njegovom izvornom dokumentu.
Za konačni kontekst računa samo prosleđeni prefiks prema `chunk_usage`, i proverava
da rekonstrukcija zaista odgovara sačuvanom `diagnostics.context`.

Dokaz može biti raspoređen preko više chunkova: računa se unija intervala iz istog
izvora, pa preklapanja i duplikati ne donose dodatne poene. Rupa u kojoj nedostaje
reč ili negacija znači da ceo dokaz nije dostavljen. Kod hijerarhijskog retrievala
računa se tekst proširenog roditeljskog odlomka koji je zaista poslat generatoru.

Nema fuzzy/semantičkog poređenja. Ako chunk ne može jednoznačno da se mapira,
nedostaje snimljeni kontekst ili se ne slaže sa evidencijom korišćenja chunkova,
pitanje je `unscorable`, a ne nula. Poslednji pokušaj po ID-u pitanja ima prednost.
Neuspeh generisanja ne kvari ocenu pretrage ako je kontekst ipak uredno sačuvan.

## Metrike

- `delivered_coverage`: broj potpuno prisutnih jedinica dokaza / broj obaveznih
  jedinica za to pitanje. Nije procenat reči niti BERT/cosine sličnost.
- `complete`: sve obavezne jedinice imaju potpunu alternativu.
- `mean_evidence_coverage`: aritmetička sredina pokrivenosti po pitanju.
- `complete_evidence_rate`: udeo pitanja sa svim označenim dokazima.
- `retrieved_coverage`: ista provera nad vraćenim tekstom pre rezanja konteksta;
  pomaže da se razlikuje problem pretrage od problema budžeta konteksta.
- `context_chars_mean`: prosečna veličina stvarno dostavljenog konteksta.

`complete` znači da su označeni pasusi prisutni, ne da kontekst nema šuma,
zastarelih suprotstavljenih pravila ili OCR grešaka. Ne meri tačnost LLM-a.
Ovo su metrike pokrivenosti anotiranih dokaza, ne standardni dokumentni Recall@k
ili nDCG. Preciznost oznaka i njihovih alternativa određuje valjanost rezultata.

Ako bilo koje pitanje iz grupe nije ocenjivo, zbirni procenti te grupe su `null`
(`N/A` u tabeli); izveštaj prikazuje koliko pitanja nedostaje. Time parcijalan run
ili odobren samo lakši deo benchmarka ne dobija veštački dobru ukupnu ocenu.
Bez `--allow-draft`, nacrti se označavaju kao `needs_review`.

## Komande (PowerShell, iz korena projekta)

Ponovo napravi pregled nakon izmena oznaka:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py `
  --review-output benchmarking/retrieval_evidence_review.md
```

Probna provera jednog run-a dok su oznake nacrt:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py `
  --run benchmarking/runs/dev_combined_c105_r01 `
  --allow-draft `
  --output benchmarking/retrieval_reports/c105_draft_01.json
```

Nakon ljudske provere oznaka izostavi `--allow-draft`. Za poređenje dodaj još
`--run` argumenata. Izaberi novo ime izlaza za svaki izveštaj: postojeći JSON ili
Markdown izveštaj se ne prepisuje. Svaki izveštaj čuva hash oznaka, skripte i
pročitanih odgovora, kao i rezultat po jedinici dokaza, bez kopiranja pitanja,
odgovora i konteksta u svaki run. Pregled oznaka je jedan zajednički fajl.

Ako su konteksti kroz ponovljene run-ove isti (uporedi `context_sha256` po pitanju),
njihovo ponovno ocenjivanje ne daje nove nezavisne podatke. Pet generisanja i dalje
služe za procenu varijabilnosti odgovora u drugoj fazi.

## Provera implementacije

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_retrieval_evidence.py -v
```

Testovi proveravaju pogrešan pasus iz pravog dokumenta, nepotpun kontekst,
izostavljenu negaciju, spajanje dokaza iz chunkova, alternative, duplikate,
hijerarhijske ID-jeve, promenu izvora i izdvajanje nepregledanih oznaka.
