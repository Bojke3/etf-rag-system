# Setup i Instalacija

## Prikupljanje benchmark odgovora: laptop ili fakultetski server

Pokreni iz korena projekta u projektnom Python okruženju:

```powershell
python scripts/collect_benchmark_answers.py
```

Skripta najpre pita da li LLM radi lokalno ili preko SSH-a, zatim prikazuje
instalirane modele na izabranoj Ollami. Podrazumevani skup je
`benchmarking/finalna_pitanja.json`. U oba režima embedding model, pretraga
lokalnog indeksa i rezultati ostaju na laptopu. Preko SSH-a šalju se pitanje,
pronađeni odlomci i prompt, a generisanje radi na serveru. Flask aplikacija
ne mora biti pokrenuta. Potreban je već napravljen lokalni vektorski indeks.

U svoj `.env` dodaj podešavanja servera (stvarne vrednosti dobijaš od fakulteta):

```dotenv
BENCHMARK_EXECUTION=ask
SSH_HOST=adresa-servera
SSH_USER=korisnicko-ime
SSH_PORT=22
SSH_LOCAL_PORT=11435
SSH_OLLAMA_HOST=127.0.0.1
SSH_OLLAMA_PORT=11434
SSH_OLLAMA_MODEL=mistral:latest
SSH_STARTUP_TIMEOUT=120
# Opciono; koristi se i SSH agent ili ~/.ssh/config:
# SSH_IDENTITY_FILE=C:/Users/ime/.ssh/id_ed25519
```

Preporučen način prijave je SSH ključ/agent. Lozinku ne upisuj u `.env`.
Ako server zahteva lozinku ili ključ ima passphrase, OpenSSH je traži u
interaktivnoj konzoli. Pri prvom povezivanju proveri fingerprint servera sa
administratorom i potvrdi ga u OpenSSH-u. Možeš koristiti i `Host` alias iz
`~/.ssh/config`, uz prazan `SSH_USER`; za nestandardni port postavi `SSH_PORT`.
Skripta koristi postojeći `ssh` program, otvara samo lokalni loopback port i
ne menja konfiguraciju niti pokreće Ollamu na serveru. Ollama tamo mora već
raditi, a SSH nalog mora imati dozvoljen TCP forwarding. Tunel se zatvara i
pri grešci ili prekidu pomoću Ctrl+C. Promeni `SSH_LOCAL_PORT` ako je zauzet.

Za automatski izbor servera postavi `BENCHMARK_EXECUTION=ssh`. Za rad bez
pitanja o modelu koristi `--model`; bez interaktivnog terminala model se uzima
iz odgovarajućeg podešavanja u `.env` i mora već biti instaliran. Primeri:

```powershell
# Kratak lokalni test
python scripts/collect_benchmark_answers.py --execution local --model mistral:7b --limit 3 --run-id local_mistral_smoke

# Isti model na serveru, pa dva poređenja
python scripts/collect_benchmark_answers.py --execution ssh --model mistral:latest --top-k 5 --run-id ssh_mistral_topk5
python scripts/collect_benchmark_answers.py --execution ssh --model qwen3.5:latest --top-k 5 --run-id ssh_qwen35_topk5
python scripts/collect_benchmark_answers.py --execution ssh --model mistral-small:latest --top-k 5 --run-id ssh_mistral_small_topk5

# Raniji način rada preko već pokrenute Flask aplikacije
python scripts/collect_benchmark_answers.py --execution api --endpoint http://localhost:8000/query
```

`--model` u lokalnom/SSH režimu stvarno bira model za generisanje. U API
režimu proverava se model aktivan u Flask aplikaciji; skripta ne menja njen
globalni izbor modela. Sam `--endpoint` takođe bira API režim.

Podešavanja `OLLAMA_TEMPERATURE`, `OLLAMA_TOP_P`, `OLLAMA_MAX_TOKENS` i
`OLLAMA_TIMEOUT` koriste se u lokalnom i SSH režimu. Generacione opcije sada
se šalju u Ollaminom polju `options`; stari klijent ih je slao na vrhu zahteva,
pa raniji rezultati nisu pouzdan dokaz da su te vrednosti bile primenjene.
Ponovi baseline sa novim klijentom. Opciono `OLLAMA_THINK` kontroliše thinking
kod podržanih modela (`true`/`false`, ili `low`/`medium`/`high` za GPT-OSS).
Ako nije zadato, koristi se podrazumevano ponašanje modela. Za Mistral nemoj
zadavati ovu opciju. Pri promeni modela proveri podršku i drži podešavanja
eksperimenta zabeleženim; veći izlazni budžet može biti potreban thinking modelu.

