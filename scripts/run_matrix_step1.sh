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
# Where generation runs. Default ssh; EXECUTION=local generates on this machine,
# which run_config.json records under backend.execution, so a run always states
# which machine produced it. A run started on one cannot be resumed on the other:
# the collector treats backend as immutable and refuses to mix them.
EXECUTION=${EXECUTION:-ssh}
# Space-separated config ids to run, e.g. ONLY="c107". Empty runs all four.
ONLY=${ONLY:-}
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
  [ "$EXECUTION" = "ssh" ] || return 0
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

# The number of lines is not the number of answers: a resumed run appends, and a
# line can be an error. A run once reported 60 answers while having 60 errors.
success_count() {
  $PYTHON - "$1" <<'PY' 2>/dev/null || echo 0
import json, sys, pathlib
path = pathlib.Path('benchmarking/runs') / sys.argv[1] / 'answers.jsonl'
latest = {}
if path.is_file():
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row = json.loads(line)
            latest[row['id']] = row
print(sum(1 for r in latest.values() if r.get('status') == 'success'))
PY
}

started=$(date "+%Y-%m-%d %H:%M:%S")
echo "=== Step 1 started $started ==="
echo "generator=$MODEL top_k=$TOP_K context=$CONTEXT_CHARS num_ctx=$NUM_CTX execution=$EXECUTION"
[ -n "$ONLY" ] && echo "only configs: $ONLY"

for entry in "${CONFIGS[@]}"; do
  IFS='|' read -r config embedding index strategy <<< "$entry"
  if [ -n "$ONLY" ] && [[ " $ONLY " != *" $config "* ]]; then
    continue
  fi
  echo
  echo "--- $config | $embedding | $strategy ---"

  for rep in 01 02 03 04 05; do
    run_id="dev_combined_${config}_r${rep}"
    log="$LOG_DIR/${run_id}.log"

    # A complete run costs a model load and, over ssh, another tunnel teardown --
    # another chance to hit the port race. Nothing to gain by re-entering it.
    if [ "$(success_count "$run_id")" = "60" ]; then
      echo "[$(date '+%H:%M:%S')] $run_id already complete (60 successful), skipping"
      continue
    fi

    for attempt in 1 2; do
      wait_for_free_port
      echo "[$(date '+%H:%M:%S')] $run_id (attempt $attempt)"
      EMBEDDING_MODEL="$embedding" \
      VECTOR_STORE_PATH="$index" \
      CHUNK_STRATEGY="$strategy" \
      $PYTHON scripts/collect_benchmark_answers.py \
        --execution "$EXECUTION" --model "$MODEL" \
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

    echo "[$(date '+%H:%M:%S')] $run_id done, $(success_count "$run_id")/60 successful"
  done
done

echo
echo "=== Step 1 finished $(date '+%Y-%m-%d %H:%M:%S') (started $started) ==="
$PYTHON scripts/build_run_index.py || true
