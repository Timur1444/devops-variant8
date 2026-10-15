"""Run the local equivalent of the workflow without claiming a GitHub run."""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--version", default="1.0.0")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    folder = root / "evidence" / args.run_id
    folder.mkdir(parents=True, exist_ok=True)
    stages = [
        ("quality", [sys.executable, "-m", "ruff", "check", "."]),
        ("tests", [sys.executable, "-m", "pytest", "-q",
                   f"--junitxml={folder / 'junit.xml'}"]),
        ("build", [sys.executable, "scripts/build_artifact.py"]),
        ("deploy", [sys.executable, "scripts/smoke_deploy.py", "--output",
                    str(folder / "smoke.json"), "--version", args.version]),
    ]
    result = {"run_id": args.run_id, "version": args.version,
              "mode": "actual-local-workflow-equivalent",
              "started_at_utc": datetime.now(timezone.utc).isoformat(), "stages": []}
    for name, command in stages:
        started = time.perf_counter()
        completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
        elapsed = round(time.perf_counter() - started, 3)
        (folder / f"{name}.log").write_text(completed.stdout + completed.stderr)
        item = {"stage": name, "exit_code": completed.returncode,
                "duration_seconds": elapsed}
        result["stages"].append(item)
        print(f"{name}: exit={completed.returncode}, seconds={elapsed}")
        if completed.returncode:
            print(completed.stdout + completed.stderr)
            result["status"] = "failed"
            break
    else:
        result["status"] = "passed"
    (folder / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
