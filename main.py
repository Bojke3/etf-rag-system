from pathlib import Path

from src.data import (
    DocumentLoaderFactory,
    TextPreprocessor,
    SimpleChunker,
)

preprocessor = TextPreprocessor()
chunker = SimpleChunker(
    chunk_size=1000,
    overlap=200,
)

pdf_paths = sorted(Path("DataAkti").glob("*.pdf"))

if not pdf_paths:
    raise FileNotFoundError("No PDF files found in DataAkti")

all_chunks = []

for pdf_path in pdf_paths:
    document = DocumentLoaderFactory.load_document(str(pdf_path))
    document.text = preprocessor.clean(document.text)

    chunks = chunker.split(document)
    all_chunks.extend(chunks)

    print(f"Dokument: {pdf_path.name}")
    print(f"Broj chunkova: {len(chunks)}")

    for chunk in chunks[:3]:
        print("=" * 50)
        print(chunk.text[:300])
        print(chunk.metadata)

    print()

print(f"Ukupan broj dokumenata: {len(pdf_paths)}")
print(f"Ukupan broj chunkova: {len(all_chunks)}")
