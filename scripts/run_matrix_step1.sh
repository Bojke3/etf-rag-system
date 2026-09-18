#!/usr/bin/env bash
# Step 1 of the TELFOR matrix: embedding x chunking, generator fixed to mistral:latest.
#
# 4 configurations x 5 repetitions = 20 runs of 60 questions. Retrieval runs
# locally; generation goes over the SSH tunnel to rticuda. See
# docs/TELFOR_RUN_MATRIX.md for the settings and why they were chosen.
#
# Every setting that selects a configuration is passed explicitly, so no .env
# edit can mislabel a run. A failed run is retried once, then recorded in
# FAILED.txt and the script moves on -- one bad run must not waste the hours
# left in the batch. Re-running this script resumes incomplete runs rather than
# duplicating answers.

set -uo pipefail
cd "$(dirname "$0")/.."

PYTHON=venv/bin/python
MODEL=mistral:latest
TOP_K=5
CONTEXT_CHARS=22000
NUM_CTX=16384
LOG_DIR=benchmarking/runs/_logs
mkdir -p "$LOG_DIR"
FAILED="$LOG_DIR/FAILED.txt"
TUNNEL_PORT=${SSH_LOCAL_PORT:-11435}

wait_for_free_port() {
  # Each run opens its own SSH tunnel on the same local port. The previous
  # run's ssh process can still be shutting down when the next one starts, and
  # the collector then refuses to launch with "Local port already in use" --
  # which once failed 17 runs in a row in under three seconds.
  local waited=0
  while lsof -iTCP:"$TUNNEL_PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; do
    if [ "$waited" -ge 60 ]; then
      echo "  port $TUNNEL_PORT still busy after ${waited}s; continuing anyway"
      return
    fi
    sleep 3
    waited=$((waited + 3))
  done
  [ "$waited" -gt 0 ] && echo "  waited ${waited}s for port $TUNNEL_PORT"
  return 0
}

# config_id | embedding model | index directory | chunk strategy
CONFIGS=(
  "c101|sentence-transformers/all-MiniLM-L6-v2|./models/vectorstore_c001_c1024_o150|flat_baseline"
  "c103|sentence-transformers/all-MiniLM-L6-v2|./models/vectorstore_c003_hier|hierarchical"
  "c105|BAAI/bge-m3|./models/vectorstore_c002_c1024_o150|flat_baseline"
  "c107|BAAI/bge-m3|./models/vectorstore_c004_hier_bge|hierarchical"
)

started=$(date "+%Y-%m-%d %H:%M:%S")
echo "=== Step 1 started $started ==="
echo "generator=$MODEL top_k=$TOP_K context=$CONTEXT_CHARS num_ctx=$NUM_CTX"

for entry in "${CONFIGS[@]}"; do
  IFS='|' read -r config embedding index strategy <<< "$entry"
  echo
  echo "--- $config | $embedding | $strategy ---"

  for rep in 01 02 03 04 05; do
    run_id="dev_combined_${config}_r${rep}"
    log="$LOG_DIR/${run_id}.log"

    for attempt in 1 2; do
      wait_for_free_port
      echo "[$(date '+%H:%M:%S')] $run_id (attempt $attempt)"
      EMBEDDING_MODEL="$embedding" \
      VECTOR_STORE_PATH="$index" \
      CHUNK_STRATEGY="$strategy" \
      $PYTHON scripts/collect_benchmark_answers.py \
        --execution ssh --model "$MODEL" \
        --top-k "$TOP_K" --context-max-chars "$CONTEXT_CHARS" --num-ctx "$NUM_CTX" \
        --run-id "$run_id" --label "$config" \
        >> "$log" 2>&1 && break

      if [ "$attempt" = 2 ]; then
        echo "FAILED: $run_id ($(date '+%Y-%m-%d %H:%M:%S')) -- see $log" | tee -a "$FAILED"
      else
        echo "  retrying $run_id in 15s"
        sleep 15
      fi
    done

    done_count=$(wc -l < "benchmarking/runs/$run_id/answers.jsonl" 2>/dev/null || echo 0)
    echo "[$(date '+%H:%M:%S')] $run_id done, $done_count answers"
  done
done

echo
echo "=== Step 1 finished $(date '+%Y-%m-%d %H:%M:%S') (started $started) ==="
$PYTHON scripts/build_run_index.py || true
