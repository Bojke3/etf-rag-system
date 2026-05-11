# Research Notes - ETF RAG System

## 📚 Literature Review

### RAG Systems

#### Ključne Reference
- **Title**: Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
- **Authors**: Lewis et al., 2020
- **Link**: https://arxiv.org/abs/2005.11401
- **Key Points**:
  - Kombinovanje retrieval-a sa generation-om
  - Poboljšanje nad baseline fine-tuning pristupima
  - Fleksibilnost bez fine-tuning-a

### Embedding Modeli

#### Sentence Transformers
- **Link**: https://www.sbert.net/
- **Modeli za razmatranje**:
  - `all-MiniLM-L6-v2` - Brz, mali (22MB)
  - `all-mpnet-base-v2` - Bolji, ali veći (438MB)
  - `multilingual-e5-base` - Za više jezika

### LLM Modeli

#### Dostupni preko Ollama

| Model | Veličina | Speed | Quality | Link |
|-------|---------|-------|---------|------|
| Llama 2 | 7B, 13B, 70B | Medium | High | https://ollama.ai/library/llama2 |
| Mistral | 7B | Fast | High | https://ollama.ai/library/mistral |
| Neural-Chat | 7B | Fast | Medium | https://ollama.ai/library/neural-chat |
| Deepseek | 7B, 33B | Medium | High | https://ollama.ai/library/deepseek |
| Qwen | 7B, 14B | Medium | High | https://ollama.ai/library/qwen |

### Evaluation Metrike

#### Token-based Metrike

**BLEU (Bilingual Evaluation Understudy)**
- Poredi n-grame sa referentnim odgovorom
- Raspon: 0-1
- Problem: Nije senzitivan na sinonime

```python
from nltk.translate.bleu_score import sentence_bleu
reference = ['this', 'is', 'a', 'test']
candidate = ['this', 'is', 'test']
score = sentence_bleu([reference], candidate)
```

**ROUGE (Recall-Oriented Understudy for Gisting Evaluation)**
- Fokus na recall
- ROUGE-1: Unigrams
- ROUGE-2: Bigrams
- ROUGE-L: Longest Common Subsequence

```python
from rouge_score import rouge_scorer
scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'])
score = scorer.score(reference, candidate)
```

#### Semantic Metrike

**BERTScore**
- Koristi kontekstne reprezentacije
- Bolje hvata semantiku
- Težinski comparison

```python
from bert_score import score
P, R, F1 = score([candidate], [reference], lang='en')
```

**LLM as a Judge**
- Koristi LLM da oceni kvalitet
- Fleksibilan, može se prilagoditi
- Problem: Skupo, sporo

### Prompt Engineering

#### Zero-Shot
```
Question: {question}
Context: {context}
Answer:
```

#### Few-Shot
```
Example 1:
Question: ...
Answer: ...

Example 2:
Question: ...
Answer: ...

Now answer this:
Question: {question}
Answer:
```

#### Chain-of-Thought
```
Let's think through this step by step.

Question: {question}
Context: {context}

Step 1: Identify key information
...
Step 2: Reason through the problem
...
Final Answer: ...
```

## 🔬 Eksperimentalni Plan

### Faza 1: Model Selection (Juni 2026)

**Cilj**: Pronaći najbolji par (embedding model, LLM model)

#### Eksperimenti

1. **Embedding Model Comparison**
   - Test: top-5 retrieval accuracy
   - Modeli: MiniLM, MPNet, E5
   - Dataset: ~20 test queries

2. **LLM Model Comparison**
   - Test: answer quality (human eval, BLEU, ROUGE)
   - Modeli: Llama2, Mistral, Qwen
   - Dataset: 50 queries

### Faza 2: Prompt Engineering (Juli 2026)

**Cilj**: Pronaći optimalnu prompt strategiju

#### Eksperimenti

1. **Zero-Shot vs Few-Shot vs CoT**
   - Metrika: F1 score, human evaluation
   - Dataset: 100 queries
   - Time measurement

2. **Prompt Templates Optimization**
   - Testiranje različitih formulacija
   - Fokus na razumevanje konteksta

### Faza 3: Retrieval Optimization (Juli 2026)

**Cilj**: Poboljšati relevantnost preuzimanja

#### Eksperimenti

1. **Chunking Strategy**
   - Test: Različite veličine chunks (256, 512, 1024)
   - Overlap: 0%, 20%, 50%
   - Metrika: Recall@5, Recall@10

2. **Reranking**
   - Base: No reranking
   - Reranker: Cross-encoder
   - Metrika: MRR, NDCG

### Faza 4: Multi-Document Retrieval (August 2026)

**Cilj**: Testiranje na queries koje zahtevaju više dokumenata

## 📊 Benchmark Dataset

### Single Document QA (Minimalno 30 queries)

```json
{
  "id": "single_doc_001",
  "question": "Koja je trajanje osnovnih studija?",
  "answer": "Osnovne studije traju 4 godine.",
  "source_document": "study_program_2024.pdf",
  "source_page": 5,
  "difficulty": "easy"
}
```

### Multi-Document QA (Minimalno 20 queries)

```json
{
  "id": "multi_doc_001",
  "question": "Koje su razlike između master i doktorskih studija?",
  "answer": "Master studije traju 1-2 godine i focus na specijalizaciju, dok doktorske studije traju 3+ godine sa istraživanjem.",
  "source_documents": ["master_program.pdf", "phd_program.pdf"],
  "difficulty": "medium"
}
```

## 💡 Ključne Istraživačke Pitanja

1. **Q1**: Koji embedding model daje najbolje retrieval rezultate za srpske dokumente?
2. **Q2**: Koja kombinacija (model + prompt strategija) daje best balance između broja (speed) i kvaliteta?
3. **Q3**: Koliko dodatnog konteksta poboljšava odgovore (1 vs 5 dokumenata)?
4. **Q4**: Kako skenirani dokumenti (OCR) utiču na kvalitet sistema?
5. **Q5**: Koja metrika je best za automatsku evaluaciju bez ljudske intervencije?

## 📈 Očekivani Rezultati

### Za TELFOR 2026

- MVP sa 85%+ accuracy na single-document queries
- 70%+ accuracy na multi-document queries
- Response time < 2 sekunde
- Minimalno 3 različita chatbot interfejsa (Web, Telegram, Discord)

### Za Konferencijsku Publikaciju

- Poređenje embedding modela
- Evaluacija prompt strategija
- Benchmark dataset za buduća istraživanja
- Open-source codebase

## 🔗 Relevantne Konferencije

- **TELFOR 2026** - Rok: Sept 4, 2026
- **ACL 2026** - NLP conference
- **EMNLP 2026** - NLP conference
- **Lokalne konferencije** - CIT.AC.RS

## 📝 Zapisane Ideje

- [ ] Istraži hybrid search (BM25 + semantic)
- [ ] Istraži query expansion tehnike
- [ ] Razmotri graph-based retrieval
- [ ] Istraži multi-modal retrieval (text + images)
- [ ] Razmotri personalizovane odgovore po studenoj godini

## 🎯 Dalji Razvoj

### Post MVP

1. **Fine-tuning LLM** na faktima o fakultetu
2. **Knowledge Graph** iz fakultetske dokumentacije
3. **Real-time feedback** loop za bolji odgovore
4. **User-specific contexts** (nastavnika, studenata, administratora)
5. **Integration sa fakultetskim sistemima** (AMIS, itd)
