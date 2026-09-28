# Predlozi dokaza za proveru pretrage

Oznake je prvobitno predložio AI. Status uz svako pitanje pokazuje da li su pregledane. `draft` znači NACRT, bez potvrđene ljudske provere.

Proverite da li su navedeni pasusi dovoljni i ne traže nepotreban tekst. Dodajte alternativne dokaze, proverite OCR/formule i verzije pravilnika prema PDF-u. Menja se retrieval_evidence.json; ovaj pregled se ponovo generiše iz njega.

## REAL_001 — approved

Polagao sam i matematiku i fiziku: iz matematike imam 42, a iz fizike 55 poena. Koji rezultat mi se računa za ER, a koji za SI?

**Očekivani odgovor:** Za Elektrotehniku i računarstvo računa se bolji rezultat, dakle 55 poena iz fizike. Za Softversko inženjerstvo računa se matematika, dakle 42 poena. Rezultati dva prijemna se ne sabiraju.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28: „prvih pet su mi okej“. Bez izmena pasusa.

### E01: ER: bolji rezultat iz matematike ili fizike, bez sabiranja.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 5133:5264

> Za studijski program Elektrotehnika i racunarstvo vrednuje ce bolji rezultat ostvaren na prijemnom ispitu iz matematike ili fizike.

### E02: SI: vrednuje se matematika.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 5265:5373

> Za studijski program Softversko inzenjerstvo vrednuje ce rezultat ostvaren na prijemnom ispitu iz matematike

## REAL_002 — approved

Za prijemni spremam samo fiziku i nemam nagrade sa takmičenja. Da li time mogu da konkurišem i za SI?

**Očekivani odgovor:** Za rangiranje na Softverskom inženjerstvu vrednuje se prijemni iz matematike, pa sama fizika nije dovoljna. Fizika se može vrednovati za Elektrotehniku i računarstvo.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28: „prvih pet su mi okej“. Bez izmena pasusa.

### E01: ER: bolji rezultat iz matematike ili fizike, bez sabiranja.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 5133:5264

> Za studijski program Elektrotehnika i racunarstvo vrednuje ce bolji rezultat ostvaren na prijemnom ispitu iz matematike ili fizike.

### E02: SI: vrednuje se matematika.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 5265:5373

> Za studijski program Softversko inzenjerstvo vrednuje ce rezultat ostvaren na prijemnom ispitu iz matematike

## REAL_003 — approved

Proseci u četiri razreda srednje su mi 4,20, 4,50, 4,80 i 5,00. Na prijemnom imam 40 poena. Koliko ukupno imam za rang-listu?

**Očekivani odgovor:** Iz škole imaš (4,20 + 4,50 + 4,80 + 5,00) × 2 = 37,00 bodova. Sa 40 poena sa prijemnog ukupno imaš 77,00 bodova.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28: „prvih pet su mi okej“. Bez izmena pasusa.

### E01: Ukupni bodovi potiču iz škole i prijemnog.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 7917:8087

> Kandidat za upis na studijski program mozs ostvariti najvise 100 bodova i to PO osnovu opsteg uspeha u srednjoj SKOLI PO osnovu rszultata postignutog na prijemnom ispitu,

### E02: Zbir proseka puta dva daje školske bodove.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 8088:8274

> Pod opstim uspehom u srednjoj skoli podrazumeva ce zbir prosecnih ocena u svakom razredu srednje skole pomnozen ca dva: Po ovom osnovu kandidat moze steci najmanje 16, najvise 40 bodova.

## REAL_004 — approved

Imam ukupno 52 boda za upis u prvu godinu. Je l to znači da sam sigurno na budžetu?

**Očekivani odgovor:** Ne. Ispunjavaš minimum od 51 boda, ali moraš biti i rangiran u okviru odobrenog broja budžetskih mesta. Sam zbir od 52 boda ne garantuje budžet.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28: „prvih pet su mi okej“. Bez izmena pasusa.

### E01: Budžet: kvota i minimum 51 bod.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 8705:8914

> Kandidat ce moze upisati na studijski program U statusu studenta koji ce finansira iz budzeta ukoliko ce nalazi na rang listI DO broja odobrenog za upis kandidata na teret budzeta i ako ostvari najmanje 51 bod

## REAL_005 — approved

Za samofinansiranje je ostalo slobodnih mesta, ali imam ukupno 29 bodova. Da li mogu da se upišem po pravilniku o upisu?

**Očekivani odgovor:** Ne po tom pravilu: za samofinansiranje je potrebno najmanje 30 bodova i mesto na rang-listi u okviru predviđenog broja mesta. Slobodno mesto ne ukida bodovni minimum.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28: „prvih pet su mi okej“. Bez izmena pasusa.

### E01: Samofinansiranje: kvota i minimum 30 bodova.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 8915:9124

> Kandidat ce moze upisati na studijski program y statusu studenta koji ce sam finansira ukoliko ce nalazi na rang listI DO broja utvrd enog 3a upis samofinansirajucih studenata i ako ostvari najmanje 30 bodova.

## REAL_006 — approved

U četvrtom razredu sam dobio drugu nagradu na republičkom takmičenju iz informatike, kategorija A, u organizaciji Ministarstva i Društva matematičara Srbije. Želim i SI i ER. Da li sam za oba programa oslobođen prijemnog?

**Očekivani odgovor:** Nagrada se za SI vrednuje kao maksimalan broj poena na prijemnom iz matematike. Za rangiranje na ER moraš polagati matematiku ili fiziku, ili oba ispita. I za SI moraš ispuniti uslove prijave i konkursa i prijaviti matematiku; oslobađanje se odnosi na izlazak na ispit.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze uz uklanjanje E02 (priznavanje navedenog takmičenja iz informatike) kao nepotrebnog. Preostali ID-jevi E01, E03 i E04 zadržani su radi praćenja izmena.

### E01: Prve tri republičke nagrade u trećem/četvrtom razredu.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 9156:9509

> Kandidatima koji su kao ucenici treceg cetvrtog razreda srednje skole osvojili jednu od prve tri nagrade na republickom nivou viseetapnih takmicenja, u organizaciji Ministarstva prosvete; nauke i tehnoloskog razvoja Republike Srbije; iz predmeta koji ce polaze na prijemnom ispitu, priznaje ce maksimalan broj bodova iz tog predmeta na prijemnom ispitu.

### E03: Nagrada daje maksimum za SI, za ER potreban prijemni.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 10660:11049

> Ukoliko kandidat ima nagradu IZ Informatiks konkuriss za upis na studijski program Softversko inzenjerstvo, njemu ce ce samo pri rangiranju za ovaj studijski program priznati maksimalan broj poena sa prijemnog ispita Ovaj kandidat, med utim; mora polagati prijemni ISPIT iz Matematike ILI Fizike (ili oba) ukoliko zeli da ce rangira na listi studijskog programa Elektrotehnika racunarstvo,

### E04: Obavezna prijava matematike i ispunjenje uslova konkursa.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 11598:12024

> Kandidati koji konkurisu 'a upis na studijski program Softversko inzenjerstvo obavezno prijavljuju matematiku na prijavnom listu bilo da imaju nagradu IZ Matematike ILI Informatike ILI polazu prijemni ISPIT IZ Matematike Kandidati koji imaju nagrade su U obavezi da ispune sve uslove prijave prijemnog ispita i konkursa upisa, a oslobod eni su samog izlaska na ispit i dobijaju maksimalan broj bodova iz odgovarajuceg predmsta

## REAL_007 — approved

Prijavio sam ER kao prvu želju, ali bih posle rezultata prijemnog da stavim SI. Mogu li tada da promenim prvu želju?

**Očekivani odgovor:** Ne. Prva želja može da se izrazi i menja samo u fazi prijave kandidata, prema članu 12 pravilnika o upisu.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_006–REAL_010. Bez izmena pasusa.

### E01: Prva želja menja se samo tokom prijave.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 13820:13887

> Prvu zelju je moguce izraziti menjati samo u fazn prijave kandidata

