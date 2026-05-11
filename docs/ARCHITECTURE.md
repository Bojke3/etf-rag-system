# ETF RAG System - Architecture

## Pregled

ETF RAG System je dizajniran kao modularna arhitektura sa jasnom separacijom briga (separation of concerns). Svaki sloj je nezavisan i može biti razvijan, testiran i unapređen odvojeno.

## 🏗️ Slojevi Arhitekture

```
┌─────────────────────────────────────────────────────────────┐
│                     CHATBOT/WEB LAYER                        │
│         (Web UI, Telegram, Discord, WhatsApp)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    AGENT/ORCHESTRATION                       │
│        (Conversation Management, State)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    RAG PIPELINE                              │
│    (Query → Retrieval → Context → LLM → Answer + Citations) │
└──────────────────────────┬──────────────────────────────────┘
                           │
      ┌────────────────────┼────────────────────┐
      │                    │                    │
┌─────▼──────┐      ┌──────▼────────┐    ┌────▼──────────┐
│ RETRIEVAL   │      │   LLM LAYER    │    │  EVALUATION   │
│  LAYER      │      │                │    │   LAYER       │
└─────┬──────┘      └──────┬────────┘    └────┬──────────┘
      │                    │                  │
┌─────▼──────────────┬─────▼─────────────┬───▼──────────┐
│  EMBEDDING LAYER   │  PROMPT LAYER    │  METRICS     │
│                    │                  │              │
│ - Vector Store     │ - Prompt Templ.  │ - BLEU       │
│ - Reranking        │ - Strategies     │ - ROUGE      │
│ - Similarity       │   (0-shot, few)  │ - LLM Judge  │
└─────┬──────────────┴─────┬────────────┴──┬───────────┘
      │                    │               │
┌─────▼────────────────────▼───────────────▼──────────────┐
│                    DATA LAYER                            │
│         (PDF/Word Extraction, Preprocessing)            │
└───────────────────────────────────────────────────────────┘
```

## 📊 Detaljni Opis Slojeva

### 1. **Data Layer** (`src/data/`)

**Odgovoran za:**
- Učitavanje dokumenata (PDF, Word)
- Ekstrakciju teksta
- Preprocessing (čišćenje, normalizacija)
- Chunking (deljenje na smislene segmente)

**Key Components:**
```python
- DocumentLoader: Opšta interfejsa
- PDFExtractor: PDF specifičan
- WordExtractor: Word specifičan
- TextPreprocessor: Čišćenje teksta
- ChunkingStrategy: Deljenje na chunks
- OCRHandler: Za skenirane dokumente (future)
```

### 2. **Embedding Layer** (`src/embedding/`)

**Odgovoran za:**
- Pretvaranje teksta u vektorske reprezentacije
- Upravljanje vector store-om
- Indeksiranje dokumenata

**Key Components:**
```python
- EmbeddingModel: Wrapper oko sentence-transformers
- VectorStore: Abstract klasa
- FAISSVectorStore: FAISS implementacija
- PineconeVectorStore: Pinecone implementacija
```

### 3. **Retrieval Layer** (`src/retrieval/`)

**Odgovoran za:**
- Pronalaženje relevantnih dokumenata
- Reranking rezultata
- Gradnja konteksta

**Key Components:**
```python
- BaseRetriever: Opšta interfejsa
- SimpleRetriever: Bazna pretraga
- HybridRetriever: Kombinovana pretraga
- Reranker: Ponovno rangiranje rezultata
- ContextBuilder: Pravljenje konteksta
```

### 4. **LLM Layer** (`src/llm/`)

**Odgovoran za:**
- Komunikacija sa lokalnim i cloud LLM-ima
- Upravljanje prompt šablonima
- Implementacija prompt strategija

**Key Components:**
```python
- BaseLLMClient: Abstract klasa
- OllamaClient: Lokalni modeli
- HuggingFaceClient: HF modeli
- PromptTemplate: Šabloni za prompte
- PromptStrategy: Zero-shot, Few-shot, CoT
```

### 5. **RAG Pipeline** (`src/rag/`)

**Odgovoran za:**
- Orkestracija svih slojeva
- Kombinovanje retrievala i LLM-a
- Upravljanje citacijama

