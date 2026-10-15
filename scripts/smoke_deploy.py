"""Extract an artifact, start an isolated test server and check the API."""

import argparse
import json
import os
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def request_json(base, path, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        base + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        raw = response.read()
        return response.status, json.loads(raw) if raw else None


def deploy(archive, output, version="1.0.0"):
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="student-test-") as temporary:
        stage = Path(temporary)
        with tarfile.open(archive) as source:
            source.extractall(stage, filter="data")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        environment = os.environ.copy()
        environment["DATABASE_URL"] = f"sqlite:///{stage / 'smoke.db'}"
        environment["APP_VERSION"] = version
        base = f"http://127.0.0.1:{port}"
        with (stage / "server.log").open("w+") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "flask", "--app", "wsgi", "run",
                 "--host", "127.0.0.1", "--port", str(port)],
                cwd=stage, env=environment, stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 12
                while True:
                    if process.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    try:
                        health_status, health = request_json(base, "/health")
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError("Test server readiness timed out") from None
                        time.sleep(0.1)
                assert health_status == 200 and health["status"] == "ok"
                assert health["version"] == version
                payload = {"full_name": "Smoke Test", "group_name": "DEV-8",
                           "email": "smoke@example.test"}
                created_status, student = request_json(base, "/api/students", "POST", payload)
                assert created_status == 201
                list_status, students = request_json(base, "/api/students")
                assert list_status == 200 and len(students) == 1
                delete_status, _ = request_json(
                    base, f"/api/students/{student['id']}", "DELETE")
                assert delete_status == 204
                result = {"mode": "actual-local-artifact-deployment", "version": version,
                          "database": health["database"], "health": health_status,
                          "create": created_status, "list": list_status,
                          "delete": delete_status, "status": "passed"}
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(result, indent=2) + "\n")
                print(json.dumps(result, indent=2))
                return result
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                log.flush()
                log.seek(0)
                output.with_suffix(".server.log").write_text(log.read())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("dist/student-manager.tar.gz"))
    parser.add_argument("--output", type=Path, default=Path("reports/smoke.json"))
    parser.add_argument("--version", default=os.getenv("APP_VERSION", "1.0.0"))
    args = parser.parse_args()
    deploy(args.archive.resolve(), args.output.resolve(), args.version)