## REAL_008 — approved

SI mi je bio prva želja i na njegovoj rang-listi sam u okviru broja budžetskih mesta. Da li ću se naći i na listi za ER?

**Očekivani odgovor:** Prema pravilu o prvoj želji, kandidat koji je na programu prve želje rangiran u okviru broja budžetskih mesta nalazi se samo na listi tog programa. U opisanoj situaciji to je lista za SI.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_006–REAL_010. Bez izmena pasusa.

### E01: Budžetska kvota prve želje znači samo listu tog programa.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 13983:14186

> Kandidati koji su na rang listi studijskog programa za kojn su izrazili prvu zelju, rangirani do broja odobrenog za upis kandndata na teret budzeta nalaze ce samo na listi studijskog programa prve zelje:

## REAL_009 — approved

Preliminarna rang-lista za upis je izašla pre 20 sati i mislim da mi je mesto pogrešno. Kome i do kada mogu da se žalim?

**Očekivani odgovor:** Žalba se podnosi Komisiji fakulteta u roku od 36 sati od objavljivanja preliminarne rang-liste. Ako je prošlo 20 sati, preostaje još 16 sati tog roka. Komisija donosi rešenje u roku od 24 sata od prijema žalbe.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_006–REAL_010. Bez izmena pasusa.

### E01: Žalba u 36 sati Komisiji; rešenje u 24 sata.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 21357:21666

> Kandidat moze podneti zalbu na regularnost postupka utvrd enog konkursom; regularnost prijemnog ispita ili na svoje mesto na rang listi u roku od 36 sati od objavljivanja prsliminarne rang liste na fakultetu Zalba ce podnosi Komisiji fakulteta, koja donosi resenje po zalbi y roku od 24 sata od prijema zalbe:

## REAL_010 — approved

Lična karta mi je istekla, ali imam važeći pasoš. Mogu li njime da se identifikujem na prijemnom?

**Očekivani odgovor:** Da. Na prijemni se donosi važeća lična karta ili pasoš. Identitet mora biti utvrđen pre polaganja.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_006–REAL_010. Bez izmena pasusa.

### E01: Važeća lična karta ili pasoš i utvrđivanje identiteta.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik o upisu studenata — pozicije 20495:20745

> Kandidat na prijemni ispit donosi dokument za identifikaciju vazecu licnu kartu iLI pasos Pre pristupanja ispitu Podkomisija za dezurstva na prijemnom ispitu, utvrd uje identitet kandidata Kandidat ciji identitet nije utvrd en ne moze polagati ispit.

## REAL_011 — approved

Na drugoj sam godini i ove skolske godine sam skupio tacno 48 ESPB. Da li mi je budzet za sledecu godinu zagarantovan?

**Očekivani odgovor:** Nije zagarantovan. Uz ostvarenih 48 ESPB iz upisanog programa, potrebno je da budeš rangiran u okviru odobrenog broja budžetskih mesta. Ako nisi u toj kvoti, status je samofinansirajući.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Budžet: 48 ESPB i mesto unutar kvote.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 27470:27793

> Status budzetskog studenta ima student: 1. upisan na osnovne akademske studije, rangiran na konkursu za upis kao takav, u skolskoj godini na koju je upisan po konkursu; 2. koji je u tekucoj skolskoj godini ostvario 48 ESPB bodova iz upisanog studijskog programa a koji je rangiran u okviru odobrenog broja mesta iz budzeta.

### E02: Van kvote student se sam finansira.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 28596:28897

> Status samofinansirajuceg studenta ima student: 1) upisan na osnovne akademske studije, rangiran na konkursu za upis kao takav, u skolskoj godini na koju je upisan po konkursu; 2) koji je u tekucoj skolskoj godini ostvario 48 ESPB bodova, ali nije rangiran u okviru ukupnog broja budzetskih studenata;

## REAL_012 — approved

Upisan sam po afirmativnoj meri i ove godine imam 36 ESPB. Da li i meni treba 48 za budžet sledeće godine?

**Očekivani odgovor:** Za studente upisane po afirmativnoj meri, kao i za studente sa invaliditetom, član 38 predviđa pravo na budžetsko finansiranje naredne godine sa ostvarenih 36 ESPB u tekućoj godini.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Afirmativne mere/invaliditet: 36 ESPB.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 27794:27982

> Studenti sa invaliditetom i studenti upisani po afirmativnoj meri koji u tekucoj skolskoj godini ostvare 36 ESPB bodova imaju pravo da se u narednoj skolskoj godini finansiraju iz budzeta.

## REAL_013 — approved

U četvrtoj godini sam bio na budžetu, ali mi je ostalo nekoliko ispita posle redovnog trajanja studija. Da li odmah prelazim na samofinansiranje?

**Očekivani odgovor:** Ne nužno. Student koji je u poslednjoj godini studija bio na budžetu zadržava pravo na budžetsko finansiranje najduže još godinu dana po isteku redovnog trajanja studija.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Budžet poslednje godine produžava se najduže godinu dana.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 28282:28471

> Student koji u poslednjoj godini studija ima status studenta koji se finansira iz budzeta, zadrzava pravo da se finansira iz budzeta najduze godinu dana po isteku redovnog trajanja studija.

## REAL_014 — approved

На буџету сам и до краја студија ми је остало укупно 20 ЕСПБ. Морам ли ипак да упишем 60?

**Očekivani odgovor:** Ne. Minimum od 60 ESPB za budžetskog studenta ima izuzetak kada je do kraja programa ostalo manje od 60. Možeš upisati preostalih 20 ESPB.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Minimum 60 ESPB i izuzetak za preostali manji broj.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 39476:39705

> Student koji se finansira iz budzeta opredeljuje se za onoliko predmeta koliko je potrebno da se ostvari najmanje 60 ESPB bodova u toku skolske godine, osim ako mu do kraja studijskog programa nije ostalo manje od 60 ESPB bodova.

## REAL_015 — approved

Samofinansiram se, ne studiram uz rad i do kraja imam još 100 ESPB. Mogu li da upišem samo 30 ESPB ove godine?

**Očekivani odgovor:** Po članu 48, samofinansirajući student upisuje najmanje 37 ESPB, osim kada mu do kraja ostaje manje. Pošto ti ostaje 100 ESPB i ne primenjuje se status studenta uz rad, 30 nije dovoljno.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Minimum 37 ESPB i izuzetak za preostali manji broj.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 39706:39928

> Student koji se sam finansira opredeljuje se za onoliko predmeta koliko je potrebno da se ostvari najmanje 37 ESPB bodova u toku skolske godine, osim ako mu do kraja studijskog programa nije ostalo manje od 37 ESPB bodova.

## REAL_016 — approved

Mogu da prijavim 40 ESPB iz treće godine, ali mi je ostao jedan ispit iz prve. Da li ispunjavam uslov da upišem treću godinu?

**Očekivani odgovor:** Ne. Pored mogućnosti prijave najmanje 37 ESPB iz naredne godine, za upis treće godine moraju biti položeni svi ispiti iz prve godine. Jedan preostali ispit iz prve godine sprečava ispunjenje tog uslova.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Uslov upisa: 37 ESPB iz naredne godine.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 42867:43106

> Student stice pravo na upis na visu godinu studijskog programa kada, u skladu sa studijskim programom, stekne mogucnost da prijavi predmete u vrednosti od najmanje 37 ESPB bodova, predvid ene studijskim programom za narednu godinu studija.

### E02: Za treću godinu svi ispiti prve moraju biti položeni.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 43107:43334

> Pored ostvarenog broja ESPB bodova, student mora pri upisu trece godine studija imati polozene sve ispite iz prve godine studija, odnosno, pri upisu cetvrte godine studija mora imati polozene sve ispite iz druge godine studija.

## REAL_017 — approved

Obnavljam godinu. Da li to znači da smem da slušam samo stare predmete i nijedan iz naredne godine?

