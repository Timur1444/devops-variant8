"""Build a deployable source archive and its SHA-256 checksum."""

import hashlib
import tarfile
from pathlib import Path


def build():
    root = Path(__file__).resolve().parents[1]
    output = root / "dist"
    output.mkdir(exist_ok=True)
    archive = output / "student-manager.tar.gz"
    with tarfile.open(archive, "w:gz") as target:
        for name in ["app.py", "wsgi.py", "templates", "requirements.txt",
                     "Dockerfile", "compose.yaml", ".env.example"]:
            target.add(root / name, arcname=name)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{checksum}  {archive.name}\n")
    print(f"Created {archive.name}; sha256={checksum}")
    return archive


if __name__ == "__main__":
    build()
