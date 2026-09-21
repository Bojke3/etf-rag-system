# Skills za ovaj projekat

Ovde idu skillovi koje Claude Code **sam učitava** kad radi u ovom repou. Svako ko klonira repo
dobija iste skillove — za razliku od onih u `~/.claude/skills/`, koji važe samo na jednoj mašini.

## Kako se dodaje skill

Jedan skill = jedan folder sa fajlom `SKILL.md`:

```
.claude/skills/
└── ime-skilla/
    └── SKILL.md
```

Ime foldera je malim slovima, sa crticama umesto razmaka (`ime-skilla`, ne `Ime Skilla`).

`SKILL.md` počinje zaglavljem, pa uputstvom:

```markdown
---
name: ime-skilla
description: Jedna rečenica o tome KADA se skill koristi. Po ovome Claude odlučuje da li mu treba.
---

# Naslov

Uputstvo, koraci, pravila.
```

**`description` je najvažniji red u fajlu.** Claude ne čita ceo skill da bi odlučio da li mu treba,
nego samo taj opis. Zato u njemu treba da stoji **kada** se skill koristi, ne šta radi:

- loše: „Pravi dokumentaciju napretka."
- dobro: „Koristi se kad se završi zaokružen deo posla i treba zapisati dokle se stiglo, da sledeća
  sesija može da nastavi."

## Šta ide ovde, a šta ne

Ovde ide **kako se radi** — postupci, pravila, redosled koraka. Primeri za ovaj projekat: kako se
pokreće serija runova, kako se ocenjuje, šta se proverava pre commita.

Ne ide **šta se desilo** — to su zapisi sesija i oni idu u `AI/docs/`.

## Napomena o `AI/skills/`

Taj folder je postojao ranije i sadržao je `Progress Documentation.md`. Prebačen je ovamo kao
`progress-documentation/` i sada se učitava sam; pre toga je Claudeu moralo izričito da se kaže da
ga pročita. Folder `AI/skills/` više ne postoji — zapisi sesija i dalje idu u `AI/docs/`.
