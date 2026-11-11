"""Hashing and immutable source references."""
from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def normalize_statement(text: str) -> str:
    """Whitespace-only normalization.  Nothing semantic is ever rewritten."""
    return " ".join(text.split())


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_blob(repo_dir: str, commit: str, path: str) -> bytes:
    """Exact file bytes at a commit.  Raises if the commit or path is absent."""
    return subprocess.run(["git", "-C", repo_dir, "show", f"{commit}:{path}"],
                          check=True, capture_output=True).stdout


def git_source(repo_url: str, commit: str, path: str, data: bytes | None = None, **extra) -> dict:
    src = {"kind": "git", "locator": repo_url, "commit": commit, "path": path}
    if data is not None:
        src["sha256"] = sha256_bytes(data)
    src.update(extra)
    return src
