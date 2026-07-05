"""Collect benchmark answers from the Flask /query endpoint.

This script does the slow part only: it sends benchmark questions to the RAG
API and stores raw answers. Metrics can be recalculated later with
score_benchmark_run.py without asking the LLM again.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_benchmark import (
    DEFAULT_BENCHMARK_PATH,
    DEFAULT_ENDPOINT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TIMEOUT,
    build_run_id,
    call_query_endpoint,
    format_duration,
    load_benchmark,
    write_json,
)

try:
    from src.config import config
except Exception:
    config = None


def get_config_value(name: str, default: Any = None) -> Any:
    """Read a value from app config when available."""
    return getattr(config, name, default)


def load_completed_ids(answers_path: Path) -> Set[str]:
    """Read completed question ids from an existing answers JSONL file."""
    completed = set()
    if not answers_path.exists():
        return completed

    with answers_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                answer = json.loads(line)
            except json.JSONDecodeError:
                continue
            question_id = answer.get("id")
            if question_id:
                completed.add(question_id)
    return completed


def iter_answers(answers_path: Path) -> Iterable[Dict[str, Any]]:
    """Yield persisted answers from a JSONL file."""
    if not answers_path.exists():
        return

    with answers_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def collect_answer(
    question_item: Dict[str, Any],
    endpoint: str,
    top_k: int,
    prompt_strategy: str,
    model: Optional[str],
    timeout: int,
) -> Dict[str, Any]:
    """Send one question to /query and return the raw answer record."""
    started_at = datetime.now().isoformat(timespec="seconds")
    wall_start = time.time()
    question = question_item["question"]

    try:
        api_result = call_query_endpoint(
            endpoint=endpoint,
            question=question,
            top_k=top_k,
            prompt_strategy=prompt_strategy,
            timeout=timeout,
        )
        return {
            "id": question_item["id"],
            "type": question_item.get("type"),
            "difficulty": question_item.get("difficulty"),
            "question": question,
            "expected_answer": question_item["expected_answer"],
            "actual_answer": api_result.get("answer", ""),
            "status": api_result.get("status", "unknown"),
            "error": api_result.get("error", ""),
            "processing_time_ms": api_result.get("processing_time_ms"),
            "retrieval_time_ms": api_result.get("retrieval_time_ms"),
            "generation_time_ms": api_result.get("generation_time_ms"),
            "wall_time_ms": int((time.time() - wall_start) * 1000),
            "sources": api_result.get("sources", []),
            "source_document": question_item.get("source_document"),
            "source_section": question_item.get("source_section"),
            "config": build_answer_config(endpoint, top_k, prompt_strategy, model, timeout),
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }
    except Exception as exc:
        return {
            "id": question_item["id"],
            "type": question_item.get("type"),
            "difficulty": question_item.get("difficulty"),
            "question": question,
            "expected_answer": question_item["expected_answer"],
            "actual_answer": "",
            "status": "error",
            "error": str(exc),
            "processing_time_ms": None,
            "retrieval_time_ms": None,
            "generation_time_ms": None,
            "wall_time_ms": int((time.time() - wall_start) * 1000),
            "sources": [],
            "source_document": question_item.get("source_document"),
            "source_section": question_item.get("source_section"),
            "config": build_answer_config(endpoint, top_k, prompt_strategy, model, timeout),
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }


def build_answer_config(
    endpoint: str,
    top_k: int,
    prompt_strategy: str,
    model: Optional[str],
    timeout: int,
) -> Dict[str, Any]:
    """Capture run settings and RAG component settings for later scoring."""
    return {
        "endpoint": endpoint,
        "top_k": top_k,
        "prompt_strategy": prompt_strategy,
        "model": model,
        "timeout": timeout,
        "embedding_model": get_config_value("embedding_model"),
        "embedding_device": get_config_value("embedding_device"),
        "chunk_size": get_config_value("chunk_size"),
        "chunk_overlap": get_config_value("chunk_overlap"),
        "retrieval_threshold": get_config_value("retrieval_threshold"),
        "vector_store_path": get_config_value("vector_store_path"),
    }


def summarize_collection(answers_path: Path, total_questions: int, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Build a lightweight collection summary without metric scores."""
    answers = list(iter_answers(answers_path))
    successful = [answer for answer in answers if answer.get("status") == "success"]
    failed = [answer for answer in answers if answer.get("status") != "success"]
    wall_times = [
        answer["wall_time_ms"]
        for answer in answers
        if isinstance(answer.get("wall_time_ms"), (int, float))
    ]

    average_wall_time = sum(wall_times) / len(wall_times) if wall_times else None
    return {
        "run_id": run_config["run_id"],
        "created_at": run_config["created_at"],
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "config": run_config,
        "total_questions": total_questions,
        "completed_questions": len(answers),
        "successful_questions": len(successful),
        "failed_questions": len(failed),
        "average_wall_time_ms": average_wall_time,
    }


