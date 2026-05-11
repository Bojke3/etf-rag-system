# ETF RAG System - Faculty Documentation Search

> Sistem za pretragu i korišćenje interne dokumentacije Elektrotehničkog fakulteta korišćenjem RAG (Retrieval-Augmented Generation) pristupa sa lokalnim LLM modelima.

## 🎯 Cilj Projekta

Razvojiti inteligentni AI Bot sistem koji omogućava:
- **Semantičku pretragu** preko interne dokumentacije fakulteta
- **Direktne odgovore** na studentska pitanja sa referencama na izvore
- **Podršku za više dokumenata** pri generisanju odgovora
- **Lokalno izvršavanje** korišćenjem Ollama i open-source modela

## 📚 Faza 1: MVP

### Fokus
- PDF i Word dokumenti (osnovne, master i doktorske studije)
- Ekstrakcija iz jednog i više dokumenata
- Zero-shot i few-shot prompting strategije
- Lokalni modeli (Ollama)

### Ciljane Konferencije
- **TELFOR 2026** - Rok: 4. septembar 2026

## 🏗️ Arhitektura

```
Documents → Preprocessing → Embeddings → Vector Store
                                            ↓
User Query → Retrieval → Context → LLM → Answer + Citations
```

## 🚀 Quick Start

```bash
# 1. Kloniranje
git clone https://github.com/Bojke3/etf-rag-system.git
cd etf-rag-system

# 2. Instalacija
python -m venv venv
source venv/bin/activate  # na Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Setup Ollama modela
bash scripts/setup_ollama_models.sh

# 4. Procesiranje dokumenata
python scripts/process_documents.py

# 5. Pokretanje web aplikacije
python web/app.py
```

## 📁 Struktura Projekta

Dokumenti sa struktuom projekta: [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 📊 Komponente

### 1. **Data Layer** (`src/data/`)
- Ekstraktori za PDF i Word dokumente
- Preprocessing i čišćenje teksta
- Chunking strategije
- OCR layer (budućnost)

### 2. **Embedding & Retrieval** (`src/embedding/`, `src/retrieval/`)
- Embedding modeli (sentence-transformers)
- Vector store integracije (FAISS, Pinecone)
- Smart retrieval i reranking

### 3. **LLM Integration** (`src/llm/`)
- Ollama client
- HuggingFace integracija
- Prompt engineering strategije

### 4. **RAG Pipeline** (`src/rag/`)
- Kombinovanje retrievala i LLM-a
- Upravljanje kontekstom
- Generisanje citacija

### 5. **Evaluacija** (`src/evaluation/`)
- BLEU, ROUGE metrike
- LLM as a Judge
- Benchmark setovi

### 6. **Chatbot/Agent** (`src/chatbot/`)
- Web interfejs (Flask/FastAPI)
- Telegram bot
- Discord bot
- WhatsApp bot (Twilio)

## 🧪 Testiranje

```bash
# Pokretanje testova
pytest tests/ -v

# Sa pokrajinom
pytest tests/ --cov=src
```

## 📖 Dokumentacija

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Detaljnija arhitektura
- [SETUP.md](docs/SETUP.md) - Detaljne instalacijske instrukcije
- [RESEARCH.md](docs/RESEARCH.md) - Rezultati istraživanja
- [BENCHMARKING.md](docs/BENCHMARKING.md) - Benchmark rezultati
- [API_DOCS.md](docs/API_DOCS.md) - API dokumentacija

## 🔄 Development Process

1. **Research Sprint** - Izbor modela i tehnika
2. **MVP Sprint** - Osnovni RAG sistem
3. **Evaluation Sprint** - Benchmarking
4. **Deployment Sprint** - Chatbot integracije
5. **Publication Sprint** - Konferencijski radovi

## 👥 Tim

- **Project Lead**: Marko Šošić (Profesor)
- **Researchers**: [Dodaj imena članova tima]

## 📅 Timeline

- **Maj 2026**: Architecture & Planning ✅
- **Jun-Jul 2026**: MVP Development
- **Aug 2026**: Testing & Optimization
- **Sep 2026**: TELFOR Conference

## 📝 License

MIT License - vidi [LICENSE](LICENSE) fajl

## 📞 Kontakt

Za pitanja ili sugestije, otvorite [GitHub Issue](https://github.com/Bojke3/etf-rag-system/issues)