**Očekivani odgovor:** Ne. Možeš prijaviti i predmete naredne godine za koje ispunjavaš preduslove, uz obaveznu prijavu svih nepoloženih predmeta ranijih godina po njihovom prioritetu. Za samofinansirajuće studente postoje dodatna ograničenja uzimanja predmeta treće i četvrte godine ako ranije godine nisu očišćene i iz nižih godina može da se prijavi najmanje 37 ESPB. Eventualni izuzetak za ta ograničenja odobrava prodekan za nastavu.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Naredni predmeti uz preduslove i prioritet svih prethodnih.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 40300:40831

> Studenti koji nisu stekli uslov za upis u narednu godinu studijskog programa mogu da prijave i slusaju, a po odslusanoj nastavi i da polazu predmete iz naredne godine studijskog programa, ako isti nisu uslovljeni nekim nepolozenim predmetom. Uslov za prijavu bilo kog predmeta odred ene godine studijskog programa jeste da student prijavi i sve nepolozene predmete iz svih prethodnih godina studijskog programa. Nepolozeni predmeti iz prethodnih godina studijskog programa redom predstavljaju prioritet pri prijavljivanju predmeta.

### E02: Ograničenja za samofinansiranje i izuzetak prodekana.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 40832:41534

> Student koji se sam finansira, a koji nije polozio sve predmete iz prve godine studijskog programa, ne moze prijaviti predmet trece godine studijskog programa ukoliko ima mogucnost da prijavi predmete prve i druge godine studijskog programa koji su potrebni da ostvari najmanje 37 ESPB bodova. Student koji se sam finansira, a koji nije polozio sve predmete iz druge godine studijskog programa, ne moze prijaviti predmet cetvrte godine studijskog programa ukoliko ima mogucnost da prijavi predmete druge i trece godine studijskog programa koji su potrebni da ostvari najmanje 37 ESPB bodova. 21 Izuzetak od pravila navedenih u stavovima 8 i 9 ovog clana je moguc samo uz odobrenje prodekana za nastavu.

## REAL_018 — approved

Nisam položio izborni predmet do početka sledeće školske godine i više ne želim da ga slušam. Mogu li da uzmem drugi izborni?

**Očekivani odgovor:** Da. Nepoložen izborni predmet možeš ponovo prijaviti ili se opredeliti za drugi izborni predmet. Za nepoložen obavezni predmet ponovo prijavljuješ isti predmet.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Obavezni se ponavlja; izborni može da se zameni.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 43675:43931

> Student koji ne polozi ispit iz obaveznog predmeta do pocetka naredne skolske godine, prijavljuje isti predmet. Student koji ne polozi izborni predmet do pocetka naredne skolske godine, moze ponovo prijaviti isti ili se opredeliti za drugi izborni predmet.

## REAL_019 — approved

Semestar je već počeo, a izborni koji sam prijavio mi ne odgovara. Mogu li sam da ga zamenim drugim?

**Očekivani odgovor:** Prijavljeni predmeti se po pravilu ne menjaju tokom školske godine. U izuzetnom slučaju, tokom semestra u kome se nastava održava, prodekan za nastavu može odobriti zamenu drugim predmetom iz istog semestra.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Promena predmeta izuzetno uz odobrenje, u istom semestru.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 44124:44365

> Predmeti koje je student prijavio, po pravilu se ne mogu menjati u toku skolske godine. U izuzetnim slucajevima, u toku semestra u kome se odrzava nastava, prodekan za nastavu moze odobriti zamenu predmeta za drugi predmet iz istog semestra.

## REAL_020 — approved

Prosek mi je 8,2, ali sam prošle školske godine položio svih 60 ESPB. Ako mi dekan odobri 72 ESPB radi bržeg završavanja, da li plaćam dodatnih 12?

**Očekivani odgovor:** Ne snosiš troškove dodatno prijavljenih ESPB po tom osnovu, jer si prethodne školske godine položio 60 ESPB. Uslov je prosek preko 8,5 ili položenih 60 ESPB prethodne godine, a odobreni obim ne sme preći 90 ESPB.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_011–REAL_020: „i narednih 10 je okej“. Bez izmena pasusa.

### E01: Odobrenje za više od 60, najviše 90 ESPB.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 44375:44545

> U cilju brzeg zavrsavanja studija, uspesnim studentima moze se omoguciti, na osnovu odluke dekana, prijavljivanje i vise od 60 ESPB bodova, ali ne vise od 90 ESPB bodova.

### E02: Oslobađanje: prosek preko 8,5 ILI 60 ESPB prethodne godine.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 44546:44704

> Ukoliko student ima prosek preko 8,5 ili je polozio predmete u obimu 60 ESPB u toku prethodne skolske godine, ne snosi troskove vise prijavljenih ESPB bodova.

## REAL_021 — approved

Uzeo sam fakultativni predmet preko programa i dobio desetku. Da li mi ta desetka podiže prosek?

**Očekivani odgovor:** Ne. Fakultativni predmeti se navode u dodatku diplome kao dodatna informacija, ali ne ulaze u prosečnu ocenu.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa.

### E01: Fakultativni se navode u dodatku, ne ulaze u prosek.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 44993:45107

> Fakultativni predmeti se navode u dodatku diplome kao dodatna informacija, ali se ne uracunavaju u prosecnu ocenu.

## REAL_022 — approved

Stekao sam uslov za treću godinu i prosek mi je 7,6. Želim da pređem na drugi modul ER-a. Da li mogu i kada se podnosi zahtev?

**Očekivani odgovor:** Ispunjavaš uslove da podneseš molbu: stečen uslov za treću godinu i prosek najmanje 7,5. Promena se traži pri upisu naredne školske godine, a godina na novom modulu zavisi od priznatih ispita i ESPB. Komisija izuzetno može razmatrati molbu početkom prolećnog semestra, ali se upis na novi modul i tada vrši početkom naredne školske godine. Odobrenje nije automatsko.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa.

### E01: Molba za promenu modula: uslov treće godine i prosek 7,5.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 38085:38299

> Student Fakulteta ima pravo da podnese molbu za prelazak sa upisanog modula na drugi modul studijskog programa nakon stecenog uslova za upis trece godine studijskog programa ukoliko ima prosecnu ocenu najmanje 7,5.

### E02: Priznati ispiti određuju godinu; upis i izuzetak za molbu.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 38300:38868

> Na osnovu priznatih ispita i ostvarenih ESPB bodova, odred uje se godina studijskog programa koju student moze upisati. 20 Promena izbornog podrucja - modula studijskog programa, ukoliko su ispunjeni uslovi iz prethodnog stava, vrsi se na licni zahtev, prilikom upisa u narednu skolsku godinu. Izuzetno, komisija za studije prvog stepena moze razmatrati molbe za promenu modula i na pocetku prolecnog semestra. Ukoliko Komisija za studije prvog stepena usvoji molbu, upis studenta u odgovarajucu studijsku godinu novog modula vrsi se na pocetku naredne skolske godine.

## REAL_023 — approved

Studiram na drugom univerzitetu i do kraja svog programa imam još 54 ESPB. Mogu li sada da pređem na ETF bez prijemnog?

**Očekivani odgovor:** Prema članu 43, student drugog univerziteta odnosno druge samostalne visokoškolske ustanove ne može se upisati tim putem ako mu je do kraja tamošnjeg programa ostalo 60 ili manje ESPB. Preostalih 54 ESPB potpada pod to ograničenje.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa.

### E01: Zabrana prelaska sa drugog univerziteta sa preostalih <=60 ESPB.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 34009:34301

> Student drugog univerziteta, odnosno druge samostalne visokoskolske ustanove, ne moze se upisati na Univerzitet, odnosno na visokoskolsku jedinicu u njegovom sastavu, ukoliko mu je do okoncanja studijskog programa na visokoskolskoj ustanovi na kojoj je upisan ostalo 60 ili manje ESPB bodova.

## REAL_024 — approved

Na ER-u sam samofinansirajući student. Upišem 30 ESPB novih predmeta i ponovo 12 ESPB nepoloženih iz prethodne godine. Ako je godišnja školarina za 60 ESPB 120.000 dinara i nemam druga oslobađanja, koliko iznosi školarina pre eventualne refundacije?