**Key Components:**
```python
- RAGPipeline: Glavna orkestracija
- AnswerGenerator: Generisanje odgovora
- CitationManager: Upravljanje izvorima
```

### 6. **Evaluation Layer** (`src/evaluation/`)

**Odgovoran za:**
- Ocenu kvalitete odgovora
- Izračunavanje metrika
- Benchmark testiranje

**Key Components:**
```python
- MetricCalculator: BLEU, ROUGE, itd
- LLMJudge: LLM kao evaluator
- BenchmarkDataset: Test setovi
- Evaluator: Glavna evaluaciona logika
```

### 7. **Chatbot/Agent Layer** (`src/chatbot/`)

**Odgovoran za:**
- Upravljanje konverzacijom
- Različitim interfejsima (Web, Telegram, Discord)
- State management

**Key Components:**
```python
- BaseAgent: Abstract agent
- ConversationManager: Upravljanje konverzacijom
- WebInterface: Flask/FastAPI
- TelegramBot: Telegram specifičan
- DiscordBot: Discord specifičan
```

## 🔄 Data Flow

### Scenario 1: Indexiranje Dokumenata

```
PDF/Word dokument
        ↓
    DocumentLoader
        ↓
    TextPreprocessor
        ↓
    ChunkingStrategy
        ↓
    EmbeddingModel
        ↓
    VectorStore (FAISS/Pinecone)
```

### Scenario 2: Pronalaženje Odgovora

```
Korisničko pitanje
        ↓
    QueryEmbedding
        ↓
    SimpleRetriever (Top-k dokumenti)
        ↓
    Reranker (Filtriranje relevantnih)
        ↓
    ContextBuilder (Spajanje u kontekst)
        ↓
    PromptTemplate (Pravljenje prompta)
        ↓
    LLMClient (Ollama/HF)
        ↓
    Answer + CitationManager
        ↓
    Korisnik
```

## 🎯 Design Patterns

### 1. **Strategy Pattern**
- `PromptStrategy` - Različite strategije za prompting
- `ChunkingStrategy` - Različiti načini deljenja teksta
- `EmbeddingStrategy` - Različiti embedding modeli

### 2. **Factory Pattern**
- `VectorStoreFactory` - Pravljenje različitih vector store-a
- `LLMClientFactory` - Pravljenje različitih LLM klijenta
- `RetrieverFactory` - Pravljenje različitih retrievera

### 3. **Observer Pattern**
- Konverzacioni moduli prate stanje agenta

### 4. **Pipeline Pattern**
- RAG Pipeline kao serija koraka

## 📦 Dependencies

```
etf-rag-system/
├── src/data/          ← Nema zavisnosti od ostalih modula
├── src/embedding/     ← Zavisi od data/
├── src/retrieval/     ← Zavisi od embedding/
├── src/llm/           ← Nema zavisnosti od ostalih
├── src/rag/           ← Zavisi od retrieval/, llm/
├── src/evaluation/    ← Zavisi od rag/
└── src/chatbot/       ← Zavisi od rag/
```

## 🔌 Integracije Trećih Strana

### LLM-ovi
- **Ollama** (lokalno)
- **HuggingFace** (cloud/lokalno)
- **OpenAI** (cloud)

### Vector Stores
- **FAISS** (lokalno)
- **Pinecone** (cloud)
- **Chroma** (lokalno)

### Chatbot Platforme
- **Web** (Flask/FastAPI)
- **Telegram** (python-telegram-bot)
- **Discord** (discord.py)
- **WhatsApp** (Twilio)

## 🚀 Skalabilnost

### Horizontalna Skalabilnost
- Vector Store može biti zamenjiv (FAISS → Pinecone)
- LLM client može biti zamenjiv (Ollama → OpenAI)

### Vertikalna Skalabilnost
- Caching sloja može biti dodan
- Load balancing za web aplikaciju
- Async/await za performance

## 📈 Budući Razvoj

1. **OCR Layer** - Za skenirane dokumente
2. **Cache Layer** - Za brže odgovore
3. **API Gateway** - Za centralizovanu kontrolu
4. **Monitoring** - Za praćenje performansi
5. **Multi-language** - Podrška za više jezika
