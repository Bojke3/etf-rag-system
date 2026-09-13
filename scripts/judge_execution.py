"""Load a fixed judge profile and connect independently of the answer generator."""

import json
from contextlib import contextmanager, nullcontext
from pathlib import Path

from src.data.stages import file_hash
from src.evaluation.llm_judge import prompt_hash
from src.llm import OllamaClient
from src.llm.ssh_tunnel import SSHTunnel, list_models

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "benchmarking/judge_profile.json"


def load_profile(path):
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    if profile.get("schema_version") != 1:
        raise ValueError("Unsupported judge profile schema")
    if profile.get("prompt_sha256") != prompt_hash():
        raise ValueError("Judge prompt differs from the frozen profile; create a new evaluation profile")
    if profile.get("temperature") != 0.0:
        raise ValueError("The reference judge protocol requires temperature 0")
    if any(not isinstance(profile.get(key), int) or profile[key] < 1
           for key in ("samples", "num_ctx", "max_tokens")):
        raise ValueError("Judge samples, num_ctx and max_tokens must be positive integers")
    digest = profile.get("digest_prefix", "")
    if len(digest) < 12 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("Judge profile must pin at least 12 hexadecimal digest characters")
    return profile


def verify_model(profile, models):
    record = next((m for m in models if (m.get("name") or m.get("model")) == profile["model"]), None)
    if record is None:
        raise ValueError(f"Fixed judge model is not installed: {profile['model']}")
    if not (record.get("digest") or "").startswith(profile["digest_prefix"]):
        raise ValueError("Judge model digest differs from the fixed profile; grading was not started")
    return record


def verify_generator_separation(profile, generator_records):
    """Reject known judge/generator overlap, including aliases with the same digest."""
    judge_family = profile["model"].split(":")[0]
    for record in generator_records:
        model = record.get("model") or ""
        digest = record.get("model_digest") or ""
        if model.split(":")[0] == judge_family or digest.startswith(profile["digest_prefix"]):
            raise ValueError("The fixed judge is reserved for evaluation and cannot score its own generated answers")


@contextmanager
def prepare_judge(args, config):
    path = getattr(args, "judge_profile", None) or DEFAULT_PROFILE
    profile = load_profile(path)
    verify_generator_separation(profile, getattr(args, "generator_records", []))
    if getattr(args, "judge_model", None) not in (None, profile["model"]):
        raise ValueError("--judge-model must match the fixed judge profile; use another profile for another judge")
    if getattr(args, "judge_samples", None) not in (None, profile["samples"]):
        raise ValueError("--judge-samples must match the fixed judge profile")
    execution = getattr(args, "judge_execution", None) or profile["execution"]
    manager = nullcontext()
    base_url = getattr(args, "judge_base_url", None) or getattr(config, "ollama_base_url", "http://localhost:11434")
    if execution == "ssh":
        if getattr(args, "judge_base_url", None):
            raise ValueError("For an existing tunnel URL use --judge-execution local with --judge-base-url")
        if config is None or not config.ssh_host:
            raise ValueError("SSH judge requires project dependencies and SSH_HOST in .env")
        manager = SSHTunnel(config.ssh_host, config.ssh_user, config.ssh_port,
                            config.ssh_identity_file, config.ssh_local_port, config.ssh_ollama_host,
                            config.ssh_ollama_port, config.ssh_startup_timeout)
        base_url = manager.base_url
    elif execution != "local":
        raise ValueError("Judge execution must be local or ssh")
    with manager:
        record = verify_model(profile, list_models(base_url))
        args.judge_samples = profile["samples"]
        args.judge_client = OllamaClient(
            base_url=base_url, model=profile["model"], timeout=args.judge_timeout,
            temperature=profile["temperature"], max_tokens=profile["max_tokens"],
            top_p=profile["top_p"], num_ctx=profile["num_ctx"], seed=profile["seed"],
            think=profile.get("think"), raise_errors=True)
        args.judge_metadata = {"profile": profile, "profile_sha256": file_hash(path),
                               "model_digest": record["digest"], "model_details": record.get("details", {}),
                               "execution": execution, "base_url": base_url}
        print(f"Fixed judge: {profile['model']} | digest={record['digest']} | mode={execution}", flush=True)
        yield