**Očekivani odgovor:** Cena jednog ESPB u ovom primeru je 120.000 / 60 = 2.000 dinara. Novi predmeti koštaju 30 × 2.000 = 60.000 dinara, a ponovo upisani nepoloženi predmeti na ER-u plaćaju se 2/3: 12 × 2.000 × 2/3 = 16.000 dinara. Ukupno je 76.000 dinara pre eventualne refundacije.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa. Tehnička napomena ostaje: formula je oštećena izdvajanjem/OCR-om; prisustvo teksta ne dokazuje čitljivost formule. U ovoj potvrdi nije posebno zabeležena provera originalnog PDF-a.

### E01: Nova formula školarine i značenje veličina.

Alternativa 1 (svi njeni pasusi su potrebni):

- Izmena Pravilnika o osnovnim akademskim studijama — pozicije 1810:2208

> ce brise i umesto njega unosi ce sledeci tekst: Student y statusu samofinansirajuceg studenta placa skolarinu prema formuli: S = N x 60 gde je S suma koju student placa, N broj ESPB bodova za predmete i ostale obaveze (strucna praksa; zavrsni rad) koje student upisuje; $ godisnja skolarina za odgovarajuci studijski program; koju svojom odlukom odred uje Savet fakulteta, na predlog Beca Fakulteta

### E02: ER: ponovo upisani nepoloženi predmeti plaćaju se 2/3.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 46873:47085

> Student osnovnih akademskih studija Elektrotehnika i racunarstvo koji u skolskoj godini ponovo upisuje nepolozene predmete iz prethodne skolske godine, a sam se finansira, placa 2/3 dela skolarine za te predmete.

## REAL_025 — approved

Plaćam školarinu, a tokom prethodne školske godine mi je preminuo roditelj. Da li postoji mogućnost oslobađanja i kome predajem molbu?

**Očekivani odgovor:** Možeš tražiti oslobađanje u visini 100% troškova tekuće godine koju upisuješ zbog smrtnog slučaja u užoj porodici tokom prethodne godine. Molbu sa dokazima podnosiš Studentskom odseku prilikom upisa godine, a rešenje donosi prodekan za nastavu.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa.

### E01: Smrtni slučaj: 100%, molba pri upisu i odluka prodekana.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 45960:46263

> Student koji placa skolarinu moze biti oslobod en placanja u visini od 100% troskova tekuce godine koju upisuje ukoliko je tokom prethodne godine imao smrtni slucaj u uzoj porodici. Odgovarajuce resenje donosi prodekan za nastavu, a molba sa dokazima podnosi se Studentskom odseku prilikom upisa godine.

## REAL_026 — approved

Pao sam isti ispit tri puta. Mogu li da trazim polaganje pred komisijom i ko je formira?

**Očekivani odgovor:** Da. Posle tri neuspešna polaganja istog ispita možeš tražiti polaganje pred komisijom. Komisiju formira prodekan za nastavu uz konsultacije sa šefom nadležne katedre.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa.

### E01: Tri neuspela polaganja; komisiju formira prodekan uz konsultacije.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 60732:60941

> Posle tri neuspela polaganja istog ispita student moze traziti da polaze ispit pred komisijom. Komisiju formira prodekan za nastavu uz konsultacije sa sefom katedre nadlezne za predmet iz koga se polaze ispit.

## REAL_027 — approved

Ocenu sa ispita sam dobio pre 30 sati. Mislim da ispit nije sproveden po pravilima. Kome podnosim prigovor i da li još imam vremena?

**Očekivani odgovor:** Prigovor na ocenu zbog nepravilnog sprovođenja ispita podnosiš dekanu u roku od 36 sati od dobijanja ocene. Ako je prošlo 30 sati, ostalo je još 6 sati roka.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa.

### E01: Prigovor zbog nepravilnosti dekanu u 36 sati.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 61198:61436

> Student ima pravo prigovora na ocenu dobijenu na ispitu, ako smatra da ispit nije obavljen u skladu sa Zakonom, Statutom Univerziteta, Statutom Fakulteta i ovim Pravilnikom. Prigovor se podnosi dekanu u roku od 36 sati od dobijanja ocene.

## REAL_028 — approved

Dobio sam sedmicu, ispit je bio regularan, ali želim bolju ocenu. Kako tražim ponovno polaganje i da li mi sedmica ostaje ako se predomislim posle odobrenja?

**Očekivani odgovor:** Zahtev podnosiš Studentskom odseku do kraja školske godine u kojoj si polagao ispit. O ponovnom polaganju odlučuje prodekan za nastavu. Ako odobri ponovno polaganje, prethodna sedmica se proglašava nevažećom; ne ostaje kao rezervna ocena. Ponovno polaganje se posebno plaća.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa.

### E01: Ponovno polaganje: rok, Studentski odsek, odluka, poništenje i naknada.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 61591:62030

> Student koji nije zadovoljan prelaznom ocenom na ispitu, ima pravo da podnese zahtev za ponovno polaganje ispita. Student zahtev podnosi Studentskom odseku do kraja skolske godine u kojoj je ispit polagao. Prodekan za nastavu donosi odluku o ponovnom polaganju ispita. U slucaju da ponovno polaganje ispita bude odobreno, prethodno dobijena ocena proglasava se nevazecom. 31 Student koji ponovo polaze ispit placa posebnu naknadu troskova.

## REAL_029 — approved

Propustio sam oba kolokvijuma iz jednog predmeta. Da li fakultet mora da mi omoguci da nadoknadim oba u prvom roku?

**Očekivani odgovor:** Obavezno pravo na nadoknadu odnosi se samo na jedan kolokvijum po predmetu, u prvom ispitnom roku nakon odgovarajućeg semestra, uz prijavu preko studentskih servisa. Nastavnici mogu organizovati dodatne nadoknade, ali iz pravilnika ne sledi obaveza da ti nadoknade oba.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa.

### E01: Pravo na jednu nadoknadu u prvom roku uz prijavu.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 54614:54864

> Studentima se mora omoguciti da polazu nadoknadu kolokvijuma u toku trajanja prvog ispitnog roka nakon semestra u kome je kolokvijum organizovan. Ovo pravo se odnosi samo na jedan kolokvijum po predmetu, koji se prijavljuje preko studentskih servisa.

### E02: Dodatne nadoknade su mogućnost nastavnika.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 55118:55195

> Nastavnici mogu da organizuju nadoknade kolokvijuma u svim ispitnim rokovima.

## REAL_030 — approved

Nisam položio predmet iz prolećnog semestra do septembra. Ako izađem u februaru naredne školske godine, da li mi važe stari poeni sa kolokvijuma?

**Očekivani odgovor:** Da. Za predmete iz prolećnog semestra predviđeno je polaganje i u februarskom roku naredne školske godine, a poeni iz predispitnih obaveza priznaju se i u tom roku.

**Napomena:** Korisnik je 2026-09-28 odobrio dokaze u grupi REAL_021–REAL_030: „21-30 su okej“. Bez izmena pasusa. Korisnik je pitao da li je E02 dovoljan; E01 i E02 su zadržani jer postojeći required_facts zasebno traži mogućnost polaganja u narednom februaru i važenje predispitnih poena. Uklanjanje E01 nije zatraženo.

### E01: Prolećni predmeti mogu se polagati i u narednom februaru.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 53965:54297

> Student moze polagati ispite iz predmeta koji se izvode u jesenjem semestru u januarskom, februarskom, julskom, avgustovskom i septembarskom ispitnom roku, a ispite iz prolecnog semestra ima pravo da polaze u junskom, julskom, avgustovskom i septembarskom ispitnom roku, kao i u februarskom ispitnom roku u narednoj skolskoj godini.

### E02: Predispitni poeni važe i narednog februara.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 54444:54604

