"""Pobierz oryginalne dane do treningu. Uruchomienie aplikacji ich nie wymaga."""

import hashlib
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://data.insideairbnb.com/germany/be/berlin/2026-09-19"
SOURCES = {
    "listings.csv.gz": (
        f"{BASE}/data/listings.csv.gz",
        "657ea25841a3f9a5be45dd1db011804f8b29dd7e4d8143b961f4704ee6bf7673",
    ),
    "neighbourhoods.geojson": (
        f"{BASE}/visualisations/neighbourhoods.geojson",
        "b2941e38593025425d23209ff457e17a3da2afd45502fd288675bec1727708bd",
    ),
}


def main():
    directory = ROOT / "data/raw"
    directory.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in SOURCES.items():
        destination = directory / name
        temporary = directory / f"{name}.part"
        candidate = destination
        if not destination.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "StayLens-course-project"})
            with (
                urllib.request.urlopen(request, timeout=90) as response,
                temporary.open("wb") as output,
            ):
                shutil.copyfileobj(response, output)
            candidate = temporary
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Plik {name} różni się od źródła użytego w projekcie")
        if candidate == temporary:
            temporary.replace(destination)
        print(f"OK: {destination}")


if __name__ == "__main__":
    main()
