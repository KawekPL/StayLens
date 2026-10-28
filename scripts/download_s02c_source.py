"""Download the observed free Berlin EssentialsPackage, never paid bundles.

Local research only. Terms: https://doorstepanalytics.com/legal/terms
The frozen hash intentionally rejects silently updated provider packages.
"""

import hashlib
import io
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from staylens.enrichment import EXTERNAL_SHA256

DESTINATION = Path(__file__).resolve().parents[1] / "data/raw/external/doorstep_berlin_20260919.zip"


def main():
    if DESTINATION.exists():
        payload = DESTINATION.read_bytes()
    else:
        fields = {
            "location": "Berlin",
            "country": "Germany",
            "filename": "EssentialsPackage",
            "date_str": "19092026",
            "form_submission": "true",
        }
        request = urllib.request.Request(
            "https://doorstepanalytics.com/download_raw",
            data=urllib.parse.urlencode(fields).encode(),
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = response.read(50_000_001)
    if len(payload) > 50_000_000 or not zipfile.is_zipfile(io.BytesIO(payload)):
        raise ValueError("Expected a free ZIP under 50 MB, not an HTML/login response")
    if hashlib.sha256(payload).hexdigest() != EXTERNAL_SHA256:
        raise ValueError("Source changed; audit it as a new version before use")
    if not DESTINATION.exists():
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        DESTINATION.write_bytes(payload)
    print(f"Verified {len(payload)} bytes: {DESTINATION}")


if __name__ == "__main__":
    main()
