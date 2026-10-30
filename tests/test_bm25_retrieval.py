"""Offline BM25 formula, normalization, corpus integrity and evidence-mapping tests."""
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.retrieval.bm25 import BM25Retriever, tokenize
from src.retrieval.context import ContextBuilder
from src.retrieval.parent_aware import ParentAwareRetriever
from scripts import evaluate_retrieval as ev
from scripts.run_bm25_retrieval import load_chunks, load_hierarchical, file_hash


def chunk(text, i=0):
    return {"text": text, "document": "Rules", "chunk_id": i}


class BM25Tests(unittest.TestCase):
    def test_script_and_diacritics_match(self):
        self.assertEqual(tokenize("Школарина, Ђак, Љиљана, Његош, Џак 2025"),
                         tokenize("Skolarina, Djak, Ljiljana, Njegos, Dzak 2025"))
        self.assertEqual(tokenize("ČĆŠŽ đ"), ["ccsz", "dj"])

    def test_hand_computed_score_and_query_term_deduplication(self):
        index = BM25Retriever([chunk("a a b"), chunk("b c", 1)])
        score = index.retrieve("a")[0]["score"]
        expected = math.log(2) * (2 * 2.2) / (2 + 1.2 * (.25 + .75 * 3 / 2.5))
        self.assertAlmostEqual(score, expected)
        self.assertEqual(index.retrieve("a"), index.retrieve("a a a"))

    def test_tf_saturates_and_length_normalization_penalizes_long_chunk(self):
        corpus = [chunk("x x"), chunk("x x " + "z " * 20, 1)]
        self.assertEqual(BM25Retriever(corpus).retrieve("x")[0]["chunk_id"], 0)
        saturated = BM25Retriever([chunk("x"), chunk("x " * 10, 1)], b=0)
        results = saturated.retrieve("x")
        self.assertGreater(results[0]["score"], results[1]["score"])
        self.assertLess(results[0]["score"] / results[1]["score"], 10)

    def test_ties_are_stable_and_source_text_is_not_normalized(self):
        corpus = [chunk("Rok je 30 dana!", 2), chunk("Rok je 30 dana!", 1)]
        results = BM25Retriever(corpus).retrieve("РОК")
        self.assertEqual([r["chunk_id"] for r in results], [2, 1])
        self.assertEqual(results[0]["text"], corpus[0]["text"])
        self.assertNotIn("score", corpus[0])

    def test_out_of_vocabulary_and_empty_queries_do_not_pad(self):
        index = BM25Retriever([chunk("rok"), chunk("ispit", 1)])
        self.assertEqual(index.retrieve("nepoznatorec"), [])
        self.assertEqual(index.retrieve("!?"), [])
        self.assertEqual(len(index.retrieve("rok", top_k=5)), 1)

    def test_parameter_validation(self):
        for kwargs in ({"k1": -1}, {"k1": float('nan')}, {"b": 1.1}, {"b": float('inf')}):
            with self.assertRaises(ValueError):
                BM25Retriever([chunk("rok")], **kwargs)
        with self.assertRaises(ValueError):
            BM25Retriever([])
        with self.assertRaises(ValueError):
            BM25Retriever([chunk("!?")])

    def test_actual_context_builder_round_trips_into_evidence_evaluator(self):
        text = "Uvod. Rok je 30 dana. Zavrsno pravilo."
        sources = BM25Retriever([chunk(text)]).retrieve("rok")
        row = {"sources": sources, "diagnostics": {**ContextBuilder.build_context_details(sources, 22000), "context_mode": "retrieved"}}
        retrieved, delivered, chars, mapped = ev.map_context(row, {ev.document_key("Rules"): text})
        self.assertTrue(ev.covers(delivered[ev.document_key("Rules")], 6, 21))
        self.assertEqual(chars, len(text))
        self.assertEqual(mapped[0]["rank"], 1)
        row = {"sources": [], "diagnostics": ContextBuilder.build_context_details([], 22000)}
        self.assertEqual(ev.map_context(row, {"rules": text})[:3], ({}, {}, 0))

    def test_manifest_rejects_modified_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); text = "Rok je 30 dana."
            (directory / "chunk.txt").write_text(text, encoding="utf-8")
            manifest = {"schema_version": 1, "stage": "chunking", "settings": {"strategy": "fixed_characters"},
                        "chunks": [{"file": "chunk.txt", "sha256": hashlib.sha256(text.encode()).hexdigest(),
                                    "chars": len(text), "document": "Rules", "chunk_id": 0}]}
            (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(load_chunks(directory)[0][0]["text"], text)
            (directory / "chunk.txt").write_text("Changed!", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA256"):
                load_chunks(directory)

    def test_hierarchical_search_ranks_children_then_deduplicates_without_refill(self):
        children = [{**chunk("rok rok", 0), "id": "c0", "parent_chunk_id": "p0"},
                    {**chunk("rok rok", 1), "id": "c1", "parent_chunk_id": "p0"},
                    {**chunk("rok", 2), "id": "c2", "parent_chunk_id": "p1"}]
        parents = {"p0": {"text": "Rok za ispit je 30 dana.", "document": "Rules"},
                   "p1": {"text": "Drugi rok.", "document": "Rules"}}
        lexical = BM25Retriever(children)
        wrapper = ParentAwareRetriever(lexical, parents)
        result = wrapper.retrieve("rok", top_k=2)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], parents["p0"]["text"])
        self.assertEqual(result[0]["score"], lexical.retrieve("rok", 2)[0]["score"])
        self.assertEqual(result[0]["matched_chunk_id"], "c0")
        self.assertEqual(len(wrapper.retrieve("rok", top_k=3)), 2)

    def test_hierarchical_loader_verifies_frozen_children_and_parents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); directory = root / "chunks"; reference = root / "run"; store = root / "store"
            for d in (directory, reference, store):
                d.mkdir()
            rows = [{"chunk_id": "p0", "level": "parent", "parent_chunk_id": None,
                     "text": "Rok za ispit je 30 dana.", "metadata": {"document": "Rules"}},
                    {"chunk_id": "c0", "level": "child", "parent_chunk_id": "p0",
                     "text": "Rok za ispit", "metadata": {"document": "Rules"}}]
            source = directory / "chunks.jsonl"
            source.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            manifest = {"schema_version": 1, "stage": "chunking", "settings": {"strategy": "hierarchical"},
                        "chunks_file": "chunks.jsonl", "chunks_file_sha256": file_hash(source),
                        "chunk_count": 2, "level_counts": {"parent": 1, "child": 1}}
            (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            meta = [{"id": "c0", "chunk_id": 0, "document": "Rules", "parent_chunk_id": "p0", "text": rows[1]["text"]}]
            parent_path = store / "parents_hierarchical.json"
            (store / "metadatas_hierarchical.json").write_text(json.dumps(meta), encoding="utf-8")
            parent_path.write_text(json.dumps({"p0": {"document": "Rules", "text": rows[0]["text"]}}), encoding="utf-8")
            config = {"component_config": {"vector_store_path": "store"}, "backend": {"retrieval_provenance": {
                "effective_strategy": "hierarchical", "files": {n: file_hash(store / n) for n in
                ("metadatas_hierarchical.json", "parents_hierarchical.json")}}}}
            (reference / "run_config.json").write_text(json.dumps(config), encoding="utf-8")
            with patch.object(ev, "ROOT", root):
                children, _, parents, _, verified = load_hierarchical(directory, reference)
                self.assertEqual(len(children), 1)
                self.assertEqual(parents["p0"]["text"], rows[0]["text"])
                self.assertTrue(verified["identical_children_and_parents"])
                parent_path.write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "artifact changed"):
                    load_hierarchical(directory, reference)


if __name__ == "__main__":
    unittest.main()
