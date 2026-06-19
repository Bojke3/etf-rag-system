"""Run RAG benchmark questions against the Flask /query endpoint.

Examples:
    python scripts/run_benchmark.py
    python scripts/run_benchmark.py --limit 1
    python scripts/run_benchmark.py --run-id 2026-06-19_baseline_topk3
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set
from urllib import error, request

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation import ROUGEMetric

try:
    from src.config import config
except Exception:
    config = None

DEFAULT_BENCHMARK_PATH = "benchmarking/benchmark_svega.json"
DEFAULT_OUTPUT_DIR = "benchmarking/runs"
DEFAULT_ENDPOINT = "http://localhost:8000/query"
DEFAULT_TIMEOUT = 900


def load_benchmark(path: str) -> List[Dict[str, Any]]:
    """Load benchmark questions from a JSON file."""
    benchmark_path = Path(path)
    with benchmark_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        questions = data
    else:
        questions = data.get("questions", [])

    if not isinstance(questions, list):
        raise ValueError(f"Benchmark file has invalid questions format: {path}")

    missing_fields = [
        item.get("id", f"index_{idx}")
        for idx, item in enumerate(questions)
        if not item.get("id") or not item.get("question") or not item.get("expected_answer")
    ]
    if missing_fields:
        raise ValueError(f"Benchmark questions missing required fields: {missing_fields}")

    return questions


def build_run_id(label: str) -> str:
    """Create a timestamped run id with a short descriptive label."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_label = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in label.strip())
    safe_label = safe_label.strip("_") or "benchmark"
    return f"{timestamp}_{safe_label}"


def load_completed_ids(results_path: Path) -> Set[str]:
    """Read completed question ids from an existing JSONL results file."""
    completed = set()
    if not results_path.exists():
        return completed

    with results_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                result = json.loads(line)
            except json.JSONDecodeError:
                continue
            question_id = result.get("id")
            if question_id:
                completed.add(question_id)

    return completed


def iter_existing_results(results_path: Path) -> Iterable[Dict[str, Any]]:
    """Yield already persisted JSONL results."""
    if not results_path.exists():
        return

    with results_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def call_query_endpoint(
    endpoint: str,
    question: str,
    top_k: int,
    prompt_strategy: str,
    timeout: int,
    examples: str = "",
) -> Dict[str, Any]:
    """Send one benchmark question to the RAG API."""
    payload = {
        "question": question,
        "top_k": top_k,
        "prompt_strategy": prompt_strategy,
    }
    if examples:
        payload["examples"] = examples

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body)
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {response_body}") from exc


