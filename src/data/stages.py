"""Persist extraction once, then build independent chunk sets from frozen text."""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from .document import Document
from .chunking import SimpleChunker
from .preprocessing import TextPreprocessor

logger = logging.getLogger(__name__)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hash(path):
    """Provenance hash for a module file, or for every .py in a package.

    ``chunking`` became a package when chunking turned into pluggable
    strategies, so the implementation fingerprint has to cover the whole
    directory rather than a single module.
    """
    path = Path(path)
    if not path.is_dir():
        return file_hash(path)
    digest = hashlib.sha256()
    for source in sorted(path.rglob("*.py")):
        digest.update(source.relative_to(path).as_posix().encode("utf-8"))
        digest.update(source.read_bytes())
    return digest.hexdigest()


def prepare_output(input_dir, output_dir):
    source, target = Path(input_dir).resolve(), Path(output_dir).resolve()
    if not source.is_dir():
        raise ValueError(f"Input directory does not exist: {source}")
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("Input and output directories must be separate, non-nested directories.")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError(f"Output must be a new or empty directory: {target}")
    return source, target


def write_manifest(directory, manifest):
    path = Path(directory) / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_manifest(directory, stage):
    path = Path(directory) / "manifest.json"
    if not path.is_file():
        raise ValueError(f"Missing {stage} manifest: {path}. Run the preceding stage first.")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("stage") != stage:
        raise ValueError(f"Expected a version 1 {stage} manifest: {path}")
    return manifest


def verified_file(directory, relative_path, expected_hash):
    root = Path(directory).resolve()
    path = (root / relative_path).resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError(f"Invalid artifact path: {relative_path}")
    if file_hash(path) != expected_hash:
        raise ValueError(f"Artifact changed since its manifest was written: {path}")
    return path


def extract_documents(input_dir, output_dir, enable_ocr=True, ocr_max_pages=None,
                      ocr_languages=None):
    """Save raw and cleaned text using the existing loader/OCR behavior."""
    from .loaders import DocumentLoaderFactory
    from .ocr import DEFAULT_OCR_LANGUAGES

    source, target = prepare_output(input_dir, output_dir)
    if ocr_max_pages is not None and ocr_max_pages <= 0:
        raise ValueError("ocr_max_pages must be positive")
    files = sorted(p for p in source.rglob("*")
                   if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".doc", ".txt"})
    if not files:
        raise ValueError(f"No supported documents found in {source}")
    stems = [p.stem.casefold() for p in files]
    if len(stems) != len(set(stems)):
        raise ValueError("Document names must have unique stems to preserve chunk filenames.")

    options = {
        "ETF_RAG_ENABLE_OCR": "1" if enable_ocr else "0",
        "ETF_RAG_OCR_MAX_PAGES": str(ocr_max_pages) if ocr_max_pages else None,
        "ETF_RAG_OCR_LANGUAGES": ocr_languages or None,
    }
    previous = {key: os.environ.get(key) for key in options}
    records = []
    target.mkdir(parents=True, exist_ok=True)
    (target / "raw").mkdir()
    (target / "cleaned").mkdir()
    try:
        for key, value in options.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for path in files:
            logger.info("Extracting: %s", path.name)
            source_hash = file_hash(path)
            document = DocumentLoaderFactory.load_document(str(path))
            cleaned = TextPreprocessor().clean(document.text)
            if not cleaned:
                raise ValueError(f"No usable text extracted from {path}; snapshot is incomplete.")
            if file_hash(path) != source_hash:
                raise ValueError(f"Source changed during extraction: {path}")
            raw_path = target / "raw" / f"{path.stem}.txt"
            cleaned_path = target / "cleaned" / f"{path.stem}.txt"
            raw_path.write_bytes(document.text.encode("utf-8"))
            cleaned_path.write_bytes(cleaned.encode("utf-8"))
            records.append({
                "document": path.stem, "source": path.relative_to(source).as_posix(),
                "source_sha256": source_hash, "metadata": document.metadata,
                "raw_file": raw_path.relative_to(target).as_posix(),
                "raw_sha256": file_hash(raw_path),
                "cleaned_file": cleaned_path.relative_to(target).as_posix(),
                "cleaned_sha256": file_hash(cleaned_path),
                "raw_chars": len(document.text), "cleaned_chars": len(cleaned),
            })
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    manifest = {
        "schema_version": 1, "stage": "extraction",
        "created_at": datetime.now(timezone.utc).isoformat(), "input_directory": str(source),
        "settings": {"enable_ocr": enable_ocr, "ocr_max_pages": ocr_max_pages,
                     "ocr_languages": ocr_languages or ",".join(DEFAULT_OCR_LANGUAGES),
                     "ocr_policy": "fallback_if_entire_pdf_has_no_text"},
        "implementation_sha256": {name: file_hash(Path(__file__).with_name(name))
                                  for name in ("loaders.py", "ocr.py", "preprocessing.py")},
        "documents": records,
    }
    # Publish only after every document succeeds; incomplete snapshots cannot be chunked.
    write_manifest(target, manifest)
    logger.info("Saved %s documents to %s. Subsequent chunking does not run OCR.", len(records), target)
    return manifest


def chunk_documents(input_dir, output_dir, chunk_size=1024, overlap=150):
    """Split frozen cleaned text without loading original documents or running OCR."""
    source, target = prepare_output(input_dir, output_dir)
    chunker = SimpleChunker(chunk_size=chunk_size, overlap=overlap)
    snapshot = read_manifest(source, "extraction")
    if not snapshot.get("documents"):
        raise ValueError("Extraction snapshot contains no documents")
    pending = []
    for record in snapshot["documents"]:
        path = verified_file(source, record["cleaned_file"], record["cleaned_sha256"])
        document = Document(path.read_bytes().decode("utf-8"), record["metadata"])
        chunks = chunker.split(document)
        if not chunks:
            raise ValueError(f"No chunks produced for {record['document']}")
        for index, chunk in enumerate(chunks):
            name = f"{record['document']}_chunk{index:04d}.txt"
            if Path(name).name != name or "/" in name or "\\" in name:
                raise ValueError(f"Invalid document name: {record['document']}")
            pending.append((name, chunk.text, record["document"], index))
    if len({name.casefold() for name, *_ in pending}) != len(pending):
        raise ValueError("Duplicate chunk filenames in snapshot")
    target.mkdir(parents=True, exist_ok=True)
    records = []
    for name, text, document, index in pending:
        path = target / name
        path.write_bytes(text.encode("utf-8"))
        records.append({"file": name, "sha256": file_hash(path), "chars": len(text),
                        "document": document, "chunk_id": index})
    manifest = {
        "schema_version": 1, "stage": "chunking",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_directory": str(source),
        "snapshot_manifest_sha256": file_hash(source / "manifest.json"),
        "settings": {"strategy": "fixed_characters", "chunk_size": chunk_size, "overlap": overlap},
        "implementation_sha256": tree_hash(Path(__file__).with_name("chunking")),
        "chunks": records,
    }
    write_manifest(target, manifest)
    logger.info("Saved %s chunks to %s", len(records), target)
    return manifest