Rezultati se čuvaju u `benchmarking/runs/<run-id>/`. Konfiguracija beleži
stvarni naziv i digest modela iz `/api/tags`, generacione opcije, otisak promptova
i skupa pitanja. To je bitno jer se sadržaj taga `latest` može promeniti.
API režim može proveriti naziv modela, ali ne beleži njegov digest i generacione
opcije servera; za kontrolisano poređenje koristi local/ssh režime.

Ponovnim pokretanjem istog `--run-id` preskaču se uspešni odgovori, a greške
se pokušavaju ponovo. Poslednji pokušaj po pitanju koristi se u sažetku i
ocenjivanju. Promena modela, promptova, skupa ili relevantnih podešavanja
zahteva novi `--run-id`, kao i nastavak starih rezultata bez novih metapodataka.
Prekid može ostaviti pitanje bez sačuvanog odgovora; ono se ponavlja. Ako
SSH vezu prekineš tokom generisanja, udaljena obrada može potrajati dok server
ne primeti prekid. Lozinke i sadržaj SSH ključa ne ulaze u rezultate.

GPU se koristi prema konfiguraciji i raspoloživoj memoriji serverske Ollame;
SSH sam po sebi ne garantuje GPU izvršavanje. Proveri `ollama ps` na serveru
tokom generisanja. Vreme generisanja mereno sa laptopa uključuje SSH/mrežni
prenos i eventualno čekanje na deljenom serveru, pa ga odvoji od ocene kvaliteta.

## 📋 Preduslov

- Python 3.10+
- pip ili conda
- Git
- Docker (opciono, za Ollama)
- 4GB RAM (minimum)
- 20GB disk prostora (za modele i dokumente)

## 🔧 Instalacija

### 1. Kloniranje Repository-a

```bash
git clone https://github.com/Bojke3/etf-rag-system.git
cd etf-rag-system
```

### 2. Kreiranje Virtual Environment-a

#### Na Linux/Mac:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Na Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalacija Zavisnosti

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Setup Ollama (Ako koristiš lokalne modele)

#### Option A: Docker (Preporučeno)

```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Preuzimanje modela
docker exec ollama ollama pull llama2
docker exec ollama ollama pull mistral
docker exec ollama ollama pull neural-chat
```

#### Option B: Direktna Instalacija

1. Preuzmi sa https://ollama.ai
2. Instaliraj za tvoj OS
3. Pokreni:
   ```bash
   ollama serve
   ```
4. U novoj terminalu:
   ```bash
   ollama pull llama2
   ollama pull mistral
   ollama pull neural-chat
   ```

### 5. Konfiguracija

#### Kreiraj `.env` fajl:

```bash
cp .env.example .env
```

#### Uređivanje `.env`:

```env
# LLM Configuration
LLM_TYPE=ollama  # ollama, huggingface, openai
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
OLLAMA_TEMPERATURE=0.7

# Embedding Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_STORE_TYPE=faiss  # faiss, pinecone, chroma

# Data Configuration
DATA_DIR=./data/documents
PROCESSED_DATA_DIR=./data/processed
EMBEDDING_DIR=./data/embeddings

# Vector Store Configuration
VECTOR_STORE_PATH=./models/vectorstore

# Logging
LOG_LEVEL=INFO

# Web Configuration
WEB_HOST=0.0.0.0
WEB_PORT=8000

# Optional: Cloud LLM APIs
# OPENAI_API_KEY=your_key_here
# HUGGINGFACE_API_KEY=your_key_here
```

## 📂 Struktura Direktrijuma

Kreiraj sledeće direktorijume:

```bash
mkdir -p data/documents/studies
mkdir -p data/documents/master_theses
mkdir -p data/documents/other
mkdir -p data/processed
mkdir -p data/embeddings
mkdir -p models/vectorstore
mkdir -p logs
mkdir -p experiments/prompt_strategies
mkdir -p experiments/model_comparisons
mkdir -p experiments/evaluation_reports
```

