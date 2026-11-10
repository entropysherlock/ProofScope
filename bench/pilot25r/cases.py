"""Pilot-25 cases exactly as executed by bench/pilot25_run (same payload, same strings, same hashes)."""
import base64
import json
import zlib
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parents[1] / "pilot25_run" / "case_payload.b64"


def load() -> list[dict]:
    return json.loads(zlib.decompress(base64.b64decode(PAYLOAD.read_text().strip())))


def adapted() -> list[dict]:
    return [d for d in load() if d["source_status"] == "ADAPTED_UNVERIFIED"]
