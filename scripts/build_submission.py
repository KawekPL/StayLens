"""Build a checked hand-in ZIP from committed source and the frozen runtime, no secrets."""

import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

from release_artifacts import RUNTIME_FILES, validated_contents

ROOT = Path(__file__).resolve().parents[1]


def main():
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise RuntimeError("Commit the submission sources before packaging")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(["git", "archive", "--format=zip", "HEAD"], cwd=ROOT)
    files = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as source:
        for name in source.namelist():
            if name.endswith("/") or name == "AGENTS.md":
                continue
            parts = Path(name).parts
            if any(
                part in {".git", ".local", ".venv", "node_modules", ".terraform"} for part in parts
            ):
                raise ValueError(f"Unexpected private source path: {name}")
            if name.endswith((".tfstate", ".tfvars", ".tfplan")) or Path(name).name.startswith(
                ".env"
            ):
                raise ValueError(f"Unexpected configuration secrets: {name}")
            files["StayLens/" + name] = source.read(name)
    manifest = json.loads((ROOT / "deploy/artifacts.json").read_text())
    runtime = validated_contents(
        ROOT / ".local/release/staylens-runtime.zip",
        manifest["archives"]["staylens-runtime.zip"],
        RUNTIME_FILES,
    )
    files.update({"StayLens/.runtime/" + name: data for name, data in runtime.items()})
    files["ZACZNIJ_TUTAJ.md"] = (ROOT / "docs/oddanie/ZACZNIJ_TUTAJ.md").read_bytes()
    files["MAIL_DO_PROWADZACEGO.txt"] = (
        ROOT / "docs/oddanie/MAIL_DO_PROWADZACEGO.txt"
    ).read_bytes()
    files["MANIFEST.json"] = (
        json.dumps(
            {
                "author": "Szymon Kawlowski",
                "student_id": "s29670",
                "date": "2026-11-02",
                "source_commit": commit,
                "model_sha256": manifest["model_sha256"],
                "files": {
                    name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode()
    directory = ROOT / "artifacts/submission"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "StayLens_s29670_2026-11-02.zip"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            out.writestr(info, data, compresslevel=9)
    with zipfile.ZipFile(destination) as check:
        assert check.testzip() is None
        assert set(check.namelist()) == set(files)
        for name, data in files.items():
            assert check.read(name) == data
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(f"{checksum}  {destination.name}\n")
    print(
        json.dumps(
            {
                "zip": str(destination),
                "bytes": destination.stat().st_size,
                "files": len(files),
                "sha256": checksum,
                "commit": commit,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
