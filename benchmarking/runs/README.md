# Šta je šta u `benchmarking/runs/`

Uputstvo za snalaženje. Pregled svih runova u tabeli je u [`INDEX.md`](INDEX.md) — pravi ga
`scripts/build_run_index.py` čitajući iz samih runova, pa ne može da odluta od stvarnog stanja.

## Hijerarhija

```
benchmarking/runs/
│
├── README.md                     ovo uputstvo
├── INDEX.md                      tabela svih runova (generisana, ne diraj ručno)
│
├── _logs/                        ispisi pokretanja, nisu u gitu
│   ├── dev_combined_c101_r01.log   ceo ispis tog runa
│   └── FAILED.txt                  spisak neuspelih pokušaja
│
└── <run_id>/                     jedan run = 60 pitanja kroz jednu konfiguraciju
    ├── run_config.json           recept: šta je pokrenuto
    ├── answers.jsonl             podaci: jedan red po pitanju
    ├── provenance.json           dokaz porekla: heševi ulaza
    ├── collection_summary.json   brojači
    └── scores/                   ocene, nastaju kasnije i ne prepisuju se
        └── rouge_llm_judge_<datum>_<vreme>.json
```

Jedan **run** je jedno prolaženje svih 60 pitanja kroz jednu konfiguraciju. Pretraga se izvršava
lokalno, generisanje odgovora ide preko SSH tunela na server.

## Imenovanje

```
dev_combined_c103_r01
 │    │        │    └── ponavljanje 01–05
 │    │        └─────── oznaka konfiguracije
 │    └──────────────── faza: base, emb, chunk, combined, llm
 └───────────────────── podela: dev, test, diag
```

Konfiguracije `c1xx` su runovi; `c001`–`c004` su **indeksi** i opisani su u
`models/registry.json`. To su dve različite stvari i namerno su u odvojenim opsezima.

Runovi bez ovog oblika (`baseline_context8k`, `baselineNo1`, `qwen35_9b_topk5`…) su istorijski,
od ranije. Zadržavaju svoja imena; vidi `docs/BENCHMARK_RUN_REGISTER.md`.

---

## `run_config.json` — šta je pokrenuto

Ovde gledaš kad hoćeš da znaš koja je ovo konfiguracija.

```json
"model": "mistral:latest",
"model_digest": "6577803aa9a03636...",
"generation_options": {"temperature": 0.7, "top_p": 0.9,
                       "num_predict": 2048, "num_ctx": 16384},
"context_max_chars": 22000,
"top_k": 5,
"prompt_strategy": "zero_shot",
"component_config": {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "vector_store_path": "models/vectorstore_c003_hier",
    "retrieval_threshold": 0.0
}
```

Digest modela je bitan: ime `mistral:latest` može da pokazuje na različite težine kroz vreme,
digest ne može.

---

## `answers.jsonl` — sami podaci

Jedan red po pitanju, 60 redova. Najveći fajl u folderu (1–3.5 MB) jer čuva doslovan prompt za
svako pitanje.

**Pitanje i merila** — prepisano iz benchmarka, da se ocenjivanje kasnije ne oslanja na spoljni fajl:
`question`, `expected_answer`, `required_facts`, `disallowed_claims`, `expected_behavior`

**Odgovor:** `actual_answer`, `status`, `error`, `retrieval_time_ms`, `generation_time_ms`, `wall_time_ms`

**`sources`** — pet pasusa koje je pretraga izvukla. Kod hijerarhijskog chunkovanja:

```json
{"document": "Pravilnik_o_OAS_preciscen_jun_2023",
 "chunk_id": "...::hierarchical::child::0069",
 "parent_chunk_id": "...::hierarchical::parent::0018",
 "expanded_to_parent": true,
 "section": "Clan 70.", "page": 1, "score": 0.51}
```

Vidi se cela putanja: koje je **dete** pogodilo pitanje, u kog je **roditelja** prošireno, iz kog
člana i sa koje strane. Kod flat chunkovanja nema `parent_chunk_id` ni `expanded_to_parent`, a
`chunk_id` je običan broj.

**`diagnostics`** — dokaz šta je tačno otišlo modelu:

```json
"context_chars": 17850,          // koliko je poslato
"full_context_chars": 17850,     // koliko je dohvaćeno
"context_truncated": false,      // ← kapija kvaliteta
"chunks_fully_included": 5,
"chunks_partially_included": 0,
"chunks_omitted": 0,
"system_prompt": "...",          // doslovno
"user_prompt": "...",            // doslovno
"generation": {"prompt_eval_count": 7827, "eval_count": 106,
               "done_reason": "stop"}
```

