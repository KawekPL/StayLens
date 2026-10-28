"""Pack or restore an explicitly allowlisted, hash-pinned S02/S03 release (no training)."""

import argparse
import csv
import hashlib
import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_SHA = "47ed42c9c8ccec4db103da7ec437ea240d5045191eaf20df9e9e4bd85265d7bf"
CATALOG_SHA = "6c6d8c34d419f16684e815c720114ade2054001e46820c40d878c6a743906987"
RUNTIME_FILES = {
    "model/manifest.json": "artifacts/s02-v1/manifest.json",
    "model/hist_gradient_boosting.joblib": "artifacts/s02-v1/hist_gradient_boosting.joblib",
    "catalog/manifest.json": "data/prepared/s03/manifest.json",
    "catalog/catalog.json": "data/prepared/s03/catalog.json",
    "catalog/neighbourhoods.geojson": "data/prepared/s03/neighbourhoods.geojson",
}
CI_FILES = {
    "cv_predictions.csv": "artifacts/s02-v1/cv_predictions.csv",
    "validation_predictions.csv": "artifacts/s02-v1/validation_predictions.csv",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def archive(path, files):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            out.writestr(info, data, compresslevel=9)
    return {
        "sha256": digest(path.read_bytes()),
        "members": {name: digest(data) for name, data in sorted(files.items())},
    }


def without_hosts(path):
    source = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
    fields = [field for field in source.fieldnames if field != "host_id"]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(source)
    return output.getvalue().encode("utf-8")


def pack():
    files = {key: (ROOT / value).read_bytes() for key, value in RUNTIME_FILES.items()}
    if digest(files["model/hist_gradient_boosting.joblib"]) != MODEL_SHA:
        raise ValueError("Only the frozen S02 model can be released")
    if digest(files["catalog/catalog.json"]) != CATALOG_SHA:
        raise ValueError("Only the verified S03 catalogue can be released")
    directory = ROOT / ".local/release"
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {
        "release_tag": "s02-artifacts-v1",
        "model_sha256": MODEL_SHA,
        "catalog_sha256": CATALOG_SHA,
        "archives": {},
    }
    manifest["archives"]["staylens-runtime.zip"] = archive(
        directory / "staylens-runtime.zip", files
    )
    manifest["archives"]["staylens-ci.zip"] = archive(
        directory / "staylens-ci.zip",
        {key: without_hosts(ROOT / value) for key, value in CI_FILES.items()},
    )
    (ROOT / "deploy").mkdir(exist_ok=True)
    (ROOT / "deploy/artifacts.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    # The public runtime has no training rows, host IDs or validation prediction tables.
    restore(directory, include_ci=False)
    print(json.dumps({"packed": list(manifest["archives"]), "model_unchanged": True}))


def validated_contents(path, specification, allowed):
    if digest(path.read_bytes()) != specification["sha256"]:
        raise ValueError(f"Archive checksum mismatch: {path.name}")
    with zipfile.ZipFile(path) as source:
        if set(source.namelist()) != set(allowed) or len(source.namelist()) != len(allowed):
            raise ValueError("Unexpected or duplicate archive members")
        if set(specification["members"]) != set(allowed):
            raise ValueError("Unexpected manifest members")
        result = {}
        for name in allowed:
            data = source.read(name)
            if digest(data) != specification["members"][name]:
                raise ValueError(f"Member checksum mismatch: {name}")
            result[name] = data
        return result


def restore(directory, include_ci):
    manifest = json.loads((ROOT / "deploy/artifacts.json").read_text(encoding="utf-8"))
    contents = validated_contents(
        directory / "staylens-runtime.zip",
        manifest["archives"]["staylens-runtime.zip"],
        RUNTIME_FILES,
    )
    if digest(contents["model/hist_gradient_boosting.joblib"]) != MODEL_SHA:
        raise ValueError("Frozen model mismatch")
    if digest(contents["catalog/catalog.json"]) != CATALOG_SHA:
        raise ValueError("Frozen catalogue mismatch")
    for name, data in contents.items():
        target = ROOT / ".runtime" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        # CI gets normal artifact paths; runtime Docker context only gets .runtime.
        if include_ci:
            target = ROOT / RUNTIME_FILES[name]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    if include_ci:
        evidence = validated_contents(
            directory / "staylens-ci.zip", manifest["archives"]["staylens-ci.zip"], CI_FILES
        )
        for name, data in evidence.items():
            target = ROOT / CI_FILES[name]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["pack", "fetch"])
    parser.add_argument("--repo", default="KawekPL/StayLens")
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()
    if args.command == "pack":
        pack()
        return
    manifest = json.loads((ROOT / "deploy/artifacts.json").read_text(encoding="utf-8"))
    directory = ROOT / ".local/downloads"
    directory.mkdir(parents=True, exist_ok=True)
    names = ["staylens-runtime.zip"] + (["staylens-ci.zip"] if args.ci else [])
    executable = shutil.which("gh")
    if not executable:
        raise RuntimeError("GitHub CLI (gh) is required for private release downloads")
    for name in names:
        subprocess.run(
            [
                executable,
                "release",
                "download",
                manifest["release_tag"],
                "--repo",
                args.repo,
                "--pattern",
                name,
                "--dir",
                str(directory),
                "--clobber",
            ],
            check=True,
        )
    restore(directory, args.ci)
    print("Verified and restored frozen runtime" + (" and saved CI evidence" if args.ci else ""))


if __name__ == "__main__":
    main()
