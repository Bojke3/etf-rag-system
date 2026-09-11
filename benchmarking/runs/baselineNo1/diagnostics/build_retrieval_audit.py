"""Reconstruct contexts without rerunning retrieval or contacting an LLM."""

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "benchmarking/runs/baselineNo1"
OUT = RUN / "diagnostics"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


metadata = read_json(ROOT / "models/vectorstore/metadatas.json")
questions = {q["id"]: q for q in read_json(ROOT / "benchmarking/finalna_pitanja.json")["questions"]}
config = read_json(RUN / "run_config.json")
answers = {}
for line in (RUN / "answers.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        row = json.loads(line)
        answers[row["id"]] = row

spec = importlib.util.spec_from_file_location("context_audit", ROOT / "src/retrieval/context.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

records = {}
counts = Counter()
rank_counts = Counter()
retained = []
for question_id, answer in answers.items():
    docs = []
    for rank, source in enumerate(answer["sources"], 1):
        matches = [m for m in metadata if m["document"] == source["document"]
                   and m["text"][:200] == source["text"]]
        if len(matches) != 1:
            raise ValueError(f"Expected one metadata match: {question_id}, rank {rank}; found {len(matches)}")
        docs.append({**matches[0], "rank": rank, "score": source["score"]})
    context = module.ContextBuilder.build_context(docs)
    remaining = 2000
    stopped = False
    for doc in docs:
        used = 0
        if not stopped:
            if len(doc["text"]) <= remaining:
                used = len(doc["text"])
                remaining -= used
            else:
                used = remaining if remaining > 100 else 0
                stopped = True
        doc["context_characters_used"] = used
        doc["included_text"] = doc["text"][:used]
        if used:
            rank_counts[doc["rank"]] += 1
    rebuilt = "\n\n".join(d["included_text"] for d in docs if d["context_characters_used"])
    assert rebuilt == context
    count = sum(d["context_characters_used"] > 0 for d in docs)
    counts[count] += 1
    retained.append(sum(d["context_characters_used"] for d in docs) / sum(len(d["text"]) for d in docs))
    records[question_id] = {
        "id": question_id, "question": questions[question_id]["question"],
        "expected_answer": questions[question_id]["expected_answer"],
        "actual_answer": answer["actual_answer"],
        "reference_sources": questions[question_id]["sources"],
        "reconstructed_context": context, "retrieved_chunks": docs,
    }

CON = "Pravilnik_o_OAS_preciscen_jun_2023"
OLD = "Pravilnik o osnovnim akademskim studijama"
ADM = "Pravilnik o upisu studenata"
NEW = "Izmena Pravilnika o osnovnim akademskim studijama"

# Selected cases are diagnostic examples, not a random sample or a full accuracy score.
CASES = [
    (1, "context_loss", [(ADM, 5)], "Pravilo ER/SI postoji u trećem pronađenom odlomku, ali taj odlomak ne ulazi u kontekst. Model zatim i izmišlja značenje skraćenica."),
    (3, "retrieval_miss", [(ADM, 9)], "Formula za srednjoškolske bodove postoji u indeksu, ali nije među pet rezultata. Kontekst počinje praksom i dobrovoljnim radom. Model ipak pokušava pogrešan račun."),
    (9, "context_loss", [(ADM, 24)], "Rok od 36 sati i žalba Komisiji nalaze se na petom mestu; model ne dobija taj tekst."),
    (12, "grounded_core_correct", [(CON, 32)], "Pravilo o 36 ESPB za afirmativnu meru ulazi iz drugog odlomka. Model daje ispravan osnovni odgovor."),
    (18, "grounded_core_correct", [(CON, 51)], "Mogućnost zamene nepoloženog izbornog predmeta nalazi se u prvom odlomku. Osnovni odgovor je tačan."),
    (24, "damaged_text_and_incomplete_retrieval", [(OLD, 50), (CON, 54)], "Model dobija oštećenu formulu 'S = Nx 60'. Odredba o plaćanju 2/3 za ponovo upisane predmete nije u top 5. Pogrešan obračun ima više uzroka; ne treba ga pripisati samo računanju modela."),
    (28, "generation_error", [(CON, 72)], "Procedura i poništavanje prethodne ocene ulaze u kontekst. Model ih navodi, a zatim zaključkom tvrdi da sedmica ostaje; odgovor je kontradiktoran."),
    (31, "retrieval_miss", [(CON, 69)], "Pravilo najave uvida najmanje 24 sata unapred postoji u indeksu, ali nije u top 5. Model bez osnova odobrava opisani termin."),
    (32, "retrieval_miss", [(CON, 69)], "Skala sa granicom 50/51 nije pronađena. Uzdržavanje je razumljivo u odnosu na dobijeni kontekst, ali RAG nije odgovorio na pitanje koje korpus pokriva."),
    (33, "retrieval_miss", [(CON, 68), (CON, 69)], "Skala 81–90 = 9 postoji u indeksu, ali nijedan od ovih odlomaka nije među pet rezultata."),
    (34, "retrieval_miss", [(CON, 60)], "Odredba o 30–70 predispitnih poena nije pronađena. Model iz povezanog, ali nedovoljnog teksta izvodi pogrešan zaključak da je dozvoljeno svih 100 poena na ispitu."),
    (36, "generation_error", [(CON, 61)], "Rok od 15 dana nalazi se u prvom odlomku. Model ga čita, ali nakon proteklih 18 dana tvrdi da ima još tri dana i izmišlja ponedeljak."),
    (38, "retrieval_miss", [(CON, 57), (CON, 58)], "Rok od 30 dana, granica 1. jun i uslovi odsustva postoje u indeksu, ali nisu pronađeni. Kontekst je o upisu i žalbama na prijemni."),
    (41, "retrieval_miss", [(CON, 23)], "Uslov svih položenih ispita za prijavu odbrane nije u top 5. Model izmišlja razliku po generaciji upisa."),
    (43, "generation_error", [(CON, 22)], "Prvi odlomak izričito kaže da se tema može promeniti samo jedanput. Model ipak odobrava ponovnu dobrovoljnu promenu, mešajući je sa posledicom isteka roka."),
    (44, "context_loss", [(NEW, 1)], "Nova odredba 'pratio i položio' je treći rezultat i potpuno otpada. Model dobija stariji tekst. Datum izmene takođe nije sačuvan uz ovaj odlomak kao metapodatak konteksta."),
    (45, "retrieval_miss", [(NEW, 1)], "Potrebna odredba izmene iz 2025. nije među pet rezultata. Stariji tekst ne omogućava pouzdan odgovor na pitanje o novoj verziji."),
    (47, "context_loss", [(NEW, 3)], "Rečenica o refundaciji 50% jeste u trećem rezultatu, ali ne stiže do modela. Zato model kaže da je nije pronašao."),
    (48, "retrieval_miss", [(CON, 16), (CON, 17)], "Odredbe o praksi u inostranstvu i 90 časova nisu pronađene. Model meša temu sa stranim srednjim školama i refundacijom školarine."),
    (53, "generation_error", [(OLD, 9)], "Prvi odlomak sadrži jasan rok 'najkasnije u prvoj sedmici semestra'. Model ga pretvara u prvi semestar/narednu akademsku godinu."),
    (54, "generation_error", [(CON, 18)], "Obaveza odgovora mejlom ulazi u kontekst. Model dodaje rok od 24 sata koji ta odredba ne propisuje. U prvom odlomku postoji 24 sata, ali za žalbu na prijemni: moguć prenos uslova iz nepovezanog pravila."),
    (56, "appropriate_abstention", [], "Model ne izmišlja iznos školarine za 2026/2027, koji benchmark označava kao nedostupan u dokumentima."),
    (57, "appropriate_abstention", [], "Model ne izmišlja datum i salu ispita, koje pravilnici ne sadrže."),
    (58, "retrieval_miss_and_unsupported_claim", [(CON, 66), (CON, 67)], "Odredba o tome da nastavnik određuje dozvoljena pomagala nije pronađena. Model zatim nedostatak dozvole pogrešno pretvara u zabranu kalkulatora."),
    (60, "unsupported_capability_claim", [], "Model sugeriše da može da proveri ličnu evidenciju i traži identifikacione podatke, iako dostupni izvori sadrže pravilnike, a ne ocene studenta."),
]

case_records = []
for number, diagnosis, references, note in CASES:
    record = records[f"REAL_{number:03d}"]
    evidence = []
    for document, chunk_id in references:
        m = next(m for m in metadata if m["document"] == document and m["chunk_id"] == chunk_id)
        match = next((d for d in record["retrieved_chunks"]
                      if d["document"] == document and d["chunk_id"] == chunk_id), None)
        evidence.append({"document": document, "chunk_id": chunk_id,
                         "retrieved_rank": match["rank"] if match else None,
                         "context_characters_used": match["context_characters_used"] if match else 0,
                         "text": m["text"]})
    case_records.append({"id": record["id"], "question": record["question"],
                         "expected_answer": record["expected_answer"], "actual_answer": record["actual_answer"],
                         "diagnosis": diagnosis, "explanation": note, "evidence_chunks": evidence})

report = {
    "run_id": "baselineNo1",
    "conclusion": "Postoje i promašaji pretrage, i gubitak već pronađenih dokaza pri sastavljanju konteksta, i greške Mistrala kada je pravilo prisutno. Osnovni tok radi, ali ovaj rezultat ne potvrđuje dovoljno pouzdan kvalitet odgovaranja. Sama promena LLM-a ne rešava sve tri grupe problema.",
    "scope": "Reconstruction for all 60 questions; manual causal review of 25 selected cases. No overall answer-accuracy or chunk-recall score is claimed.",
    "method": "Each saved 200-character source preview was matched uniquely, together with document name, to current index metadata. Current ContextBuilder was then applied to the original ranking. No retrieval or LLM call was repeated.",
    "limitations": [
        "The run did not save full chunks or the actual prompt/context. Reconstruction assumes the remainder of each matching chunk and context-building code are unchanged since collection.",
        "Benchmark and prompt-file hashes match the recorded run, but the run did not record an index hash or a context-builder hash.",
        "Selected diagnostic cases are not a random sample and their distribution must not be reported as full-run failure percentages.",
        "Finding a reference document is not evidence that its relevant article or all required facts were retrieved.",
    ],
    "verification": {
        "benchmark_hash_matches": sha(ROOT / "benchmarking/finalna_pitanja.json") == config["benchmark_sha256"],
        "prompts_hash_matches": sha(ROOT / "src/llm/prompts.py") == config["backend"]["prompts_sha256"],
        "current_metadata_sha256": sha(ROOT / "models/vectorstore/metadatas.json"),
        "current_index_sha256": sha(ROOT / "models/vectorstore/index.faiss"),
        "current_context_builder_sha256": sha(ROOT / "src/retrieval/context.py"),
        "unique_source_matches": sum(len(r["retrieved_chunks"]) for r in records.values()),
    },
    "summary": {
        "question_count": len(records), "indexed_chunk_count": len(metadata),
        "indexed_document_count": len({m["document"] for m in metadata}),
        "context_text_budget_characters": 2000,
        "questions_by_number_of_chunks_at_least_partially_included": dict(sorted(counts.items())),
        "questions_with_rank_at_least_partially_included": {str(i): rank_counts[i] for i in range(1, 6)},
        "mean_fraction_of_retrieved_text_in_context": round(sum(retained) / len(retained), 4),
        "manual_case_count": len(case_records),
    },
    "index_consistency_check": read_json(OUT / "index_consistency.json") if (OUT / "index_consistency.json").exists() else None,
    "embedding_observation": {
        "run_model": "sentence-transformers/all-MiniLM-L6-v2",
        "note": "The publisher labels the current model English. A multilingual model is a candidate for a separate retrieval experiment; improvement has not been measured in this audit. Changing embedding models requires rebuilding the index even if dimensions match.",
        "sources": ["https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2", "https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"],
    },
    "recommended_next_experiments": [
        "Save full retrieved chunks, chunk IDs, source metadata and exact context for every new run.",
        "Keep retrieval and Mistral fixed; test a context budget that fits all five current chunks without cutting a rule mid-sentence.",
        "Use manually selected complete evidence as context on diagnostic questions, with fixed generation settings, to isolate model errors.",
        "Verify index/model consistency, then evaluate a multilingual embedding model in a separate rebuilt index on retrieval alone.",
        "Preserve article boundaries and document versions; repair extracted tables/formulas and evaluate duplicate suppression or reranking.",
        "Compare LLMs only on identical saved contexts; lower temperature for a more controlled run, without assuming it repairs retrieval.",
    ],
    "cases": case_records,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "retrieval_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OUT / "reconstructed_contexts.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records.values()), encoding="utf-8")
print(json.dumps(report["summary"], indent=2))
