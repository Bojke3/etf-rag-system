# ETF RAG System — Progress & Status

## Project Structure

```
etf-rag-system/
├── DataAkti/                          # 7 PDF dokumenata ETF pravilnika
├── benchmarking/
│   └── OAS_prec_23_benchmark.json     # 60 Q&A parova za evaluaciju
├── data/
│   └── processed/                     # Chunk .txt fajlovi (gitignored)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── OCR.md                         # Dokumentacija za OCR setup
│   └── ...
├── models/
│   └── vectorstore/                   # FAISS index fajlovi (gitignored)
├── scripts/
│   ├── index_documents.py             # Embedduje chunkove → FAISS index
│   ├── process_documents.py           # PDF → chunk .txt fajlovi (sa OCR fallbackom)
│   └── setup_ollama_models.sh         # Preuzima Ollama modele
├── src/
│   ├── config.py                      # Pydantic config, čita .env
│   ├── constants.py                   # Spisak podržanih embedding modela
│   ├── data/
│   │   ├── chunking.py                # SimpleChunker — deli Document na Chunk liste
│   │   ├── document.py                # Document dataclass (text + metadata)
│   │   ├── loaders.py                 # PDF/Word/Text loaderi, OCR fallback
│   │   ├── ocr.py                     # OCRHandler — easyocr + PyMuPDF za skenove
│   │   └── preprocessing.py          # TextPreprocessor — čisti whitespace/newlines
│   ├── embedding/
│   │   └── __init__.py                # SentenceTransformerEmbedding + FAISSVectorStore
│   ├── llm/
│   │   └── __init__.py                # OllamaClient + PromptTemplate (zero/few/CoT)
│   ├── rag/
│   │   └── __init__.py                # RAGPipeline — retrieve → prompt → generate
│   ├── retrieval/
│   │   └── __init__.py                # SimpleRetriever + ContextBuilder
│   ├── evaluation/
│   │   └── __init__.py                # (stub) BLEU, ROUGE, LLM-as-Judge
│   └── chatbot/
│       └── __init__.py                # (stub) Telegram/Discord/WhatsApp
├── web/
│   └── app.py                         # Flask REST API (GET /, POST /query)
├── tests/
│   ├── conftest.py
│   ├── test_document_loader.py
│   └── test_embedding.py
├── main.py                            # Demo skripta — štampa prvih 3 chunka po dokumentu
├── test_structure.py                  # Brza provera da se sve importuje
├── .env                               # Lokalna konfiguracija (gitignored)
├── .env.example                       # Template za .env
└── requirements.txt
```

---

## Šta Radi / Šta Ne Radi

### Radi
- **Document loading** — `src/data/loaders.py` čita PDF, Word i .txt fajlove
- **Preprocessing** — `TextPreprocessor` čisti srpski tekst (whitespace, newlines)
- **Chunking** — `SimpleChunker` deli tekst na overlapping chunkove
- **Embedding** — `SentenceTransformerEmbedding` sa multilingual modelom
- **FAISS vector store** — čuvanje i učitavanje indeksa
- **Retrieval** — kosinusna sličnost sa threshold filterom
- **LLM client** — `OllamaClient` komunicira sa lokalnim Ollama serverom
- **Prompt engineering** — zero-shot, few-shot, chain-of-thought strategije
- **Flask API** — `POST /query` vraća odgovor + izvore + metrike vremena
- **OCR handler** — `OCRHandler` koristi easyocr + PyMuPDF za skenirana PDF-ova
- **Config sistem** — sve se čita iz `.env` via Pydantic BaseSettings

### Ne Radi / Nije Završeno
- **FAISS index nije rebuild-ovan** — trenutno sadrži samo 2 stara test chunka
- **6 od 7 PDF-ova nisu procesirana** — skenirana su, OCR još nije pokrenut
- **Web server nije testiran** — nikad pokrenut sa pravim podacima
- **Evaluacija** — `src/evaluation/` je stub, benchmark skripta ne postoji
- **Chatbot integracije** — `src/chatbot/` je prazan stub
- **`.env` ima pogrešan model** — `OLLAMA_MODEL=mistral`, ali mistral nije instaliran

---

## Zavisnosti i Pokretanje

### Preduslovi

```bash
# Python 3.10+
python3 --version

# Ollama
ollama --version
```

### Instalacija