> **`context_truncated` mora biti `false` u svim pitanjima.** Ako je igde `true`, deo dohvaćenog
> teksta nikad nije stigao do modela i taj run **nije uporediv** sa ostalima na istom budžetu.
> `INDEX.md` ima kolonu `truncated` baš zbog toga.

`done_reason` reci nešto drugo osim `"stop"` (npr. `"length"`) znači da je odgovor presečen na
granici tokena — takav odgovor se ne sme računati kao potpun.

---

## `provenance.json` — dokaz porekla

Heš svakog ulaza i stanje mašine. Fajlovi se **ne kopiraju** u run, samo se beleži putanja i heš:

```json
"inputs": {
  "benchmark.json":                    {"sha256": "5d843c31..."},
  "vectorstore/index_hierarchical.faiss":     {"sha256": "2dd371b1..."},
  "vectorstore/metadatas_hierarchical.json":  {"sha256": "c5ca7af2..."},
  "vectorstore/parents_hierarchical.json":    {"sha256": "64bd175f..."}
},
"embedding": {"retriever": "ParentAwareRetriever(SimpleRetriever)",
              "effective_strategy": "hierarchical",
              "parent_chunks_held_out": 51},
"runtime_observed_now": {"platform": "macOS-26.3.1-arm64",
                         "git_revision": "a4af919f...",
                         "code_sha256": { /* 52 fajla */ }}
```

Time se kasnije dokazuje da je **baš taj** indeks i **ta** verzija koda dala ove odgovore.

Provera jednog runa, bez ijednog poziva modelu:

```bash
venv/bin/python scripts/benchmark_provenance.py --verify-run benchmarking/runs/<run_id>
```

Ako nešto nije poklopljeno tačno, izveštaj to navodi pod `input_match_exceptions`:

- `line_endings` — heš je snimljen na Windowsu iz CRLF radnog stabla, a fajl je u gitu LF.
  Pogađa stare runove; novi imaju 0 izuzetaka.
- `relocated` — direktorijum indeksa je preimenovan, a fajl je pronađen po **poklapanju heša**,
  ne po nagađanju.

---

## `collection_summary.json` — brojači

`total_questions`, `completed_questions`, `successful_questions`, `failed_questions`,
`average_wall_time_ms`, kad je počeo i završio. Brzi pregled bez otvaranja `answers.jsonl`.

---

## `scores/` — ocene

Nastaju kasnije, odvojeno od prikupljanja. Prikupljanje čuva sirove odgovore; ocenjivanje se može
ponavljati nad njima bez ponovnog generisanja.

```bash
venv/bin/python scripts/score_benchmark_run.py --run-id <run_id> --metrics rouge
venv/bin/python scripts/score_benchmark_run.py --run-id <run_id> --metrics rouge,llm_judge --judge-execution ssh
```

Svaki fajl ima vremensku oznaku i **nikad se ne prepisuje**, pa se ranije ocene čuvaju. ROUGE radi
lokalno; sudija traži server.

Upozorenje o metrikama: ROUGE, BLEU i BERTScore mere **preklapanje reči, ne tačnost**. Netačan
odgovor koji prepisuje rečnik reference dobija visok ROUGE, a tačan odgovor rečen drugim rečima
dobija nisku ocenu. Rangiranje konfiguracija po tačnosti nosi jedino sudija ili ručna provera.

---

## Brzе provere

```bash
# tabela svih runova
venv/bin/python scripts/build_run_index.py

# koliko je stvarno uspesnih odgovora (broj redova NIJE broj uspeha —
# red moze biti i greska)
venv/bin/python - <<'EOF'
import json, collections
rows=[json.loads(l) for l in open('benchmarking/runs/<run_id>/answers.jsonl')]
latest={r['id']: r for r in rows}          # poslednji pokusaj po pitanju
print(collections.Counter(r['status'] for r in latest.values()))
print('odseceno:', sum(1 for r in latest.values()
                       if (r.get('diagnostics') or {}).get('context_truncated')))
EOF
```

Dva pravila koja se lako previde:

1. **Broj redova nije broj odgovora.** Pri nastavku runa pokušaj se dopisuje, pa isto pitanje može
   imati više redova; važi poslednji. Run može imati 60 redova a nula uspeha.
2. **`status: success` znači da je server vratio odgovor**, ne da je odgovor tačan.
