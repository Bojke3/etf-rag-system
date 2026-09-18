"""Collect benchmark answers with local or SSH Ollama, or an existing RAG API.

This script runs the local RAG pipeline (or calls an existing RAG API) and
stores raw answers. Metrics can be recalculated later with
score_benchmark_run.py without asking the LLM again.
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_benchmark import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TIMEOUT,
    build_run_id,
    call_query_endpoint,
    format_duration,
    load_benchmark,
    recorded_path,
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
    statuses = {}
    if not answers_path.exists():
        return set()

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
                statuses[question_id] = answer.get('status')
    return {key for key, status in statuses.items() if status == 'success'}


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
    query_fn=None,
    backend_info=None,
    context_documents=None,
) -> Dict[str, Any]:
    """Send one question to /query and return the raw answer record."""
    started_at = datetime.now().isoformat(timespec="seconds")
    wall_start = time.time()
    question = question_item["question"]

    try:
        api_result = (query_fn or call_query_endpoint)(
            endpoint=endpoint,
            question=question,
            top_k=top_k,
            prompt_strategy=prompt_strategy,
            timeout=timeout,
            **({'context_documents': context_documents} if context_documents is not None else {}),
        )
        if api_result.get("status") == "success" and not api_result.get("answer", "").strip():
            api_result = {**api_result, "status": "error", "error": "The model returned no answer text."}
        return {
            "id": question_item["id"],
            "type": question_item.get("type"),
            "difficulty": question_item.get("difficulty"),
            "question": question,
            "expected_answer": question_item["expected_answer"],
            "required_facts": question_item.get("required_facts", []),
            "disallowed_claims": question_item.get("disallowed_claims", []),
            "expected_behavior": question_item.get("expected_behavior"),
            "actual_answer": api_result.get("answer", ""),
            "status": api_result.get("status", "unknown"),
            "error": api_result.get("error", ""),
            "processing_time_ms": api_result.get("processing_time_ms"),
            "retrieval_time_ms": api_result.get("retrieval_time_ms"),
            "generation_time_ms": api_result.get("generation_time_ms"),
            "wall_time_ms": int((time.time() - wall_start) * 1000),
            "sources": api_result.get("sources", []),
            "diagnostics": api_result.get("diagnostics", {}),
            "reference_sources": question_item.get("sources", []),
            "source_document": question_item.get("source_document"),
            "source_section": question_item.get("source_section"),
            "config": {**build_answer_config(endpoint, top_k, prompt_strategy, model, timeout), **(backend_info or {})},
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
            "required_facts": question_item.get("required_facts", []),
            "disallowed_claims": question_item.get("disallowed_claims", []),
            "expected_behavior": question_item.get("expected_behavior"),
            "actual_answer": "",
            "status": "error",
            "error": str(exc),
            "processing_time_ms": None,
            "retrieval_time_ms": None,
            "generation_time_ms": None,
            "wall_time_ms": int((time.time() - wall_start) * 1000),
            "sources": [],
            "reference_sources": question_item.get("sources", []),
            "source_document": question_item.get("source_document"),
            "source_section": question_item.get("source_section"),
            "config": {**build_answer_config(endpoint, top_k, prompt_strategy, model, timeout), **(backend_info or {})},
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
        "vector_store_path": recorded_path(get_config_value("vector_store_path")),
    }


def summarize_collection(answers_path: Path, total_questions: int, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Build a lightweight collection summary without metric scores."""
    # Retries append records; summarize the latest result for each question.
    answers = list({answer['id']: answer for answer in iter_answers(answers_path)}.values())
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


