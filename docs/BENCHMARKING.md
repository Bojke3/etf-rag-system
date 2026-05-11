# Benchmarking Framework

## 📊 Overview

Ovaj dokument opisuje framework za sistemsko testiranje i poređenje različitih komponenti ETF RAG sistema.

## 🎯 Benchmark Categories

### 1. Retrieval Benchmarks

**Cilj**: Ocena kvalitete pronalaženja relevantnih dokumenata

#### Metrike
- **Recall@k**: Procenat relevantnih dokumenata u top-k rezultata
- **Precision@k**: Procenat relevantnih u top-k
- **MRR (Mean Reciprocal Rank)**: Gde se prvi relevantni dokument nalazi
- **NDCG (Normalized Discounted Cumulative Gain)**: Rangiranje kvalitete

#### Test Set
- 50 queries
- 3 relevantna dokumenta po query
- Mix od easy/medium/hard queries

### 2. Generation Benchmarks

**Cilj**: Ocena kvalitete generisanog odgovora

#### Metrike

**BLEU Score**
```
Score: 0-1
Interp: > 0.5 je dobar
Problem: Ne hvata sinonime
```

**ROUGE Scores**
```
ROUGE-1 (unigrams): 0-1
ROUGE-2 (bigrams): 0-1
ROUGE-L (longest common subseq): 0-1
```

**BERTScore**
```
P, R, F1: 0-1
Bolji za semantičku sličnost
```

**LLM-as-Judge**
```
Score: 1-5
Kriterijumi: Accuracy, Relevance, Completeness
```

#### Test Set
- 100 queries
- Reference answers sa dokumentima
- Mix: single-doc (70%), multi-doc (30%)

### 3. Speed Benchmarks

**Cilj**: Ocena brzine sistema

#### Metrike
- **Retrieval latency**: Vreme pretraživanja
- **Generation latency**: Vreme generisanja odgovora
- **E2E latency**: Celo vreme user query → answer
- **Throughput**: Queries po sekundi

#### Test Set
- 50 queries
- Mereno 5 puta (prosek)

### 4. Resource Benchmarks

**Cilj**: Ocena resursa potrebnih

#### Metrike
- **Memory usage**: RAM potreban
- **CPU usage**: CPU procenat
- **Disk space**: Prostor potreban za modele
- **Network bandwidth** (ako cloud)

## 🧪 Eksperimentalni Setup

### Hardware

```
CPU: Intel i7/Ryzen 7 (8 cores minimum)
RAM: 16GB (32GB recommended)
Storage: SSD 256GB minimum
GPU: Optional (NVIDIA 3070+ recommended)
OS: Linux/Windows/Mac
```

### Software

```
Python 3.10+
Ollama latest
Docker (optional)
Jupyter (for analysis)
```

## 📈 Benchmark Results Template

### Retrieval Results

```
Embedding Model: sentence-transformers/all-MiniLM-L6-v2
Vector Store: FAISS
Chunk Size: 512
Top-k: 5

Results:
  Recall@5: 0.92
  Precision@5: 0.88
  MRR: 0.95
  NDCG@5: 0.91

Time:
  Avg Retrieval Time: 45ms
  p95: 120ms
```

### Generation Results

```
LLM Model: mistral (7B)
Prompt Strategy: Few-shot with CoT
Temperature: 0.7

Quality Metrics:
  BLEU: 0.42
  ROUGE-1: 0.58
  ROUGE-2: 0.35
  ROUGE-L: 0.52
  BERTScore F1: 0.89

LLM Judge (1-5 scale):
  Accuracy: 4.2
  Relevance: 4.5
  Completeness: 3.8
  Overall: 4.2

Time:
  Avg Generation Time: 1.2s
  p95: 2.1s
```

### E2E Results

```
Complete System

E2E Latency:
  Mean: 1.3s
  Median: 1.2s
  p95: 2.5s
  p99: 3.2s

Throughput: 15 queries/min

Resource Usage:
  Memory: 8.5GB
  CPU: 45%
  GPU: N/A
```

## 🔄 Continuous Benchmarking

### Schedule

- **Weekly**: Speed benchmarks (regression detection)
- **Bi-weekly**: Generation quality benchmarks
- **Monthly**: Comprehensive benchmark suite
- **Quarterly**: Hardware/resource evaluation

### CI/CD Integration

```yaml
# .github/workflows/benchmark.yml
name: Benchmark Suite
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly
  push:
    branches: [main, develop]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Run Benchmarks
        run: python scripts/run_benchmarks.py
      - name: Save Results
        run: |
          mkdir -p results
          cp benchmark_results.json results/
```

## 📊 Reporting

### Weekly Report Template

```markdown
## Week of [DATE]

### Highlights
- Retrieval accuracy: 92% (↑ from 88%)
- E2E latency: 1.3s (← same)
- New benchmark dataset: 50 queries

### Key Metrics
| Metric | Current | Previous | Change |
|--------|---------|----------|--------|
| BLEU | 0.42 | 0.40 | ↑ 5% |
| Retrieval Time | 45ms | 50ms | ↓ 10% |
| Memory Usage | 8.5GB | 8.7GB | ↓ 2% |

### Action Items
- [ ] Investigate spike in p95 latency
- [ ] Optimize embedding model
- [ ] Test on larger dataset
```

## 🎯 Target Metrics

### MVP Phase (September 2026)

- **Retrieval**: Recall@5 > 90%
- **Quality**: BLEU > 0.35, BERTScore > 0.85
- **Speed**: E2E latency < 2s
- **Resources**: Memory < 12GB

### Production Phase (Q4 2026)

- **Retrieval**: Recall@5 > 95%
- **Quality**: BLEU > 0.45, BERTScore > 0.90
- **Speed**: E2E latency < 1s
- **Resources**: Memory < 10GB
- **Reliability**: 99.5% uptime

## 🔧 Running Benchmarks

### Lokalno

```bash
# Svi benchmarks
python scripts/run_benchmarks.py

# Specifični benchmark
python scripts/run_benchmarks.py --benchmark retrieval

# Sa specifičnom konfigom
python scripts/run_benchmarks.py --config configs/benchmark_config.yaml

# Verbose output
python scripts/run_benchmarks.py -v

# Spremi rezultate
python scripts/run_benchmarks.py --output results/benchmark_2026_05_11.json
```

### Docker

```bash
# Gradnja image-a
docker build -t etf-rag-benchmark -f docker/Dockerfile.benchmark .

# Pokretanje
docker run --rm etf-rag-benchmark python scripts/run_benchmarks.py
```

## 📝 Benchmark Dataset

Dataset se čuva u `data/benchmarks/` sa sledećom strukturom:

```json
{
  "metadata": {
    "version": "1.0",
    "created_at": "2026-05-11",
    "num_queries": 100,
    "categories": ["single_doc", "multi_doc"],
    "language": "sr"
  },
  "queries": [
    {
      "id": "q001",
      "query": "Koja je trajanje osnovnih studija?",
      "category": "single_doc",
      "difficulty": "easy",
      "reference_answer": "Osnovne studije traju 4 godine.",
      "source_documents": ["study_program_2024.pdf"],
      "expected_citations": [
        {"document": "study_program_2024.pdf", "page": 5}
      ]
    }
  ]
}
```

## 🚀 Sljedeći Koraci

1. Kreiraj initial benchmark dataset (30 queries)
2. Implementiraj metrike kalkulatore
3. Setup CI/CD pipeline
4. Pocni sa weekly benchmarking
5. Pripremi benchmark paper za TELFOR