> Izuzetno za ispite iz prolecnog semestara, ostvareni poeni predispitnih obaveza iz prethodnog stava priznaju se i u februarskom roku u narednoj skolskoj godini.

## REAL_031 — approved

Rezultati pisanog ispita su objavljeni danas u 12, a uvid je zakazan za 13 časova istog dana i tek je sada najavljen. Je li to u skladu sa pravilnikom?

**Očekivani odgovor:** Nije. Termin uvida mora biti objavljen najkasnije uz rezultate pisanog ispita i najmanje 24 sata pre uvida. Najava samo sat vremena unapred ne ispunjava taj rok.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Najava uvida uz rezultate i najmanje 24 sata unapred.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 59584:59769

> Termin uvida u pregledane zadatke nakon pismenog ispita mora biti objavljen najkasnije u trenutku isticanja rezultata pismenog ispita, a najmanje 24 sata pre odrzavanja uvida u zadatke.

## REAL_032 — approved

Imam ukupno tačno 50 poena iz predispitnih obaveza i završnog ispita. Da li je to šestica po skali iz pravilnika?

**Očekivani odgovor:** Ne. Do 50 poena je ocena 5, odnosno ispit nije položen. Ocena 6 počinje od 51 poena.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Ocena 6 počinje od 51, do 50 je ocena 5.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 59096:59150

> 51-60 poena 6 dovoljan D do 50 poena/ 5 nije polozio F

## REAL_033 — approved

Испунио сам све обавезе и укупно имам 81 поен. Која је то оцена према скали у правилнику?

**Očekivani odgovor:** Ukupno 81 poen pripada rasponu 81-90, što je ocena 9.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Raspon 81–90 daje ocenu 9.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 59016:59046

> 81-90 poena 9 izuzetno dobar A

## REAL_034 — approved

Na predmetu kažu da svih 100 poena dobijamo samo na završnom ispitu, bez poena tokom semestra. Da li pravilnik predviđa takvu raspodelu?

**Očekivani odgovor:** Ne. U ukupnih 100 poena, za predispitne aktivnosti i provere znanja u toku semestra mora biti predviđeno najmanje 30, a najviše 70 poena.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Predispitne obaveze nose 30–70 od ukupno 100 poena.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 51774:52015

> U strukturi ukupnog broja poena 26 najmanje 30, a najvise 70 poena mora biti predvid eno za aktivnosti i provere znanja u toku semestra ( predispitne obaveze). Ukupno 100 poena se stice ispunjavanjem predispitnih obaveza i polaganjem ispita.

## REAL_035 — approved

Ostao mi je samo jedan nepoložen ispit do kraja OAS. Imam li pravo na dodatno polaganje pred početak nove školske godine?

**Očekivani odgovor:** Da. Student sa samo jednim preostalim nepoloženim ispitom ima pravo na dodatno ispitivanje u poslednjem ispitnom roku pre početka naredne školske godine.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Jedan preostali ispit: dodatno ispitivanje u poslednjem roku.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 55205:55424

> Izuzetno, student kome je preostao samo jedan nepolozen ispit do okoncanja studijskog programa osnovnih akademskih studija, ima pravo na dodatno ispitivanje u poslednjem ispitnom roku pre pocetka naredne skolske godine.

## REAL_036 — approved

Od kolokvijuma je prošlo 18 dana, a rezultati nisu objavljeni. Postoji li rok za njihovu objavu?

**Očekivani odgovor:** Da. Rezultati kolokvijuma moraju biti objavljeni najkasnije 15 dana od održavanja. U opisanoj situaciji taj rok je prekoračen za 3 dana.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Objava rezultata kolokvijuma u roku 15 dana.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 52333:52441

> Rezultati kolokvijuma moraju da budu objavljeni najkasnije u roku od 15 dana od dana odrzavanja kolokvijuma.

## REAL_037 — approved

Одобрено ми је мировање године. Могу ли ипак да изађем на један испит или завршим лабораторијске вежбе док мировање траје?

**Očekivani odgovor:** Ne. Tokom odobrenog mirovanja ne možeš polagati ispite, ostvarivati predispitne obaveze niti druge obaveze iz nastavnog procesa. Pravilo za polaganje posle dužeg opravdanog odsustva ne daje dozvolu za polaganje tokom odobrenog mirovanja.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Zabrana ispita i predispitnih obaveza tokom mirovanja.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 49099:49230

> Tokom odobrenog mirovanja, student ne moze da polaze ispite ili ostvaruje predispitne obaveze i druge obaveze iz nastavnog procesa.

## REAL_038 — approved

Zbog teže bolesti želim da tražim mirovanje. Da li je dovoljno da samo predam molbu do kraja školske godine ili postoje posebni rokovi i uslovi odsustva?

**Očekivani odgovor:** Zahtev se podnosi u roku od 30 dana od nastanka sprečenosti, a najkasnije do 1. juna za tekuću školsku godinu. Mirovanje se može odobriti samo kada je student propustio dva uzastopna ispitna roka ili bio sprečen da pohađa nastavu najmanje tri meseca. Teža bolest je jedan od predviđenih osnova.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Teža bolest je osnov za mirovanje na zahtev.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 48335:48428

> Studentu se, na njegov zahtev, odobrava mirovanje prava i obaveza, u slucaju:  teze bolesti;

### E02: Rok 30 dana/najkasnije 1. jun i uslov odsustva.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 49511:49820

> Zahtev za mirovanje prava i obaveza student podnosi u roku od 30 dana od dana nastanka sprecenosti, a najkasnije do 1. juna za tekucu skolsku godinu. 25 Mirovanje se moze odobriti samo u slucajevima kada je student propustio dva sukcesivna ispitna roka, ili bio sprecen da pohad a nastavu najmanje tri meseca.

## REAL_039 — approved

Vec sam jednom na ovom programu dobio mirovanje jer nisam mogao da platim skolarinu. Mogu li sledece godine ponovo da ga trazim po istom finansijskom osnovu?

**Očekivani odgovor:** Po tom osnovu mirovanje se može odobriti u trajanju od jedne školske godine i samo jednom tokom studija na istom programu. Zato drugi put ne možeš ostvariti mirovanje po istom osnovu nemogućnosti plaćanja školarine.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Finansijski osnov: jedna godina i samo jednom na programu.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 48717:48971

> Studentu se moze odobriti mirovanje i u slucaju nemogucnosti placanja skolarine u trajanju od jedne skolske godine i to jednom u toku studija na istom studijskom programu, zbog nedostatka materijalnih sredstava, u skladu sa merilima koje utvrdi Fakultet.

## REAL_040 — approved

Redovan sam student četvorogodišnjeg programa i nemam poseban status. Od upisa je prošlo osam školskih godina, od kojih sam jednu celu godinu bio u odobrenom mirovanju. Da li sam time već potrošio osmogodišnji rok i mogu li da tražim produženje?

**Očekivani odgovor:** Godina odobrenog mirovanja ne ulazi u rok, pa je u opisanom primeru iskorišćeno sedam godina tog roka. Na lični zahtev podnet pre isteka roka može se odobriti produženje do trostrukog trajanja programa, odnosno do 12 školskih godina koje se računaju u rok. Produženje nije automatsko.

**Napomena:** AI predlog dokaza korisnik je pregledao i odobrio u razgovoru 2026-09-28, u grupi REAL_031–REAL_040: „31-40 su dobra isto“. Bez izmena pasusa.

### E01: Redovni rok osam godina za četvorogodišnji program.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 49857:49998

> Status studenta prestaje ako student ne zavrsi studije u roku od osam skolskih godina, za studijski program koji traje cetiri skolske godine.

### E02: Mirovanje isključeno; produženje na zahtev pre isteka do trostrukog roka.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 50115:50454

> U rok iz st. 1 i 2 ovog clana ne racuna se vreme mirovanja prava i obaveza, odobrenog studentu u skladu sa Statutom Fakulteta. Studentu se na licni zahtev, podnet pre isteka roka iz st. 1 i 2 ovog clana, moze produziti rok za zavrsetak studija do isteka roka u trostrukom broju skolskih godina potrebnih za realizaciju studijskog programa.