def collect_benchmark_answers(args: argparse.Namespace, query_fn=None, backend_info=None) -> Path:
    """Collect benchmark answers and return the run directory."""
    questions = load_benchmark(args.benchmark)
    from scripts.diagnostic_benchmark import select_questions
    questions_to_run, diagnostic_config = select_questions(questions, args)
    if diagnostic_config and (backend_info or {}).get('execution') not in ('local', 'ssh'):
        raise ValueError('Diagnostic collection requires a local/SSH backend.')
    if diagnostic_config:
        print(f"Diagnostic subset: {len(questions_to_run)} questions | mode={args.diagnostic_mode}", flush=True)

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
        "benchmark": recorded_path(args.benchmark),
        "benchmark_sha256": hashlib.sha256(Path(args.benchmark).read_bytes()).hexdigest(),
        "backend": backend_info or {"execution": "api", "model": args.model},
        "endpoint": args.endpoint,
        "top_k": args.top_k,
        "prompt_strategy": args.prompt_strategy,
        "model": args.model,
        "timeout": args.timeout,
        "limit": args.limit,
        "resume": not args.no_resume,
        "mode": "collect_answers",
        "diagnostic_config": diagnostic_config,
        "repeat_from": recorded_path(args.repeat_from) if getattr(args, 'repeat_from', None) else None,
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
        existing_config = json.loads(config_path.read_text(encoding="utf-8"))
        # Older runs stored absolute paths. Compare the same locations in one
        # form so the path-format migration does not prevent resuming a run.
        existing_config['repeat_from'] = recorded_path(existing_config.get('repeat_from'))
        existing_component = existing_config.get('component_config', {})
        if 'vector_store_path' in existing_component:
            existing_component['vector_store_path'] = recorded_path(existing_component['vector_store_path'])
        # Never mix answers from different models/settings in a resumed run.
        immutable = ("benchmark_sha256", "backend", "top_k", "prompt_strategy", "model", "component_config", "diagnostic_config", "repeat_from")
        changed = [key for key in immutable if existing_config.get(key) != run_config.get(key)]
        if changed:
            raise ValueError(f'The run has a different configuration ({", ".join(changed)}). Use a new --run-id.')
        run_config["created_at"] = existing_config.get("created_at", run_config["created_at"])
    elif answers_path.exists():
        raise ValueError('Answers exist without run_config.json. Use a new --run-id.')
    from scripts.benchmark_provenance import record_inputs
    retrieval = (backend_info or {}).get('retrieval_provenance')
    record_inputs(run_dir, args.benchmark,
                  index_dir=get_config_value('vector_store_path') if retrieval else None,
                  expected_files=retrieval.get('files') if retrieval else None,
                  embedding=retrieval)
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
                query_fn=query_fn,
                backend_info=backend_info,
                context_documents=question_item.get('curated_documents') if diagnostic_config and
                    args.diagnostic_mode == 'curated' else None,
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
            details = answer.get('diagnostics', {})
            if details:
                print(f"  Context: {details['context_chars']}/{details['full_context_chars']} chars "
                      f"| full chunks={details['chunks_fully_included']} "
                      f"| partial={details['chunks_partially_included']} | omitted={details['chunks_omitted']} "
                      f"| input with prompts={details['input_chars']} chars", flush=True)
            if answer.get("status") != "success" and answer.get("error"):
                print(f"[{index}/{len(questions_to_run)}] error {question_id}: {answer.get('error')}", flush=True)

            summary = summarize_collection(answers_path, len(questions_to_run), run_config)
            write_json(collection_summary_path, summary)

    summary = summarize_collection(answers_path, len(questions_to_run), run_config)
    write_json(collection_summary_path, summary)

    print(f"Answers saved to: {answers_path}")
    print(f"Completed: {summary['completed_questions']}/{summary['total_questions']}")
    print(f"Successful: {summary['successful_questions']} | Failed: {summary['failed_questions']}")
    return run_dir


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect ETF RAG answers: local retrieval, local/SSH LLM")
    parser.add_argument("--benchmark", default="benchmarking/finalna_pitanja.json", help="Benchmark JSON path")
    parser.add_argument("--execution", choices=["local", "ssh", "api"], help="Skip the local/SSH question; api uses an existing Flask service")
    parser.add_argument("--endpoint", default=None, help="Existing RAG /query endpoint (selects api mode)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for benchmark runs")
    parser.add_argument("--run-id", help="Existing or new run id. Reusing it resumes by default")
    parser.add_argument("--repeat-from", help="Reference run directory; use its recorded input paths/settings and verify all prompts before generation (requires a new run ID)")
    parser.add_argument("--label", default="baseline_topk3", help="Short label used when run id is generated")
    parser.add_argument("--limit", type=int, help="Only run the first N questions")
    parser.add_argument("--diagnostic-contexts", help="Reviewed source-passage JSON; selects only its question IDs")
    parser.add_argument("--diagnostic-mode", choices=["curated", "retrieved"], default="curated",
                        help="Use curated evidence or normal retrieval on the same diagnostic subset")
    parser.add_argument("--top-k", type=int, default=get_config_value("retrieval_top_k", 3), help="Retrieval top_k")
    parser.add_argument("--context-max-chars", type=int, default=None,
                        help="Retrieved context character budget, including separators but excluding prompts/question; local/SSH only (default: CONTEXT_MAX_CHARS from .env, otherwise 2000)")
    parser.add_argument("--num-ctx", type=int, default=None,
                        help="Ollama context window in tokens; local/SSH only (default: OLLAMA_NUM_CTX from .env, otherwise server/model default)")
    parser.add_argument("--prompt-strategy", default="zero_shot", help="Prompt strategy sent to /query")
    parser.add_argument("--model", default=None, help="Actual installed Ollama model to run; otherwise select interactively/use .env")
    parser.add_argument("--timeout", type=int, default=get_config_value("ollama_timeout", DEFAULT_TIMEOUT), help="HTTP timeout in seconds")
    parser.add_argument("--no-resume", action="store_true", help="Do not skip ids already present in answers.jsonl")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive.')
    if args.top_k < 1 or args.timeout < 1:
        parser.error('--top-k and --timeout must be positive.')
    if any(value is not None and value < 1 for value in (args.context_max_chars, args.num_ctx)):
        parser.error('--context-max-chars and --num-ctx must be positive.')
    return args


def main():
    global config
    from scripts.benchmark_execution import prepare_execution
    try:
        args = parse_args()
        if getattr(args, 'repeat_from', None):
            from scripts.benchmark_provenance import apply_repeat_settings
            config = apply_repeat_settings(args, config)
            print('Repeating recorded settings from the reference run; parameter defaults/overrides are replaced.', flush=True)
        # Validate input before establishing a connection or loading models.
        from scripts.diagnostic_benchmark import select_questions
        select_questions(load_benchmark(args.benchmark), args)
        with prepare_execution(args, config) as (query_fn, backend_info):
            run_dir = collect_benchmark_answers(args, query_fn=query_fn, backend_info=backend_info)
        summary = json.loads((run_dir / 'collection_summary.json').read_text(encoding='utf-8'))
        if summary['failed_questions']:
            return 1
    except KeyboardInterrupt:
        print('\nInterrupted. Saved answers are preserved; use the same --run-id to resume.')
        return 130
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