```bash
git clone https://github.com/Bojke3/etf-rag-system.git
cd etf-rag-system

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Konfiguracija

Kopiraj `.env.example` → `.env` i podesi:

```env
OLLAMA_MODEL=qwen2.5:3b
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
DATA_DIR=./DataAkti
CHUNK_SIZE=1024
CHUNK_OVERLAP=150
RETRIEVAL_THRESHOLD=0.5
VECTOR_STORE_PATH=./models/vectorstore
PROCESSED_DATA_DIR=./data/processed
```

### Pokretanje

```bash
# 1. Procesiranje dokumenata (sa OCR za skenove)
python scripts/process_documents.py \
  --input DataAkti \
  --output data/processed \
  --chunk-size 1024 \
  --overlap 150 \
  --ocr-languages rs_cyrillic,en

# 2. Kreiranje FAISS indeksa
python scripts/index_documents.py

# 3. Pokretanje web servera
python web/app.py

# 4. Test upit
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Када почиње школска година на Факултету?", "top_k": 5}'
```

---

## Sledeći Koraci (Po Prioritetu)

### 1. Update `.env` — promeniti LLM model
```
OLLAMA_MODEL=qwen2.5:3b
```

### 2. Instalirati nove zavisnosti (Andrija dodao easyocr i PyMuPDF)
```bash
pip install -r requirements.txt
```

### 3. OCR procesiranje skeniranih PDF-ova
Pokrenuti `process_documents.py` sa OCR flagom. EasyOCR će preuzeti modele
(~500MB) pri prvom pokretanju i procesirati ~1-2 min/stranica na CPU-u.

### 4. Rebuild FAISS indeksa
Trenutni indeks ima samo 2 placeholder chunka. Rebuild sa pravim podacima.

### 5. End-to-end test web servera
Pokrenuti `web/app.py` i testirati pitanje iz benchmark dataseta.

### 6. Napisati benchmark skriptu
Automatski prolaz kroz `benchmarking/OAS_prec_23_benchmark.json` — upoređivanje
generisanih odgovora sa `expected_answer` koristeći ROUGE/semantic similarity.

### 7. Evaluacija kvaliteta OCR-a
Ručno proveriti par chunk fajlova iz skeniranih PDF-ova — easyocr za ćirilicu
nije savršen, može biti grešaka.

---

## Poznati Problemi i Bagovi

| Problem | Status | Rešenje |
|---------|--------|---------|
| `.env` ima `OLLAMA_MODEL=mistral` ali mistral nije instaliran | Otvoreno | Promeniti na `qwen2.5:3b` |
| FAISS index sadrži samo 2 test chunka | Otvoreno | Pokrenuti `index_documents.py` |
| 6/7 PDF-ova su skenirana — pypdf ne može da izvuče tekst | Otvoreno | Pokrenuti OCR processing |
| `src/evaluation/__init__.py` je prazan stub | Otvoreno | Implementirati ROUGE metriku |
| `easyocr` OCR kvalitet za ćirilicu može biti slab | Nepoznato | Proveriti posle pokretanja |

---

## Status Modela

| Model | Veličina | Status | Napomena |
|-------|----------|--------|---------|
| `qwen2.5:3b` (Ollama) | 1.9 GB | **Instaliran** | Primarni LLM za testiranje |
| `mistral` (Ollama) | 4.4 GB | **Nije instaliran** | Download prekinut, pokrenuti: `ollama pull mistral` |
| `paraphrase-multilingual-MiniLM-L12-v2` | ~470 MB | **Keširan** | `~/.cache/huggingface/hub/` |
| `all-MiniLM-L6-v2` | ~90 MB | **Keširan** | Engleski model, ne koristimo |

---

## Status Benchmark Dataseta

**Fajl:** `benchmarking/OAS_prec_23_benchmark.json`

- **60 pitanja/odgovora** iz `Pravilnik_o_OAS_preciscen_jun_2023.pdf`
- Format: `id`, `type`, `difficulty`, `question`, `expected_answer`, `source_document`, `source_section`
- Tipovi: `single_chunk` (jedno poglavlje), potencijalno `multi_chunk` (više poglavlja)
- Težine: `easy`, `medium`, `hard`
- **Benchmark skripta ne postoji** — treba je napisati

---

## Tim

- **Vuk Bojovic** — setup, konfiguracija, retrieval pipeline, chunking
- **Andrija Trnavcevic** — `src/data/` refaktor, OCR integracija (`easyocr` + `PyMuPDF`)

## Rok

**TELFOR 2026** — 4. septembar 2026