## REAL_041 — approved

Završni rad mi je gotov, ali imam još jedan nepoložen ispit. Mogu li prvo da prijavim odbranu pa da ispit položim kasnije?

**Očekivani odgovor:** Ne. Za prijavu odbrane moraš imati položene sve ispite i ispunjene sve obaveze predviđene studijskim programom. Studentski odsek na obrascu overava ispunjenost tih uslova.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Prijava odbrane uz sve obaveze; overa Studentskog odseka.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 19872:20145

> Za prijavu odbrane zavrsnog rada student mora imati polozene sve ispite i ispunjene sve obaveze predvid ene studijskim programom. Prijava odbrane zavrsnog rada se vrsi na propisanom obrascu Fakulteta, na kome Studentski odsek overava ispunjenost uslova iz prethodnog stava.

## REAL_042 — approved

Temu završnog sam prijavio pre 13 meseci i nisam dobio produženje. Mogu li samo da nastavim sa istom temom?

**Očekivani odgovor:** Redovni rok za odbranu je jedna godina od prijave teme; ako se ne odbrani u tom roku, mora se uzeti nova tema. Izuzetno se, na zahtev i iz opravdanih razloga, uz odobrenje šefa odseka rok može produžiti najviše šest meseci. Bez odobrenog produženja ne možeš pretpostaviti da stara tema i dalje važi.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Godina za odbranu; nova tema ili produženje do šest meseci.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 18894:19205

> Student je u obavezi da odbrani zavrsni rad u roku od jedne godine od dana prijave teme. U suprotnom, student mora da uzme novu temu. Studentu se moze na njegov zahtev, izuzetno u opravdanim slucajevima, po odobrenju sefa 11 odseka, odobriti produzenje roka za odbranu zavrsnog rada, ali najvise za sest meseci.

## REAL_043 — approved

Već sam jednom promenio temu završnog rada uz odobrenje šefa odseka. Mogu li ponovo da je promenim zato što sam našao zanimljiviju?

**Očekivani odgovor:** Član 26 dozvoljava promenu teme uz odobrenje šefa odseka samo jedanput. Druga dobrovoljna promena teme po tom pravilu nije predviđena.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Promena teme uz odobrenje samo jednom.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 18787:18893

> Student moze po odobrenju sefa odseka da promeni temu zavrsnog rada. Tema se moze promeniti samo jedanput.

## REAL_044 — approved

Profesor nije angažovan na mom modulu, a njegov predmet sa drugog modula sam slušao, ali nisam položio. Može li da mi bude mentor prema izmeni iz oktobra 2025?

**Očekivani odgovor:** Ne po tom osnovu. Izmena člana 26 iz oktobra 2025. zahteva da je nastavnik angažovan na predmetu drugog modula koji je student pratio i položio. Samo slušanje nije dovoljno. Druga mogućnost je da nastavnik bude angažovan na predmetu studentovog modula, što u pitanju nije slučaj.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Izmenjeni uslov mentora: angažovan na predmetu koji je student pratio i položio.

Alternativa 1 (svi njeni pasusi su potrebni):

- Izmena Pravilnika o osnovnim akademskim studijama — pozicije 1009:1333

> ce brise i umesto njega unosi ce sledeci tekst: Student moze uzeti zavrsni rad samo kod nastavnika koji je angazovan na nekom od predmeta izbornog podrucja - modula studijskog programa na kome je student upisan, ili na predmetu koji je student pratio i polozio, koji pripada drugom izbornom podrucju modulu osnovnih studija:

## REAL_045 — approved

Položio sam predmet drugog modula kod profesora A, ali bih završni radio kod profesora B koji je takođe angažovan na tom predmetu. B nije na mom modulu. Da li to dopušta izmena iz oktobra 2025?

**Očekivani odgovor:** Da, ako si taj predmet pratio i položio i profesor B je na njemu angažovan. Izmenjeni član 26 vezuje uslov za angažovanje nastavnika na predmetu koji si pratio i položio, pa mentor ne mora biti baš nastavnik kod koga si polagao. I dalje važi da tema završnog rada mora biti iz oblasti modula koji si upisao.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Tema mora ostati u oblasti upisanog modula.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 18033:18116

> Zavrsni rad mora biti iz oblasti izbornog podrucja - modula koje je student upisao.

### E02: Izmenjeni uslov mentora: angažovan na predmetu koji je student pratio i položio.

Alternativa 1 (svi njeni pasusi su potrebni):

- Izmena Pravilnika o osnovnim akademskim studijama — pozicije 1009:1333

> ce brise i umesto njega unosi ce sledeci tekst: Student moze uzeti zavrsni rad samo kod nastavnika koji je angazovan na nekom od predmeta izbornog podrucja - modula studijskog programa na kome je student upisan, ili na predmetu koji je student pratio i polozio, koji pripada drugom izbornom podrucju modulu osnovnih studija:

## REAL_046 — approved

U prečišćenom pravilniku iz 2023. piše da se praksa i završni plaćaju pri prijavljivanju završnog rada. Da li mogu to isto da tvrdim na osnovu teksta posle izmene iz oktobra 2025?

**Očekivani odgovor:** Ne. Izmena iz oktobra 2025. zamenjuje član 52 i izostavlja raniju rečenicu da se školarina za praksu i završni rad plaća u trenutku prijavljivanja završnog rada. Formula srazmerna broju upisanih ESPB ostaje. Novi tekst ne navodi konkretan zamenski rok plaćanja, pa se on ne može utvrditi iz same te izmene.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa. Meri se samo prisustvo dokaza za potkrepljeni deo/uslove. Ne meri se prepoznavanje nepoznatih podataka, odsustva pravila ili potreba za dopunom.

### E01: Zamena člana 52: stari i novi tekst radi poređenja roka.

Alternativa 1 (svi njeni pasusi su potrebni):

- Izmena Pravilnika o osnovnim akademskim studijama — pozicije 1334:2273

> U clanu 52. tekst koji glasi: ,Student u statusu samofinansirajuceg studenta placa skolarinu prema formuli: ; 5 = N h 60 gde je S suma koju student placa; N broj ESPB bodova za predmete I ostale obaveze (strucna praksa; zavrsni rad) koje student upisuje; $ godisnja skolarina za odgovarajuci studijski program; koju svojom odlukom odred uje Savet fakulteta; na predlog Beca Fakulteta Skolarina za strucnu praksu i zavrsni rad placa ce u trenutku prijavljivanja zavrsnog rada. ce brise i umesto njega unosi ce sledeci tekst: Student y statusu samofinansirajuceg studenta placa skolarinu prema formuli: S = N x 60 gde je S suma koju student placa, N broj ESPB bodova za predmete i ostale obaveze (strucna praksa; zavrsni rad) koje student upisuje; $ godisnja skolarina za odgovarajuci studijski program; koju svojom odlukom odred uje Savet fakulteta, na predlog Beca Fakulteta U preostalom delu tekst Pravilnika ostaje neizmenjen i na snazi_

## REAL_047 — approved

Da li u izmeni iz oktobra 2025. piše da mogu da dobijem nazad 50% dela školarine za praksu i završni rad? Da li taj dokument objašnjava i kako da podnesem zahtev?

**Očekivani odgovor:** U obrazloženju izmene navodi se da promena člana 52 omogućava refundaciju od 50% i za deo školarine koji potiče od ESPB za stručnu praksu i završni rad. Dokument ne opisuje postupak podnošenja zahteva, rokove, potrebna dokumenta niti sve uslove za ostvarivanje refundacije.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa. Meri se samo prisustvo dokaza za potkrepljeni deo/uslove. Ne meri se prepoznavanje nepoznatih podataka, odsustva pravila ili potreba za dopunom.

### E01: Obrazloženje refundacije 50% za praksu i završni.

Alternativa 1 (svi njeni pasusi su potrebni):

- Izmena Pravilnika o osnovnim akademskim studijama — pozicije 2554:2726

