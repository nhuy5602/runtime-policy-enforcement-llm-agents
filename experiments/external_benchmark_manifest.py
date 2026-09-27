"""Compatibility verifier for the authoritative independent benchmark manifest.

The manifest in ``independent_benchmark_manifest.json`` is the only source of
truth. This read-only helper verifies pins and metadata only; it never
downloads a benchmark, calls an LLM, or turns a missing run into a result.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from experiments.independent_benchmark_runner import DEFAULT_MANIFEST, load_manifest
except ModuleNotFoundError:  # direct ``python experiments/external_benchmark_manifest.py``
    from independent_benchmark_runner import DEFAULT_MANIFEST, load_manifest


def verify_remote_commits(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Read-only verification against remote refs; no clone or benchmark run."""

    results: list[dict[str, str]] = []
    for name, item in manifest["benchmarks"].items():
        completed = subprocess.run(
            ["git", "ls-remote", item["repository"], item["commit"]],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )
        status = (
            "match"
            if completed.returncode == 0 and item["commit"] in completed.stdout
            else "not_verified"
        )
        results.append({"name": name, "commit": item["commit"], "status": status})
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--verify-remotes", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    result: dict[str, Any] = {
        "manifest": str(args.manifest),
        "status": manifest["status"],
        "benchmarks": [
            {
                "name": name,
                "commit": item["commit"],
                "result_status": item["result_status"],
            }
            for name, item in manifest["benchmarks"].items()
        ],
    }
    if args.verify_remotes:
        result["remote_verification"] = verify_remote_commits(manifest)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