def evaluate_question(
    question_item: Dict[str, Any],
    endpoint: str,
    top_k: int,
    prompt_strategy: str,
    model: Optional[str],
    timeout: int,
    metric: ROUGEMetric,
) -> Dict[str, Any]:
    """Run and score one benchmark question."""
    started_at = datetime.now().isoformat(timespec="seconds")
    wall_start = time.time()
    question = question_item["question"]
    expected_answer = question_item["expected_answer"]

    try:
        api_result = call_query_endpoint(
            endpoint=endpoint,
            question=question,
            top_k=top_k,
            prompt_strategy=prompt_strategy,
            timeout=timeout,
        )
        actual_answer = api_result.get("answer", "")
        scores = metric.calculate(expected_answer, actual_answer)
        status = api_result.get("status", "unknown")
        error = api_result.get("error", "")

        return {
            "id": question_item["id"],
            "type": question_item.get("type"),
            "difficulty": question_item.get("difficulty"),
            "question": question,
            "expected_answer": expected_answer,
            "actual_answer": actual_answer,
            "status": status,
            "error": error,
            "rouge1": scores.get("rouge1", 0.0),
            "rouge2": scores.get("rouge2", 0.0),
            "rougeL": scores.get("rougeL", 0.0),
            "processing_time_ms": api_result.get("processing_time_ms"),
            "retrieval_time_ms": api_result.get("retrieval_time_ms"),
            "generation_time_ms": api_result.get("generation_time_ms"),
            "wall_time_ms": int((time.time() - wall_start) * 1000),
            "sources": api_result.get("sources", []),
            "source_document": question_item.get("source_document"),
            "source_section": question_item.get("source_section"),
            "config": {
                "endpoint": endpoint,
                "top_k": top_k,
                "prompt_strategy": prompt_strategy,
                "model": model,
            },
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }
    except Exception as exc:
        return {
            "id": question_item["id"],
            "type": question_item.get("type"),
            "difficulty": question_item.get("difficulty"),
            "question": question,
            "expected_answer": expected_answer,
            "actual_answer": "",
            "status": "error",
            "error": str(exc),
            "rouge1": 0.0,
            "rouge2": 0.0,
            "rougeL": 0.0,
            "processing_time_ms": None,
            "retrieval_time_ms": None,
            "generation_time_ms": None,
            "wall_time_ms": int((time.time() - wall_start) * 1000),
            "sources": [],
            "source_document": question_item.get("source_document"),
            "source_section": question_item.get("source_section"),
            "config": {
                "endpoint": endpoint,
                "top_k": top_k,
                "prompt_strategy": prompt_strategy,
                "model": model,
            },
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }


def average(values: List[float]) -> Optional[float]:
    """Return average for a non-empty list."""
    if not values:
        return None
    return sum(values) / len(values)


def summarize_results(
    results: List[Dict[str, Any]],
    total_questions: int,
    run_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Build run-level summary metrics."""
    successful = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") != "success"]

    processing_times = [
        r["processing_time_ms"]
        for r in successful
        if isinstance(r.get("processing_time_ms"), (int, float))
    ]
    retrieval_times = [
        r["retrieval_time_ms"]
        for r in successful
        if isinstance(r.get("retrieval_time_ms"), (int, float))
    ]
    generation_times = [
        r["generation_time_ms"]
        for r in successful
        if isinstance(r.get("generation_time_ms"), (int, float))
    ]

    worst_questions = sorted(results, key=lambda r: r.get("rougeL", 0.0))[:10]

    def grouped_average(field: str) -> Dict[str, Optional[float]]:
        grouped: Dict[str, List[float]] = {}
        for result in successful:
            key = result.get(field) or "unknown"
            grouped.setdefault(key, []).append(result.get("rougeL", 0.0))
        return {key: average(values) for key, values in sorted(grouped.items())}

    return {
        "run_id": run_config["run_id"],
        "created_at": run_config["created_at"],
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "config": run_config,
        "total_questions": total_questions,
        "completed_questions": len(results),
        "successful_questions": len(successful),
        "failed_questions": len(failed),
        "average_rouge1": average([r.get("rouge1", 0.0) for r in successful]),
        "average_rouge2": average([r.get("rouge2", 0.0) for r in successful]),
        "average_rougeL": average([r.get("rougeL", 0.0) for r in successful]),
        "average_processing_time_ms": average(processing_times),
        "average_retrieval_time_ms": average(retrieval_times),
        "average_generation_time_ms": average(generation_times),
        "average_rougeL_by_difficulty": grouped_average("difficulty"),
        "average_rougeL_by_type": grouped_average("type"),
        "worst_questions": [
            {
                "id": r.get("id"),
                "status": r.get("status"),
                "rougeL": r.get("rougeL", 0.0),
                "error": r.get("error", ""),
            }
            for r in worst_questions
        ],
    }


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write indented JSON with UTF-8 encoding."""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def format_duration(milliseconds: Optional[int]) -> str:
    """Format milliseconds as a compact human-readable duration."""
    if milliseconds is None:
        return "unknown"

    seconds = milliseconds / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds:.1f}s"


