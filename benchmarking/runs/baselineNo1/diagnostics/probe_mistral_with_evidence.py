"""Send two diagnostic questions with curated corpus chunks and unchanged prompts."""

import hashlib
import importlib.util
import json
import os
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "benchmarking/runs/baselineNo1"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def connection_settings():
    # Read only connection settings, without displaying or copying credentials.
    allowed = {"SSH_HOST", "SSH_USER", "SSH_PORT", "SSH_IDENTITY_FILE", "SSH_LOCAL_PORT",
               "SSH_OLLAMA_HOST", "SSH_OLLAMA_PORT", "SSH_STARTUP_TIMEOUT"}
    result = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = line.partition("=")
        key = key.strip().upper()
        if separator and key in allowed:
            result[key] = value.strip().strip("\"'")
    result.update({key: os.environ[key] for key in allowed if key in os.environ})
    return result


def main():
    prompt_module = load_module("probe_prompts", ROOT / "src/llm/prompts.py")
    ssh_module = load_module("probe_ssh", ROOT / "src/llm/ssh_tunnel.py")
    preprocessing = load_module("probe_preprocessing", ROOT / "src/data/preprocessing.py")
    config = json.loads((RUN / "run_config.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "models/vectorstore/metadatas.json").read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in json.loads((ROOT / "benchmarking/finalna_pitanja.json").read_text(encoding="utf-8"))["questions"]}
    prompt_hash = hashlib.sha256((ROOT / "src/llm/prompts.py").read_bytes()).hexdigest()
    if prompt_hash != config["backend"]["prompts_sha256"]:
        raise ValueError("Current prompts differ from the baseline; review the experiment before running.")
    template = prompt_module.PromptTemplate
    cases = []
    for question_id, chunk_ids in [("REAL_043", [22]), ("REAL_033", [68, 69])]:
        chunks = [next(m for m in metadata if m["document"] == "Pravilnik_o_OAS_preciscen_jun_2023"
                       and m["chunk_id"] == chunk_id) for chunk_id in chunk_ids]
        context = "\n\n".join(chunk["text"] for chunk in chunks)
        question = preprocessing.TextPreprocessor().clean(questions[question_id]["question"])
        options = {k: v for k, v in config["backend"]["generation_options"].items()
                   if k in ("temperature", "num_predict", "top_p") and v is not None}
        payload = {"model": config["model"], "system": template.SYSTEM,
                   "prompt": template.format_zero_shot(question, context), "options": options, "stream": False}
        cases.append({"id": question_id, "question": questions[question_id]["question"],
                      "expected_answer": questions[question_id]["expected_answer"], "chunks": chunks,
                      "context": context, "request": payload})
    report = {"experiment": "Curated evidence with baseline model, system prompt, zero-shot template and generation options; no retrieval and no 2000-character context truncation.",
              "prompts_sha256": prompt_hash, "expected_model_digest": config["backend"]["model_digest"],
              "cases": cases}
    output = RUN / "diagnostics/mistral_curated_evidence.json"

    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    save()
    settings = connection_settings()
    base_url = f"http://127.0.0.1:{settings.get('SSH_LOCAL_PORT', '11435')}"
    manager = nullcontext()
    try:
        ssh_module.list_models(base_url, timeout=3)
        print("Using the existing Ollama endpoint after model digest verification.", flush=True)
    except (OSError, ValueError):
        if not settings.get("SSH_HOST"):
            raise ValueError("SSH_HOST must be configured in .env.")
        manager = ssh_module.SSHTunnel(
            settings["SSH_HOST"], settings.get("SSH_USER", ""), int(settings.get("SSH_PORT", "22")),
            settings.get("SSH_IDENTITY_FILE", ""), int(settings.get("SSH_LOCAL_PORT", "11435")),
            settings.get("SSH_OLLAMA_HOST", "127.0.0.1"), int(settings.get("SSH_OLLAMA_PORT", "11434")),
            int(settings.get("SSH_STARTUP_TIMEOUT", "120")))
    with manager:
        models = ssh_module.list_models(base_url)
        model = next((m for m in models if m.get("name") == config["model"]), None)
        if model is None or model.get("digest") != report["expected_model_digest"]:
            raise ValueError("The requested model is missing or its digest differs from the baseline.")
        report["verified_model_digest"] = model["digest"]
        for case in cases:
            print(f"Generating {case['id']} with {len(case['context'])} context characters...", flush=True)
            started = time.monotonic()
            request = Request(base_url + "/api/generate", data=json.dumps(case["request"]).encode("utf-8"),
                              headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=config["timeout"]) as response:
                result = json.load(response)
            case["actual_answer"] = result.get("response", "")
            case["done"] = result.get("done")
            case["done_reason"] = result.get("done_reason")
            case["prompt_eval_count"] = result.get("prompt_eval_count")
            case["eval_count"] = result.get("eval_count")
            case["wall_seconds"] = round(time.monotonic() - started, 3)
            case["completed_at"] = datetime.now(timezone.utc).isoformat()
            save()
            if not case["actual_answer"].strip() or not case["done"]:
                raise RuntimeError("Ollama did not return a completed nonempty answer.")
            print(json.dumps({"id": case["id"], "actual_answer": case["actual_answer"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
