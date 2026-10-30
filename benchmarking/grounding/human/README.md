# Ručna provera podrške odgovora u dostavljenom kontekstu

Sve radi lokalno, bez API poziva i bez dodatnih biblioteka. Otvori HTML fajl direktno u pregledaču.

- `ocenjivac_grounding_A.html`: Andrija, svih 120 odgovora, po 20 iz svake konfiguracije.
- `ocenjivac_grounding_B.html`: Vuk, nezavisna provera unapred izabranih 30 odgovora, po 5 iz svake konfiguracije.
- `analysis_key_private.json`: mapiranje za analizu; ne koristiti tokom ocenjivanja. Nema prethodnih ocena sudije.

Svaki HTML sadrži celo pitanje, odgovor i stvarno dostavljeni kontekst. Model, konfiguracija, očekivani odgovor, prethodne ljudske ocene i API ocene nisu prikazani. A i B imaju različit redosled. B ne vidi ocene A. Zadržati nezavisnost do izvoza konačnih ocena; tek zatim razgovarati o neslaganjima.

## Pravila

1. **Potpuno podržan**: sve bitne činjenične tvrdnje, uključujući zaključak, imaju podršku u kontekstu.
2. **Delimično podržan**: glavni zaključak ima podršku, ali bar jedna druga bitna tvrdnja ili obrazloženje nema podršku ili protivreči kontekstu. Ako odgovor nema direktan zaključak, ali sadrži mešavinu podržanih i nepodržanih bitnih tvrdnji, koristi ovu oznaku.
3. **Nepodržan**: glavni zaključak nije podržan ili protivreči kontekstu, bez obzira na tačne sporedne detalje. Koristi i ako nijedna bitna tvrdnja nema podršku.
4. **Bez činjeničnih tvrdnji**: čisto uzdržavanje ili traženje pojašnjenja, bez tvrdnji o pravilima. Samo „nisam našao odgovor u kontekstu” ne računa se kao regulatorna tvrdnja.

Ne ocenjuj stil, relevantnost ni potpunost. Ne koristi spoljno znanje i ne popravljaj nečitljive formule pretpostavkama. Pazi na opseg zamene odredbe, izuzetke, stečene/preostale ESPB i potrebne/dovoljne uslove. Nepodržano ne znači nužno činjenično netačno: dokaz može samo nedostajati u dostavljenom kontekstu.

Za oznake 2 i 3 obavezno je kratko obrazloženje. Polje za dokaz je opciono: kopiraj jedan neprekinuti odlomak konteksta, bez umetanja `...`. Kad podrška nedostaje, dokaz može ostati prazan. Ne postoji unapred zadat „ispravan” odgovor niti automatski sudija koji prihvata tvoju semantičku ocenu.

## Čuvanje

Pregledač pokušava automatski da sačuva unose na tom računaru; prikazuje status čuvanja. Redovno klikni **Preuzmi JSON ocene**, obavezno pre zatvaranja ili promene uređaja. Delimičan izvoz je dozvoljen kao rezervna kopija. Za nastavak na drugom uređaju otvori isti HTML i učitaj svoj izvezeni JSON.

Završeni izvozi se zovu `grounding_ocene_A.json` i `grounding_ocene_B.json`. Ručno ih sačuvaj u ovaj direktorijum. Pregledač bez servera ne može direktno upisivati u proizvoljan folder projekta. HTML i JSON ne treba stavljati u direktorijume starih API runova.

## Analiza posle ocenjivanja

Iz korena projekta:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_grounding_annotation.py summarize --a benchmarking/grounding/human/grounding_ocene_A.json --b benchmarking/grounding/human/grounding_ocene_B.json
```

Ako je završio samo A, izostavi argument `--b`. Izveštaj će jasno navesti da nezavisna provera još nije dostupna. Analiza odbija nepotpune setove, pogrešan uzorak i neispravne dokaze. Generiše `summary.json`, `summary.md` i, uz B, `disagreements.json`.

Glavna raspodela unapred koristi ocene A nad 120 odgovora. B proverava 30 i služi za procenu slaganja: tačno slaganje i obična Cohenova kapa nad četiri kategorije, pre rasprave. Ne prosečavati kategorije i ne zamenjivati automatski ocene A ocenama B. Nezavisne izvoze zadržati ako se kasnije dodaje odvojeno usaglašavanje.

Ovo je **ljudska kategorizacija podrške na nivou odgovora**, a ne udeo podržanih atomskih tvrdnji i ne validacija API faithfulness ocena. U radu prikazati broj odgovora po kategoriji i konfiguraciji, primere grešaka, obim provere drugog ocenjivača i ograničenje uzorka od 20 odgovora po konfiguraciji. Ukupnih 120 odgovora ne predstavljaju 120 različitih nezavisnih pitanja. Čisto uzdržavanje prikazati odvojeno.

Za ponovnu izradu istih obrazaca bez promene uzorka ili redosleda:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_grounding_annotation.py prepare
```

Ponavljanje ne briše izvezene ocene. Promenjeni ulazni tekst zahteva novi direktorijum i novu proveru; ne mešati stare ocene sa izmenjenim kontekstima.