def run_benchmark(args: argparse.Namespace) -> Path:
    """Run benchmark and return the run directory path."""
    questions = load_benchmark(args.benchmark)
    if args.limit is not None:
        questions_to_run = questions[: args.limit]
    else:
        questions_to_run = questions

    run_id = args.run_id or build_run_id(args.label)
    run_dir = Path(args.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    results_path = run_dir / "results.jsonl"
    summary_path = run_dir / "summary.json"

    if args.no_resume and results_path.exists():
        raise ValueError(
            f"Results already exist for run_id={run_id}. Use a new --run-id or omit --no-resume to continue."
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
    }
    config_path = run_dir / "run_config.json"
    if config_path.exists() and not args.no_resume:
        try:
            existing_config = json.loads(config_path.read_text(encoding="utf-8"))
            run_config["created_at"] = existing_config.get("created_at", run_config["created_at"])
        except json.JSONDecodeError:
            pass
    write_json(config_path, run_config)

    completed_ids = set() if args.no_resume else load_completed_ids(results_path)
    metric = ROUGEMetric()

    with results_path.open("a", encoding="utf-8") as f:
        for index, question_item in enumerate(questions_to_run, start=1):
            question_id = question_item["id"]
            if question_id in completed_ids:
                print(f"[{index}/{len(questions_to_run)}] skip {question_id} (already completed)")
                continue

            started_at = datetime.now().isoformat(timespec="seconds")
            print(f"[{index}/{len(questions_to_run)}] start {question_id} at {started_at}", flush=True)
            result = evaluate_question(
                question_item=question_item,
                endpoint=args.endpoint,
                top_k=args.top_k,
                prompt_strategy=args.prompt_strategy,
                model=args.model,
                timeout=args.timeout,
                metric=metric,
            )
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            f.flush()
            completed_ids.add(question_id)

            finished_at = result.get("finished_at") or datetime.now().isoformat(timespec="seconds")
            duration = format_duration(result.get("wall_time_ms"))
            print(
                f"[{index}/{len(questions_to_run)}] finish {question_id} at {finished_at} "
                f"| duration={duration} | status={result.get('status')} | rougeL={result.get('rougeL', 0.0):.4f}",
                flush=True,
            )

            all_results = list(iter_existing_results(results_path))
            summary = summarize_results(
                results=all_results,
                total_questions=len(questions_to_run),
                run_config=run_config,
            )
            write_json(summary_path, summary)

    all_results = list(iter_existing_results(results_path))
    summary = summarize_results(
        results=all_results,
        total_questions=len(questions_to_run),
        run_config=run_config,
    )
    write_json(summary_path, summary)

    print(f"Benchmark run saved to: {run_dir}")
    print(f"Completed: {summary['completed_questions']}/{summary['total_questions']}")
    print(f"Average ROUGE-L: {summary['average_rougeL']}")
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ETF RAG benchmark against the /query API")
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK_PATH, help="Benchmark JSON path")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="RAG /query endpoint")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for benchmark runs")
    parser.add_argument("--run-id", help="Existing or new run id. Reusing it resumes by default")
    parser.add_argument("--label", default="baseline_topk3", help="Short label used when run id is generated")
    parser.add_argument("--limit", type=int, help="Only run the first N questions")
    parser.add_argument("--top-k", type=int, default=getattr(config, "retrieval_top_k", 3), help="Retrieval top_k")
    parser.add_argument("--prompt-strategy", default="zero_shot", help="Prompt strategy sent to /query")
    parser.add_argument("--model", default=getattr(config, "ollama_model", None), help="Model label recorded in run metadata")
    parser.add_argument("--timeout", type=int, default=getattr(config, "ollama_timeout", DEFAULT_TIMEOUT), help="HTTP timeout in seconds")
    parser.add_argument("--no-resume", action="store_true", help="Do not skip ids already present in results.jsonl")
    return parser.parse_args()


if __name__ == "__main__":
    run_benchmark(parse_args())