def collect_benchmark_answers(args: argparse.Namespace) -> Path:
    """Collect benchmark answers and return the run directory."""
    questions = load_benchmark(args.benchmark)
    questions_to_run = questions[: args.limit] if args.limit is not None else questions

    run_id = args.run_id or build_run_id(args.label)
    run_dir = Path(args.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    answers_path = run_dir / "answers.jsonl"
    collection_summary_path = run_dir / "collection_summary.json"

    if args.no_resume and answers_path.exists():
        raise ValueError(
            f"Answers already exist for run_id={run_id}. Use a new --run-id or omit --no-resume to continue."
        )

    run_config = {
        "run_id": run_id,
        "label": args.label,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "benchmark": str(Path(args.benchmark)),
        "endpoint": args.endpoint,
        "top_k": args.top_k,
        "prompt_strategy": args.prompt_strategy,
        "model": args.model,
        "timeout": args.timeout,
        "limit": args.limit,
        "resume": not args.no_resume,
        "mode": "collect_answers",
        "component_config": build_answer_config(
            args.endpoint,
            args.top_k,
            args.prompt_strategy,
            args.model,
            args.timeout,
        ),
    }

    config_path = run_dir / "run_config.json"
    if config_path.exists() and not args.no_resume:
        try:
            existing_config = json.loads(config_path.read_text(encoding="utf-8"))
            run_config["created_at"] = existing_config.get("created_at", run_config["created_at"])
        except json.JSONDecodeError:
            pass
    write_json(config_path, run_config)

    completed_ids = set() if args.no_resume else load_completed_ids(answers_path)
    print(f"Run id: {run_id}")
    print(f"Endpoint: {args.endpoint}")
    print(f"Answers file: {answers_path}")

    with answers_path.open("a", encoding="utf-8") as f:
        for index, question_item in enumerate(questions_to_run, start=1):
            question_id = question_item["id"]
            if question_id in completed_ids:
                print(f"[{index}/{len(questions_to_run)}] skip {question_id} (already completed)")
                continue

            started_at = datetime.now().isoformat(timespec="seconds")
            print(f"[{index}/{len(questions_to_run)}] start {question_id} at {started_at}", flush=True)
            answer = collect_answer(
                question_item=question_item,
                endpoint=args.endpoint,
                top_k=args.top_k,
                prompt_strategy=args.prompt_strategy,
                model=args.model,
                timeout=args.timeout,
            )
            f.write(json.dumps(answer, ensure_ascii=False) + "\n")
            f.flush()
            completed_ids.add(question_id)

            finished_at = answer.get("finished_at") or datetime.now().isoformat(timespec="seconds")
            duration = format_duration(answer.get("wall_time_ms"))
            print(
                f"[{index}/{len(questions_to_run)}] finish {question_id} at {finished_at} "
                f"| duration={duration} | status={answer.get('status')}",
                flush=True,
            )
            if answer.get("status") != "success" and answer.get("error"):
                print(f"[{index}/{len(questions_to_run)}] error {question_id}: {answer.get('error')}", flush=True)

            summary = summarize_collection(answers_path, len(questions_to_run), run_config)
            write_json(collection_summary_path, summary)

    summary = summarize_collection(answers_path, len(questions_to_run), run_config)
    write_json(collection_summary_path, summary)

    print(f"Answers saved to: {answers_path}")
    print(f"Completed: {summary['completed_questions']}/{summary['total_questions']}")
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect ETF RAG benchmark answers from the /query API")
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK_PATH, help="Benchmark JSON path")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="RAG /query endpoint")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for benchmark runs")
    parser.add_argument("--run-id", help="Existing or new run id. Reusing it resumes by default")
    parser.add_argument("--label", default="baseline_topk3", help="Short label used when run id is generated")
    parser.add_argument("--limit", type=int, help="Only run the first N questions")
    parser.add_argument("--top-k", type=int, default=get_config_value("retrieval_top_k", 3), help="Retrieval top_k")
    parser.add_argument("--prompt-strategy", default="zero_shot", help="Prompt strategy sent to /query")
    parser.add_argument("--model", default=get_config_value("ollama_model"), help="Model label recorded in run metadata")
    parser.add_argument("--timeout", type=int, default=get_config_value("ollama_timeout", DEFAULT_TIMEOUT), help="HTTP timeout in seconds")
    parser.add_argument("--no-resume", action="store_true", help="Do not skip ids already present in answers.jsonl")
    return parser.parse_args()


if __name__ == "__main__":
    collect_benchmark_answers(parse_args())
