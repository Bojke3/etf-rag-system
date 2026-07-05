"""Score previously collected benchmark answers.

This script reads benchmarking/runs/<run_id>/answers.jsonl and writes metric
outputs under benchmarking/runs/<run_id>/scores/. It never calls the RAG API.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation import BERTScoreMetric, BLEUMetric, ROUGEMetric

DEFAULT_OUTPUT_DIR = "benchmarking/runs"
AVAILABLE_METRICS = ("rouge", "bleu", "bertscore")


def iter_answers(answers_path: Path) -> Iterable[Dict[str, Any]]:
    """Yield collected answers from JSONL."""
    with answers_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def parse_metrics(value: str) -> List[str]:
    """Parse comma-separated metric names."""
    if value.strip().lower() == "all":
        return list(AVAILABLE_METRICS)

    metrics = [metric.strip().lower() for metric in value.split(",") if metric.strip()]
    unknown = [metric for metric in metrics if metric not in AVAILABLE_METRICS]
    if unknown:
        raise ValueError(f"Unknown metrics: {unknown}. Available metrics: {list(AVAILABLE_METRICS)}")
    return metrics


def average(values: List[float]) -> Optional[float]:
    """Return average for a non-empty list."""
    if not values:
        return None
    return sum(values) / len(values)


def calculate_metrics(
    answer: Dict[str, Any],
    metrics: List[str],
    metric_instances: Dict[str, Any],
) -> Dict[str, Any]:
    """Calculate selected metrics for one answer."""
    reference = answer.get("expected_answer", "")
    candidate = answer.get("actual_answer", "")
    scores: Dict[str, Any] = {}

    if answer.get("status") != "success":
        for metric in metrics:
            scores[metric] = {"error": "answer_status_not_success"}
        return scores

    if "rouge" in metrics:
        scores["rouge"] = metric_instances["rouge"].calculate(reference, candidate)
    if "bleu" in metrics:
        scores["bleu"] = metric_instances["bleu"].calculate(reference, candidate)
    if "bertscore" in metrics:
        scores["bertscore"] = metric_instances["bertscore"].calculate(reference, candidate)

    return scores


def extract_primary_score(scores: Dict[str, Any], metric_name: str) -> Optional[float]:
    """Extract the main numeric score for summary averages."""
    metric_scores = scores.get(metric_name)
    if isinstance(metric_scores, (int, float)):
        return float(metric_scores)
    if not isinstance(metric_scores, dict):
        return None

    if metric_name == "rouge":
        value = metric_scores.get("rougeL")
    elif metric_name == "bertscore":
        value = metric_scores.get("f1")
    elif metric_name == "bleu":
        value = metric_scores
    else:
        value = None

    return float(value) if isinstance(value, (int, float)) else None


def summarize_scores(scored_answers: List[Dict[str, Any]], metrics: List[str]) -> Dict[str, Any]:
    """Build aggregate metric summary."""
    successful = [answer for answer in scored_answers if answer.get("status") == "success"]
    failed = [answer for answer in scored_answers if answer.get("status") != "success"]
    metric_averages = {}

    for metric in metrics:
        values = [
            score
            for answer in successful
            for score in [extract_primary_score(answer.get("scores", {}), metric)]
            if score is not None
        ]
        metric_averages[metric] = average(values)

    worst_by_rouge = []
    if "rouge" in metrics:
        worst_by_rouge = sorted(
            scored_answers,
            key=lambda answer: extract_primary_score(answer.get("scores", {}), "rouge") or 0.0,
        )[:10]

    return {
        "total_answers": len(scored_answers),
        "successful_answers": len(successful),
        "failed_answers": len(failed),
        "metric_averages": metric_averages,
        "worst_by_rougeL": [
            {
                "id": answer.get("id"),
                "status": answer.get("status"),
                "rougeL": extract_primary_score(answer.get("scores", {}), "rouge"),
                "error": answer.get("error", ""),
            }
            for answer in worst_by_rouge
        ],
    }


def build_metric_instances(metrics: List[str]) -> Dict[str, Any]:
    """Instantiate only requested metrics."""
    instances = {}
    if "rouge" in metrics:
        instances["rouge"] = ROUGEMetric()
    if "bleu" in metrics:
        instances["bleu"] = BLEUMetric()
    if "bertscore" in metrics:
        instances["bertscore"] = BERTScoreMetric()
    return instances


def score_run(args: argparse.Namespace) -> Path:
    """Score a collected benchmark run and return the score path."""
    run_dir = Path(args.output_dir) / args.run_id
    answers_path = run_dir / "answers.jsonl"
    if not answers_path.exists():
        raise FileNotFoundError(f"Missing answers file: {answers_path}")

    metrics = parse_metrics(args.metrics)
    metric_instances = build_metric_instances(metrics)
    answers = list(iter_answers(answers_path))

    scored_answers = []
    for index, answer in enumerate(answers, start=1):
        print(f"[{index}/{len(answers)}] score {answer.get('id')} with {','.join(metrics)}", flush=True)
        scores = calculate_metrics(answer, metrics, metric_instances)
        scored_answers.append(
            {
                "id": answer.get("id"),
                "type": answer.get("type"),
                "difficulty": answer.get("difficulty"),
                "question": answer.get("question"),
                "expected_answer": answer.get("expected_answer"),
                "actual_answer": answer.get("actual_answer"),
                "status": answer.get("status"),
                "error": answer.get("error", ""),
                "source_document": answer.get("source_document"),
                "source_section": answer.get("source_section"),
                "sources": answer.get("sources", []),
                "timing": {
                    "processing_time_ms": answer.get("processing_time_ms"),
                    "retrieval_time_ms": answer.get("retrieval_time_ms"),
                    "generation_time_ms": answer.get("generation_time_ms"),
                    "wall_time_ms": answer.get("wall_time_ms"),
                },
                "scores": scores,
            }
        )

    scores_dir = run_dir / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    score_name = "_".join(metrics)
    score_path = scores_dir / f"{score_name}.json"
    summary = summarize_scores(scored_answers, metrics)

    output = {
        "run_id": args.run_id,
        "scored_at": datetime.now().isoformat(timespec="seconds"),
        "metrics": metrics,
        "answers_path": str(answers_path),
        "summary": summary,
        "results": scored_answers,
    }
    score_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Scores saved to: {score_path}")
    print(f"Metric averages: {summary['metric_averages']}")
    return score_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score a collected ETF RAG benchmark run")
    parser.add_argument("--run-id", required=True, help="Run id under benchmarking/runs")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory containing benchmark runs")
    parser.add_argument(
        "--metrics",
        default="rouge",
        help=f"Comma-separated metrics or 'all'. Available: {', '.join(AVAILABLE_METRICS)}",
    )
    return parser.parse_args()


if __name__ == "__main__":
    score_run(parse_args())
