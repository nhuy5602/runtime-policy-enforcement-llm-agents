"""Fetch, validate, and run pinned independent benchmark entry points.

This wrapper never invents benchmark results.  ``--smoke`` validates the pin
and local data only; ``--dry-run`` prints the exact external command; ``--run``
requires a real model credential and writes the upstream logs to the requested
directory.  AgentDojo is pinned to the source commit because the released
0.1.35 wheel does not expose the openai-compatible provider used by Runpod.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from experiments.agentdojo_pilot_manifest import load_manifest as load_pilot_case_manifest
except ModuleNotFoundError:  # direct ``python experiments/*.py`` support
    from agentdojo_pilot_manifest import load_manifest as load_pilot_case_manifest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path(__file__).with_name("independent_benchmark_manifest.json")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9A-Fa-f]{64}$")


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "independent-benchmark/v1":
        raise ValueError("unsupported independent benchmark manifest schema")
    if payload.get("status") != "not_run":
        raise ValueError("manifest status must remain not_run until result artifacts exist")
    if not isinstance(payload.get("benchmarks"), dict):
        raise ValueError("manifest.benchmarks must be an object")
    for name, spec in payload["benchmarks"].items():
        if not isinstance(spec, dict):
            raise ValueError(f"benchmark {name} must be an object")
        if spec.get("result_status") != "not_run":
            raise ValueError(f"benchmark {name} result_status must remain not_run")
        repository = spec.get("repository", "")
        commit = spec.get("commit", "")
        if not isinstance(repository, str) or not repository.startswith("https://"):
            raise ValueError(f"benchmark {name} repository must be https")
        if not isinstance(commit, str) or not HEX40.fullmatch(commit):
            raise ValueError(f"benchmark {name} commit must be a 40-character SHA")
        environment = spec.get("environment") or {}
        if environment:
            lockfile = environment.get("lockfile")
            lock_hash = environment.get("lockfile_sha256")
            if not isinstance(lockfile, str) or not lockfile or Path(lockfile).is_absolute():
                raise ValueError(f"benchmark {name} has an invalid lockfile path")
            if not isinstance(lock_hash, str) or not HEX64.fullmatch(lock_hash):
                raise ValueError(f"benchmark {name} has an invalid lockfile SHA256")
        for relative, digest in (spec.get("data_sha256") or {}).items():
            if not isinstance(relative, str) or Path(relative).is_absolute():
                raise ValueError(f"benchmark {name} has an invalid data path")
            if not isinstance(digest, str) or not HEX64.fullmatch(digest):
                raise ValueError(f"benchmark {name} has an invalid data SHA256")
        if name == "agentdojo":
            contract = spec.get("contract_migration")
            if not isinstance(contract, dict):
                raise ValueError("AgentDojo requires a reviewed contract_migration object")
            for field in ("module", "module_to_load", "manifest", "activation_env", "audit_env"):
                value = contract.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"AgentDojo contract_migration.{field} must be non-empty")
            for field in ("module", "manifest"):
                if Path(contract[field]).is_absolute():
                    raise ValueError(f"AgentDojo contract_migration.{field} must be repo-relative")
            expected_digest = contract.get("manifest_sha256")
            if not isinstance(expected_digest, str) or not HEX64.fullmatch(expected_digest):
                raise ValueError("AgentDojo contract_migration.manifest_sha256 must be SHA-256")
            contract_module = ROOT / contract["module"]
            contract_manifest = ROOT / contract["manifest"]
            if not contract_module.is_file() or not contract_manifest.is_file():
                raise ValueError("AgentDojo contract migration artifact is missing")
            actual_digest = hashlib.sha256(contract_manifest.read_bytes()).hexdigest().upper()
            if actual_digest != expected_digest.upper():
                raise ValueError("AgentDojo contract migration manifest digest mismatch")
            pilot = spec.get("pilot_case_manifest")
            if not isinstance(pilot, dict):
                raise ValueError("AgentDojo requires a preregistered pilot_case_manifest object")
            for field in ("path", "generator", "status", "scope"):
                value = pilot.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"AgentDojo pilot_case_manifest.{field} must be non-empty")
            for field in ("path", "generator"):
                if Path(pilot[field]).is_absolute():
                    raise ValueError(f"AgentDojo pilot_case_manifest.{field} must be repo-relative")
            if pilot["status"] != "pre_registered_not_run":
                raise ValueError("AgentDojo pilot_case_manifest must remain pre_registered_not_run")
            pilot_digest = pilot.get("sha256")
            if not isinstance(pilot_digest, str) or not HEX64.fullmatch(pilot_digest):
                raise ValueError("AgentDojo pilot_case_manifest.sha256 must be SHA-256")
            pilot_path = ROOT / pilot["path"]
            pilot_generator = ROOT / pilot["generator"]
            if not pilot_path.is_file() or not pilot_generator.is_file():
                raise ValueError("AgentDojo pilot case manifest or generator is missing")
            actual_pilot_digest = hashlib.sha256(pilot_path.read_bytes()).hexdigest().upper()
            if actual_pilot_digest != pilot_digest.upper():
                raise ValueError("AgentDojo pilot case manifest digest mismatch")
            load_pilot_case_manifest(pilot_path)
    return payload


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def git_head(source: Path) -> str | None:
    if not (source / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def fetch_source(spec: dict[str, Any], destination: Path) -> dict[str, Any]:
    if destination.exists():
        current = git_head(destination)
        if current == spec["commit"]:
            return {"status": "already_pinned", "path": str(destination), "head": current}
        raise FileExistsError(
            f"refusing to reuse {destination}: existing HEAD {current!r} != {spec['commit']}"
        )
    if shutil.which("git") is None:
        raise RuntimeError("git is required for --fetch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--filter=blob:none", "--no-checkout", spec["repository"], str(destination)],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(destination), "fetch", "--depth=1", "origin", spec["commit"]],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(destination), "checkout", "--detach", spec["commit"]],
        check=True,
    )
    return {"status": "fetched", "path": str(destination), "head": git_head(destination)}


def verify_source(name: str, spec: dict[str, Any], source: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "required_commit": spec["commit"],
        "source": str(source) if source else None,
        "head": None,
        "commit_ok": False,
        "data_hashes_ok": None,
        "lockfile_ok": None,
        "missing_data": [],
        "hash_mismatches": {},
    }
    if source is None or not source.exists():
        result["status"] = "source_missing"
        return result
    result["head"] = git_head(source)
    result["commit_ok"] = result["head"] == spec["commit"]
    environment = spec.get("environment") or {}
    if environment:
        lock_path = source / environment["lockfile"]
        result["lockfile"] = str(lock_path)
        result["lockfile_sha256"] = sha256(lock_path) if lock_path.exists() else None
        result["lockfile_ok"] = result["lockfile_sha256"] == environment["lockfile_sha256"].upper()
    if spec.get("data_sha256"):
        result["data_hashes_ok"] = True
        for relative, expected in spec["data_sha256"].items():
            path = source / relative
            if not path.exists():
                result["missing_data"].append(relative)
                result["data_hashes_ok"] = False
                continue
            actual = sha256(path)
            if actual != expected.upper():
                result["hash_mismatches"][relative] = {"expected": expected, "actual": actual}
                result["data_hashes_ok"] = False
    result["status"] = (
        "pinned"
        if result["commit_ok"]
        and result["data_hashes_ok"] is not False
        and result["lockfile_ok"] is not False
        else "unverified"
    )
    return result


def benchmark_source_root(name: str, spec: dict[str, Any], root: Path) -> Path:
    return root / name


def build_command(
    name: str,
    spec: dict[str, Any],
    source: Path | None,
    output: Path,
    *,
    track: str = "attested",
    user_task: str | None = None,
    injection_task: str | None = None,
) -> list[str]:
    if track not in {"baseline", "attested"}:
        raise ValueError("track must be baseline or attested")
    if name == "agentdojo":
        if source is not None:
            command = [
                "uv",
                "run",
                "--project",
                str(source),
                "--locked",
                "--no-dev",
                "--python",
                "3.12",
            ]
        else:
            command = [
                "uv",
                "run",
                "--python",
                "3.12",
                "--with",
                spec["package_spec"],
            ]
        command.extend(
            [
                "python",
                "-m",
                "agentdojo.scripts.benchmark",
                "--model",
                spec["model_provider"],
                "--model-id",
                spec["model_id"],
                "--benchmark-version",
                spec["benchmark_version"],
                "--suite",
                spec["suite"],
                "--attack",
                spec["attack"],
            ]
        )
        command.extend(["--module-to-load", spec["contract_migration"]["module_to_load"]])
        if track == "attested":
            command.extend(["--module-to-load", spec["module_to_load"]])
        if user_task:
            command.extend(["--user-task", user_task])
        if injection_task:
            command.extend(["--injection-task", injection_task])
        command.extend(["--logdir", str(output), "--force-rerun"])
        return command
    if name == "injecagent":
        if source is None:
            raise ValueError("InjecAgent requires --source-root or --fetch")
        model = os.environ.get(spec["model_name_env"], f"<missing:{spec['model_name_env']}>")
        return [
            sys.executable,
            "src/evaluate_prompted_agent.py",
            "--model_type",
            spec["model_type"],
            "--model_name",
            model,
            "--setting",
            spec["setting"],
            "--prompt_type",
            spec["prompt_type"],
            "--use_cache",
        ]
    raise ValueError(f"unsupported benchmark {name}")


def smoke(manifest: dict[str, Any], source_root: Path | None) -> dict[str, Any]:
    report: dict[str, Any] = {"manifest_valid": True, "benchmarks": {}}
    for name, spec in manifest["benchmarks"].items():
        source = benchmark_source_root(name, spec, source_root) if source_root else None
        status = verify_source(name, spec, source)
        if name == "agentdojo":
            status["adapter_module"] = spec["adapter_module"]
            status["adapter_module_exists"] = (ROOT / spec["adapter_module"]).exists()
            contract = spec["contract_migration"]
            contract_manifest = ROOT / contract["manifest"]
            status["contract_migration_module"] = contract["module"]
            status["contract_migration_module_exists"] = (ROOT / contract["module"]).exists()
            status["contract_migration_manifest"] = contract["manifest"]
            status["contract_migration_manifest_sha256"] = (
                sha256(contract_manifest) if contract_manifest.exists() else None
            )
            status["contract_migration_manifest_ok"] = (
                status["contract_migration_manifest_sha256"]
                == contract["manifest_sha256"].upper()
            )
            pilot = spec["pilot_case_manifest"]
            pilot_path = ROOT / pilot["path"]
            pilot_manifest = load_pilot_case_manifest(pilot_path)
            status["pilot_case_manifest"] = pilot["path"]
            status["pilot_case_manifest_sha256"] = sha256(pilot_path)
            status["pilot_case_manifest_ok"] = (
                status["pilot_case_manifest_sha256"] == pilot["sha256"].upper()
            )
            status["pilot_case_count"] = pilot_manifest["population"]["case_count"]
            status["pilot_selected_attack_episode_count"] = pilot_manifest["feasibility_selection"][
                "selected_attack_episode_count"
            ]
            status["package_importable_in_current_python"] = importlib.util.find_spec("agentdojo") is not None
            status["credentials_present"] = bool(
                os.environ.get(spec["base_url_env"]) and os.environ.get(spec["api_key_env"])
            )
        else:
            status["credentials_present"] = bool(os.environ.get(spec["api_key_env"]))
        report["benchmarks"][name] = status
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", choices=("agentdojo", "injecagent"), default="agentdojo")
    parser.add_argument(
        "--track",
        choices=("baseline", "attested"),
        default="attested",
        help="AgentDojo paired track: baseline omits the adapter; attested loads the fail-closed adapter.",
    )
    parser.add_argument("--user-task", help="Optional locked AgentDojo user task (for smoke runs).")
    parser.add_argument("--injection-task", help="Optional locked AgentDojo injection task (for smoke runs).")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source-root", type=Path, help="directory containing agentdojo/ and/or injecagent/")
    parser.add_argument("--fetch", action="store_true", help="clone the exact pinned repository before checking")
    parser.add_argument("--smoke", action="store_true", help="validate manifest, optional source, and hashes")
    parser.add_argument("--dry-run", action="store_true", help="print the exact upstream command without running it")
    parser.add_argument("--run", action="store_true", help="run the upstream benchmark; requires real credentials")
    parser.add_argument("--output", type=Path, default=Path("experiments/independent_runs"))
    args = parser.parse_args()
    if sum((args.smoke, args.dry_run, args.run)) != 1:
        parser.error("choose exactly one of --smoke, --dry-run, or --run")

    manifest = load_manifest(args.manifest)
    spec = manifest["benchmarks"][args.benchmark]
    source_root = args.source_root.resolve() if args.source_root else None
    source = benchmark_source_root(args.benchmark, spec, source_root) if source_root else None
    if args.fetch:
        if source is None:
            parser.error("--fetch requires --source-root")
        print(json.dumps(fetch_source(spec, source), indent=2))
        source = source
    if args.smoke:
        print(json.dumps(smoke(manifest, source_root), indent=2))
        return 0

    command = build_command(
        args.benchmark,
        spec,
        source,
        args.output.resolve(),
        track=args.track,
        user_task=args.user_task,
        injection_task=args.injection_task,
    )
    if args.dry_run:
        print(json.dumps({"benchmark": args.benchmark, "cwd": str(source or ROOT), "command": command}, indent=2))
        return 0

    missing = [
        variable
        for variable in (spec.get("api_key_env"), spec.get("base_url_env"))
        if variable and not os.environ.get(variable)
    ]
    if (
        args.benchmark == "agentdojo"
        and args.track == "attested"
        and not os.environ.get(spec.get("allowlist_env", ""))
    ):
        missing.append(spec.get("allowlist_env", "AGENTDOJO_ATTESTATION_ALLOWLIST"))
    if args.benchmark == "injecagent":
        missing = [
            variable
            for variable in (spec["api_key_env"], spec["model_name_env"])
            if not os.environ.get(variable)
        ]
    if missing:
        raise SystemExit("blocked: missing required credential/environment variable(s): " + ", ".join(missing))
    if args.benchmark == "agentdojo" and source is None:
        raise SystemExit("blocked: AgentDojo --run requires --source-root with the pinned lockfile")
    if source is not None:
        source_status = verify_source(args.benchmark, spec, source)
        if not source_status["commit_ok"]:
            raise SystemExit("blocked: source is not checked out at the manifest commit")
        if (spec.get("environment") or {}).get("lock_required_for_run") and not source_status["lockfile_ok"]:
            raise SystemExit("blocked: source lockfile does not match the manifest")
    args.output.mkdir(parents=True, exist_ok=True)
    run_env = os.environ.copy()
    adapter_root = str(ROOT)
    existing_pythonpath = run_env.get("PYTHONPATH")
    run_env["PYTHONPATH"] = (
        adapter_root
        if not existing_pythonpath
        else adapter_root + os.pathsep + existing_pythonpath
    )
    # AgentDojo/Rich emits Unicode symbols in logs; force UTF-8 so Windows
    # cp1252 consoles cannot turn a diagnostic into a benchmark failure.
    run_env.setdefault("PYTHONUTF8", "1")
    run_env.setdefault("PYTHONIOENCODING", "utf-8")
    if args.benchmark == "agentdojo":
        contract = spec["contract_migration"]
        run_env[contract["activation_env"]] = str((ROOT / contract["manifest"]).resolve())
        run_env.setdefault(
            contract["audit_env"],
            str(args.output.resolve() / "contract_migration_witness.json"),
        )
    if args.benchmark == "agentdojo" and args.track == "attested":
        run_env.setdefault(
            "AGENTDOJO_ATTESTATION_AUDIT_PATH",
            str(args.output.resolve() / "adapter_audit.json"),
        )
    subprocess.run(command, cwd=str(source or ROOT), env=run_env, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