## 📥 Skidanje Dokumenata

### Fakultetski Dokumenti

1. Idi na [ETF Beograd](https://www.etf.bg.ac.rs/)
2. Preuzmi studijske programe (PDF)
3. Smesti u `data/documents/studies/`

### Master Radovi

Kontaktiraj profesora Marka za:
- Master radove
- Interna dokumenta

Smesti u `data/documents/master_theses/`

## 🚀 Prvi Testovi

### 1. Provera Installation-a

```bash
python -c "import src; print('Installation OK')"
```

### 2. Provera Ollama-e

```bash
curl http://localhost:11434/api/version
```

Ili iz Pythona:

```bash
python -c "from src.llm.ollama_client import OllamaClient; c = OllamaClient(); print(c.list_models())"
```

### 3. Provera Embedding-a

```bash
python -c "from src.embedding.embedder import EmbeddingModel; e = EmbeddingModel(); print(e.embed('test')[:5])"
```

## 📝 Procesiranje Dokumenata

```bash
# Procesiranje svih dokumenata iz data/documents/
python scripts/process_documents.py

# Opcije:
python scripts/process_documents.py --input data/documents --output data/processed --chunk-size 512
```

## 🏗️ Gradnja Vector Store-a

```bash
python scripts/build_vectorstore.py

# Opcije:
python scripts/build_vectorstore.py --input data/processed --output models/vectorstore --vector-store faiss
```

## 🌐 Pokretanje Web Aplikacije

```bash
# Development
python web/app.py

# Production (sa gunicorn)
gunicorn -w 4 -b 0.0.0.0:8000 web.app:app
```

Otidi na: http://localhost:8000

## 🤖 Pokretanje Bot-a

### Telegram Bot

```bash
# Prvo kreiraj bot sa @BotFather na Telegram-u i dobij token
# Onda postavi u .env:
# TELEGRAM_BOT_TOKEN=your_token_here

python scripts/run_telegram_bot.py
```

### Discord Bot

```bash
# Prvo kreiraj bot na Discord Developer Portal
# Onda postavi token u .env:
# DISCORD_BOT_TOKEN=your_token_here

python scripts/run_discord_bot.py
```

## 🧪 Pokretanje Testova

```bash
# Svi testovi
pytest tests/ -v

# Sa pokrajinom
pytest tests/ --cov=src

# Specifičan test
pytest tests/test_document_loader.py -v

# Sa output-om
pytest tests/ -v -s
```

## 📊 Pokretanje Benchmarka

```bash
python scripts/run_benchmarks.py

# Opcije:
python scripts/run_benchmarks.py --benchmark single_doc_qa --num-queries 100
```

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'src'"

**Rešenje:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
# ili na Windows:
set PYTHONPATH=%PYTHONPATH%;%cd%
```

### Problem: "ConnectionError: Can't connect to Ollama"

**Rešenje:**
- Provera da li je Ollama pokrenut: `curl http://localhost:11434/api/version`
- Provera `.env` za ispravan `OLLAMA_BASE_URL`

### Problem: "Out of Memory" pri procesiranju dokumenata

**Rešenje:**
```bash
# Smanjiti chunk size
python scripts/process_documents.py --chunk-size 256

# Ili procesirati po direktorijumima
python scripts/process_documents.py --input data/documents/studies
```

### Problem: "CUDA out of memory" (ako koristi GPU)

**Rešenje:**
- Smanjiti batch size u `.env`
- Ili koristi CPU samo

## 📚 Dodatne Resurse

- [Ollama Dokumentacija](https://github.com/jmorganca/ollama)
- [Sentence Transformers](https://www.sbert.net/)
- [LangChain](https://python.langchain.com/)
- [FAISS](https://github.com/facebookresearch/faiss)

## ✅ Checklist - Prvo Pokretanje

- [ ] Python 3.10+ instaliran
- [ ] Virtual environment kreiran i aktiviran
- [ ] Zavisnosti instalirane (`pip install -r requirements.txt`)
- [ ] Ollama preuzet i pokrenuta
- [ ] `.env` fajl kreiran i konfiguriran
- [ ] Direktorijumi kreirani
- [ ] Dokumenti skidati
- [ ] Testovi prolaze (`pytest tests/`)
- [ ] Web aplikacija pokreće se (`python web/app.py`)
