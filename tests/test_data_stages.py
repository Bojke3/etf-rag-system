"""Offline regression tests for extraction, reusable chunking and indexing inputs."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.data import Document, SimpleChunker, TextPreprocessor
from src.data.stages import extract_documents, chunk_documents, read_manifest
from scripts.index_documents import index_documents


class DataStagesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "documents"
        self.source.mkdir()
        self.raw = "  Правило о студирању.\n\n\nStudent   has 81 points.\n" * 20
        (self.source / "rules.txt").write_text(self.raw, encoding="utf-8")
        self.snapshot = self.root / "snapshot"

    def extract(self):
        return extract_documents(self.source, self.snapshot, enable_ocr=False)

    def test_rechunking_matches_old_pipeline_without_loading_or_cleaning_again(self):
        manifest = self.extract()
        record = manifest["documents"][0]
        self.assertEqual((self.snapshot / record["raw_file"]).read_text(encoding="utf-8"), self.raw)
        cleaned = TextPreprocessor().clean(self.raw)
        self.assertEqual((self.snapshot / record["cleaned_file"]).read_text(encoding="utf-8"), cleaned)
        with patch("src.data.loaders.DocumentLoaderFactory.load_document", side_effect=AssertionError("Must not load PDFs")), \
             patch.object(TextPreprocessor, "clean", side_effect=AssertionError("Must not clean again")):
            for size, overlap in [(1024, 150), (512, 51)]:
                output = self.root / f"chunks_{size}"
                result = chunk_documents(self.snapshot, output, size, overlap)
                actual = [(output / item["file"]).read_text(encoding="utf-8") for item in result["chunks"]]
                expected = [c.text for c in SimpleChunker(size, overlap).split(Document(cleaned, {}))]
                self.assertEqual(actual, expected)

    def test_existing_outputs_and_changed_snapshot_are_rejected(self):
        self.extract()
        with self.assertRaisesRegex(ValueError, "empty directory"):
            self.extract()
        output = self.root / "chunks"
        chunk_documents(self.snapshot, output)
        before = (output / "manifest.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "empty directory"):
            chunk_documents(self.snapshot, output, 512, 10)
        self.assertEqual((output / "manifest.json").read_bytes(), before)
        (self.snapshot / "cleaned/rules.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Artifact changed"):
            chunk_documents(self.snapshot, self.root / "other")

    def test_no_usable_text_does_not_publish_snapshot_and_restores_environment(self):
        with patch.dict(os.environ, {"ETF_RAG_ENABLE_OCR": "original"}), \
             patch("src.data.loaders.DocumentLoaderFactory.load_document", return_value=Document("", {})):
            with self.assertRaisesRegex(ValueError, "No usable text"):
                self.extract()
            self.assertEqual(os.environ["ETF_RAG_ENABLE_OCR"], "original")
        self.assertFalse((self.snapshot / "manifest.json").exists())
        with self.assertRaisesRegex(ValueError, "Missing extraction manifest"):
            chunk_documents(self.snapshot, self.root / "chunks")

    def test_duplicate_stems_rejected_before_extraction(self):
        (self.source / "rules.pdf").write_bytes(b"placeholder")
        with patch("src.data.loaders.DocumentLoaderFactory.load_document") as loader:
            with self.assertRaisesRegex(ValueError, "unique stems"):
                self.extract()
            loader.assert_not_called()

    def test_extraction_passes_ocr_options_and_preserves_raw_output(self):
        expected = "Scanned rule.\r\nAnother line."

        def load_document(path):
            self.assertEqual(os.environ["ETF_RAG_ENABLE_OCR"], "1")
            self.assertEqual(os.environ["ETF_RAG_OCR_MAX_PAGES"], "2")
            self.assertEqual(os.environ["ETF_RAG_OCR_LANGUAGES"], "rs_cyrillic,en")
            return Document(expected, {"source": path, "ocr_used": True})

        with patch("src.data.loaders.DocumentLoaderFactory.load_document", side_effect=load_document):
            result = extract_documents(self.source, self.snapshot, True, 2, "rs_cyrillic,en")
        self.assertTrue(result["documents"][0]["metadata"]["ocr_used"])
        self.assertEqual((self.snapshot / "raw/rules.txt").read_bytes(), expected.encode("utf-8"))

    def test_invalid_sizes_and_pdf_input_rejected(self):
        for size, overlap in [(0, 0), (-1, 0), (100, -1), (100, 100)]:
            with self.assertRaises(ValueError):
                SimpleChunker(size, overlap)
        with self.assertRaisesRegex(ValueError, "Missing extraction manifest"):
            chunk_documents(self.source, self.root / "chunks")
        with self.assertRaisesRegex(ValueError, "non-nested"):
            extract_documents(self.source, self.source / "snapshot")

    def test_index_consumes_only_verified_chunks_and_records_provenance(self):
        self.extract()
        chunks = self.root / "chunks"
        manifest = chunk_documents(self.snapshot, chunks, 512, 150)
        encoder = Mock(embedding_dim=3)
        store = Mock()
        fake_embedding = SimpleNamespace(SentenceTransformerEmbedding=Mock(return_value=encoder),
                                         FAISSVectorStore=Mock(return_value=store))
        with patch.dict(sys.modules, {"src.embedding": fake_embedding}), \
             patch("src.data.loaders.DocumentLoaderFactory.load_document", side_effect=AssertionError("No OCR")):
            index_documents(str(chunks), str(self.root / "index"), "test-model", "cpu", 2)
            result = read_manifest(self.root / "index", "indexing")
            self.assertEqual(result["chunk_count"], len(manifest["chunks"]))
            self.assertTrue(result["chunk_manifest_sha256"])
            self.assertEqual(store.add.call_args_list[0].args[1][0]["document"], "rules")
            (chunks / "unexpected_chunk0001.txt").write_text("stale", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "do not match"):
                index_documents(str(chunks), str(self.root / "index2"), "test-model", "cpu", 2)
        with self.assertRaisesRegex(ValueError, "raw or cleaned"):
            index_documents(str(self.snapshot / "cleaned"), str(self.root / "index3"), "test", "cpu", 2)


if __name__ == "__main__":
    unittest.main()


class StrategyChunkingFromSnapshotTests(unittest.TestCase):
    """Chunking strategies must reach the frozen-text path, not only the OCR path."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "documents"
        source.mkdir()
        body = ("Clan {n}.\n\nOdredba broj {n} propisuje uslove studiranja i "
                "polaganja ispita u toku skolske godine. " * 6 for n in range(1, 12))
        (source / "pravilnik.txt").write_text(
            "\n\n".join(text.format(n=i) for i, text in enumerate(body, start=1)),
            encoding="utf-8")
        self.snapshot = self.root / "snapshot"
        extract_documents(source, self.snapshot, enable_ocr=False)

    def test_hierarchical_chunking_needs_no_ocr_and_links_every_child(self):
        from src.data.stages import chunk_snapshot_with_strategy

        output = self.root / "chunks_hier"
        with patch("src.data.loaders.DocumentLoaderFactory.load_document",
                   side_effect=AssertionError("Must not load original documents")):
            manifest = chunk_snapshot_with_strategy(self.snapshot, output, "hierarchical")

        records = [json.loads(line) for line in
                   (output / "hierarchical" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
        parents = {r["chunk_id"] for r in records if r["level"] == "parent"}
        children = [r for r in records if r["level"] == "child"]

        self.assertEqual(manifest["settings"]["strategy"], "hierarchical")
        self.assertTrue(parents and children)
        self.assertTrue(all(c["parent_chunk_id"] in parents for c in children))
        self.assertEqual(manifest["chunk_count"], len(records))

    def test_process_documents_honours_strategy_on_a_snapshot(self):
        """Regression: --strategy used to be dropped for snapshot input."""
        from scripts.process_documents import process_documents

        output = self.root / "chunks_via_script"
        process_documents(input_dir=str(self.snapshot), output_dir=str(output),
                          strategy="hierarchical")

        self.assertTrue((output / "hierarchical" / "chunks.jsonl").is_file())
        levels = {json.loads(line)["level"] for line in
                  (output / "hierarchical" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()}
        self.assertIn("parent", levels)