> Izmenom clana 52. bice omoguceno samofinansirajucim studentima da ostvare refundaciju od 50% i za onaj deo skolarine koji proistice iz ESPB za strucnu praksu i zavrsni rad.

## REAL_048 — approved

Upisao sam ETF 2021. i nasao firmu u inostranstvu za strucnu praksu. Da li to moze da se prizna i sta treba da proverim i predam?

**Očekivani odgovor:** Praksa može da se obavi i u inostranstvu. Pre izbora organizacije treba da konsultuješ rukovodioca prakse na svom modulu da proveriš priznavanje aktivnosti. Potrebno je najmanje 90 časova prakse, izveštaj studenta i potvrda odgovornog lica sa potpisom i pečatom organizacije. Priznata praksa nosi 2 ESPB i opisnu ocenu „priznaje se”.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Praksa u inostranstvu i prethodna konsultacija rukovodioca.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 14350:14607

> Strucna praksa se moze obaviti i u inostranstvu. Potrebno je da student pre izbora organizacije u kojoj ce raditi praksu konsultuje rukovodioca prakse na odgovarajucem modulu kako bi proverio da li se predvid ene aktivnosti mogu priznati kao strucna praksa.

### E02: 90 časova, izveštaj, potvrda/potpis/pečat, 2 ESPB i opisna ocena.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 14741:15062

> Po obavljenoj strucnoj praksi od najmanje 90 casova, a na osnovu izvestaja studenta i potvrde odgovornog lica koje potpisom i pecatom organizacije potvrd uje da je praksa obavljena, studentu se dodeljuju 2 ESPB boda za obavljenu strucnu praksu. Strucna praksa se ne ocenjuje numericki, vec opisno, ocenom ''priznaje se''.

## REAL_049 — approved

Ja sam upisao 2019/2020, a kolega 2021/2022. Obojica smo odradili po 80 sati stručne prakse. Da li je to dovoljan broj sati za obojicu?

**Očekivani odgovor:** Za tebe, upisanog pre 2020/2021, prelazna odredba propisuje najmanje 80 sati. Za kolegu upisanog 2021/2022 primenjuje se minimum od 90 časova, pa mu nedostaje još 10. Ispunjen broj sati sam po sebi ne zamenjuje ostale uslove priznavanja, poput izveštaja i potvrde organizacije.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Pre 2020/2021 najmanje 80 sati.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 62955:63081

> Za studente upisane pre skolske 2020/2021. godine trajanje strucne prakse iz clana 19 ovog Pravilnika iznosi najmanje 80 sati.

### E02: Opšti uslov 90 časova uz izveštaj i potvrdu.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 14741:14985

> Po obavljenoj strucnoj praksi od najmanje 90 casova, a na osnovu izvestaja studenta i potvrde odgovornog lica koje potpisom i pecatom organizacije potvrd uje da je praksa obavljena, studentu se dodeljuju 2 ESPB boda za obavljenu strucnu praksu.

## REAL_050 — approved

Planiram semestar na razmeni i našao sam predmete slične našim. Šta treba da dogovorim pre prijave da bi mi ispiti bili priznati po povratku?

**Očekivani odgovor:** Pre prijave za mobilnost kontaktiraš nastavnike najbližih odgovarajućih predmeta na ETF-u radi procene podudarnosti sadržaja. Na osnovu njihovih saglasnosti prodekan za nastavu potpisuje Ugovor o učenju. Priznavanje ugovorenih položenih predmeta garantuje se ako po povratku dostaviš odgovarajući transkript ocena.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Kontakt nastavnika pre prijave i procena sadržaja.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 23912:24419

> Student je pre prijavljivanja za mobilnost duzan da kontaktira nastavnika angazovanog na predmetu koji je najslicniji sa predmetom koji planira da prati i polaze u toku svog boravka na drugoj visokoskolskoj ustanovi van sastava Univerziteta. Predmetni nastavnik procenjuje da li je poklapanje sadrzaja dva predmeta dovoljno veliko da bi se student mogao osloboditi pracenja i polaganja predmeta na kome je on angazovan ( na maticnom Fakultetu) na osnovu polozenog predmeta na drugoj visokoskolskoj ustanovi.

### E02: Saglasnosti, potpis prodekana i priznavanje uz transkript.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 24420:24717

> Na osnovu dobijene saglasnosti od strane predmetnih nastavnika, Prodekan za nastavu u ime Fakulteta potpisuje Ugovor o ucenju, kojim se studentu garantuje da ce predmeti koje polozi tokom boravka na mobilnosti biti priznati, ukoliko po povratku sa mobilnosti dostavi odgovarajuci transkript ocena.

## REAL_051 — approved

Za budžetsko rangiranje imam dve godine studiranja bez mirovanja i zbir svih doprinosa e × (1 + r) × ocena jednak 990, bez fakultativnih predmeta. Kolika mi je srednja ponderisana ocena po izmeni člana 49 iz 2020?

**Očekivani odgovor:** Po toj formuli zbir se deli sa S × 60. Za S = 2 dobija se 990 / (2 × 60) = 8,25. To je srednja ponderisana ocena za rangiranje, a ne automatska potvrda da si u budžetskoj kvoti.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa. Tehnička napomena ostaje: formula je oštećena izdvajanjem/OCR-om; prisustvo teksta ne dokazuje čitljivost formule. U ovoj potvrdi nije posebno zabeležena provera originalnog PDF-a.

### E01: Formula izmene iz 2020: imenilac S×60 i definicije.

Alternativa 1 (svi njeni pasusi su potrebni):

- Odluka o izmeni Pravilnika o osnovnim akademskim studijama — pozicije 871:1257

> e; x (1 +r)x 0; spo = I=1 Sx 60 gde je spo srednja ponderisana ocena, N ukupan broj predmeta studijskog programa koje je student polozio (ne racunajuci fakultativne predmete); ei broj ESPB bodova za predmet, 0; ocena koju je ostvario na ispitu, r stimulativni faktor, $ broj godina studiranja studenta od trenutka upisa (ne racunajuci godine koje je student proveo u statusu mirovanja):

### E02: Budžetsko finansiranje zavisi od rangiranja.

Alternativa 1 (svi njeni pasusi su potrebni):

- Odluka o izmeni Pravilnika o osnovnim akademskim studijama — pozicije 452:870

> Prilikom upisa svake skolske godine; studenti ce na osnovu Zakona 0 VISOKOM obrazovanju i Statuta Univerziteta rangiraju za budzetsko finansiranje: Rangiranje studenata obuhvata studente upisane iste skolske godine na odred eni studijski program; a vrsi ce polazeci od broja ostvarenih ESPB bodova I postignutog uspeha U savlad ivanju studijskog programa; na osnovu srednje ponderisane ocene formirane na sledeci nacin

## REAL_052 — approved

Predmet sam prvi put upisao prošle školske godine, pa ga ponovo upisao ove. Položio sam ga u prvom roku ove godine. Dobijam li stimulativni faktor 0,1 za budžetsko rangiranje?

**Očekivani odgovor:** Ne. Faktor 0,1 za prvi ili drugi odgovarajući rok dobijaju samo studenti koji su predmet položili u školskoj godini kada su ga prvi put upisali. Pošto je predmet prvi put upisan prethodne godine, za ovaj ispit faktor je 0.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Stimulacija samo u godini prvog upisa i u prva dva roka.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 42412:42702

> Stimulativne faktore dobijaju samo studenti koji su ispite polozili u skolskoj godini kada su prvi put upisali predmet i to ri=0,1 ukoliko je student polozio ispit u prvom ili drugom ispitnom roku u kome je stekao pravo na polaganje ispita, ri=0 ukoliko je ispit polozio u ostalim rokovima.

## REAL_053 — approved

Počela je druga nedelja semestra, a plan rada za predmet još nije javno dostupan. Do kada nastavnik treba da objavi plan sa obavezama i načinom ocenjivanja?

**Očekivani odgovor:** Plan rada na predmetu mora biti javno dostupan studentima najkasnije u prvoj sedmici semestra. Plan obuhvata predispitne obaveze, način ocenjivanja i druge podatke o predmetu, pa je u opisanoj situaciji rok već istekao.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: Plan uključuje predispitne obaveze i ocenjivanje.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 8152:8492

> Plan rada ukljucuje:  osnovne podatke o predmetu: naziv, godina, fond casova, broj ESPB bodova;  preduslove za prijavljivanje predmeta;  ciljeve predmeta;  sadrzaj i strukturu predmeta;  plan izvod enja nastave (predavanja i vezbe);  predispitne obaveze studenata;  broj i okvirne termine odrzavanja kolokvijuma,  nacin ocenjivanja;

### E02: Objava plana najkasnije u prvoj nedelji.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 8709:8873

> Predmetni nastavnik je u obavezi da plan rada na predmetu ucini javno dostupnim studentima najkasnije u prvoj sedmici semestra u kome se izvodi nastava iz predmeta.

## REAL_054 — approved

Profesor je jedan termin konsultacija zamenio mejlom. Ako mu pitanje o gradivu pošaljem sa zvanične fakultetske adrese, da li ima obavezu da odgovori i u kom roku?

**Očekivani odgovor:** Jedan termin konsultacija može biti zamenjen konsultacijama elektronskom poštom. U tom slučaju postoji obaveza odgovora na pitanja poslata sa zvanične fakultetske adrese. Član 20 ne određuje konkretan rok odgovora u satima ili danima.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa. Meri se samo prisustvo dokaza za potkrepljeni deo/uslove. Ne meri se prepoznavanje nepoznatih podataka, odsustva pravila ili potreba za dopunom.

### E01: Zamena konsultacija mejlom i odgovor sa fakultetske adrese.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 15926:16163

> Jedan termin konsultacija moze se zameniti konsultacijama pomocu elektronske poste, pri cemu su nastavnici i saradnici obavezni da odgovore na sva postavljena pitanja koje student postavi sa zvanicne fakultetske adrese elektronske poste.

## REAL_055 — approved

Imao sam celu školsku godinu odobrenog mirovanja. Da li mi se ona računa i u broj godina za budžetsko rangiranje i u rok za završetak studija?

**Očekivani odgovor:** Ne računa se ni u jednom od ta dva obračuna. Član 49 iz broja godina S za budžetsko rangiranje isključuje godine provedene u statusu mirovanja, a član 57 iz roka za završetak studija isključuje vreme odobrenog mirovanja.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa.

### E01: S za rangiranje isključuje godine mirovanja.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 42292:42411

> S broj godina studiranja studenta od trenutka upisa ( ne racunajuci godine koje je student proveo u statusu mirovanja).

### E02: Rok završetka isključuje odobreno mirovanje.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 50115:50241

> U rok iz st. 1 i 2 ovog clana ne racuna se vreme mirovanja prava i obaveza, odobrenog studentu u skladu sa Statutom Fakulteta.

## REAL_056 — approved

Kolika je tačno godišnja školarina za SI za školsku 2026/2027, u dinarima?

**Očekivani odgovor:** U priloženim dokumentima nema odluke sa iznosom godišnje školarine za SI za 2026/2027. Dokument određuje način obračuna i ko utvrđuje godišnju školarinu, ali za konkretan iznos potrebna je odgovarajuća odluka o školarini za tu školsku godinu.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa. Nema pozitivnog dokaza za traženi podatak u korpusu. Isključeno iz evidence coverage; ispravnost uzdržavanja ocenjuje se zasebno.

## REAL_057 — approved

Kog datuma i u kojoj sali je ispit iz Matematike 1 u septembarskom roku 2026?

**Očekivani odgovor:** Priloženi pravilnici ne sadrže konkretan raspored Matematike 1 za septembar 2026. Potreban je raspored ispita odnosno odgovarajuće obaveštenje za taj rok. Pravilo o ispitnim rokovima nije dovoljno da se utvrde datum i sala.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa. Nema pozitivnog dokaza za traženi podatak u korpusu. Isključeno iz evidence coverage; ispravnost uzdržavanja ocenjuje se zasebno.

## REAL_058 — approved

Da li smem da koristim kalkulator na ispitu iz Osnova elektrotehnike 1?

**Očekivani odgovor:** Iz ovih pravilnika se ne može utvrditi da li je kalkulator dozvoljen baš na tom predmetu. Predmetni nastavnik odlučuje koja pomoćna sredstva smeju da se koriste i o tome obaveštava studente na početku nastave. Potrebno je proveriti pravila ili obaveštenje za taj predmet.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa. Meri se samo prisustvo dokaza za potkrepljeni deo/uslove. Ne meri se prepoznavanje nepoznatih podataka, odsustva pravila ili potreba za dopunom.

### E01: Nastavnik određuje pomoćna sredstva i obaveštava na početku.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 57198:57387

> Predmetni nastavnik odlucuje koja se pomocna sredstva mogu koristiti na ispitu (knjiga, tabele, dijagrami, kalkulatori i slicno) i o tome obavestava studente na pocetku nastave na predmetu.

## REAL_059 — approved

Imam 60 ESPB na drugom fakultetu. Mogu li bez prijemnog da pređem na ETF i budem odmah na budžetu?

**Očekivani odgovor:** Sam podatak o 60 ESPB nije dovoljan za potvrdu prelaska. Potrebno je razjasniti da li su to osnovne akademske studije iz oblasti elektrotehničkog i računarskog inženjerstva, koliko ESPB je ostalo do završetka, kao i uslove i priznavanje ispita. Ako je reč o posebnom upisu bez prijemnog iz člana 43, upis je samo u statusu samofinansirajućeg studenta, pa po tom osnovu nije moguć neposredan upis na budžet.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa. Meri se samo prisustvo dokaza za potkrepljeni deo/uslove. Ne meri se prepoznavanje nepoznatih podataka, odsustva pravila ili potreba za dopunom.

### E01: Uslovi za prelazak sa druge ustanove.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 32864:33324

> 2) student druge visokoskolske ustanove, upisan na studijski program osnovnih akademskih studija iz oblasti Elektrotehnicko i racunarsko inzenjerstvo, koji je polozio sve ispite sa prve godine, odnosno ostvario najmanje 60 ESPB bodova na studijskom programu akademskih studija na drugoj visokoskolskoj ustanovi, pod uslovima koje propisuje Vece Fakulteta svojom odlukom, na predlog Komisije za studije prvog stepena i na osnovu misljenja predmetnih nastavnika;

### E02: Upis na samofinansiranje; ograničenje preostalih ESPB.

Alternativa 1 (svi njeni pasusi su potrebni):

- Pravilnik_o_OAS_preciscen_jun_2023 — pozicije 33858:34301

> Lice iz stava 1 ovog clana moze se upisati samo kao samofinansirajuci student i ne ubraja se u odobreni broj studenata za odred eni studijski program. Student drugog univerziteta, odnosno druge samostalne visokoskolske ustanove, ne moze se upisati na Univerzitet, odnosno na visokoskolsku jedinicu u njegovom sastavu, ukoliko mu je do okoncanja studijskog programa na visokoskolskoj ustanovi na kojoj je upisan ostalo 60 ili manje ESPB bodova.

## REAL_060 — approved

Možeš li da proveriš koju sam ocenu dobio iz Programiranja 1 i koliko trenutno imam ukupno ESPB?

**Očekivani odgovor:** To se ne može utvrditi iz priloženih pravilnika, jer oni ne sadrže tvoje lične rezultate ispita ni evidenciju ostvarenih ESPB. Potrebna je tvoja studentska evidencija ili podaci iz nje.

**Napomena:** Korisnik je pregledao i odobrio preostale oznake REAL_041–REAL_060 u razgovoru 2026-09-28: „i do kraja je sve okej“. Bez izmena pasusa. Nema pozitivnog dokaza za traženi podatak u korpusu. Isključeno iz evidence coverage; ispravnost uzdržavanja ocenjuje se zasebno.
