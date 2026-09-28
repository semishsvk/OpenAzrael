#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SELF = "tools/validate_public_release_safety.py"
MAX_TRACKED_SIZE = 250 * 1024

FORBIDDEN_PREFIXES = (
    "original/",
    "raw/",
    "source_original/",
    "data/audio/original_audio/",
    "assets/audio/",
    "assets/rooms/",
    "assets/textures/classic/",
    "assets/ui/mice/",
    "assets/ui/legacy_menu/",
    "exports/",
    "export/",
    "build/",
    "dist/",
    "OpenAzrael_Backups/",
    "backups/",
    "snapshots/",
)
FORBIDDEN_NAMES = {"R.EXE", "r.exe"}
FORBIDDEN_EXTENSIONS = {
    ".exe", ".dll", ".com",
    ".iso", ".cue", ".mdf", ".mds",
    ".zip", ".7z", ".rar",
    ".wav", ".mp3", ".ogg", ".flac", ".mid", ".midi",
    ".azf", ".xaf", ".dat", ".pck", ".pak", ".wad",
    ".dmp", ".core",
}
CREDENTIAL_NAME = re.compile(
    r"(^|/)(?:\.env(?:\..*)?|id_(?:rsa|dsa|ecdsa|ed25519)|"
    r"credentials(?:\.[^/]+)?|secrets?(?:\.[^/]+)?|"
    r"\.npmrc|\.netrc|[^/]+\.(?:pem|key|p12|pfx|kdbx))$",
    re.IGNORECASE,
)
CONTENT_PATTERNS = {
    "github_token": re.compile(r"(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9_]{20,})"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "windows_home_path": re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s\"']+"),
    "mac_home_path": re.compile(r"/Users/[^/\s\"']+"),
    "linux_home_path": re.compile(r"/home/[^/\s\"']+"),
}

def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

def tracked_files() -> list[str]:
    proc = run_git("ls-files", "-z")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git ls-files failed")
    return [item for item in proc.stdout.split("\0") if item]

def is_probably_binary(data: bytes) -> bool:
    if not data:
        return False
    if b"\0" in data[:8192]:
        return True
    return False

def main() -> int:
    failures: list[dict[str, object]] = []
    checked_text = 0
    files = tracked_files()

    for rel in files:
        path = ROOT / rel
        normalized = rel.replace("\\", "/")

        if normalized in FORBIDDEN_NAMES or any(normalized.startswith(p) for p in FORBIDDEN_PREFIXES):
            failures.append({"kind": "forbidden_path", "path": normalized})

        suffix = path.suffix.lower()
        if suffix in FORBIDDEN_EXTENSIONS:
            failures.append({"kind": "forbidden_extension", "path": normalized, "extension": suffix})

        if CREDENTIAL_NAME.search(normalized):
            failures.append({"kind": "credential_like_filename", "path": normalized})

        try:
            size = path.stat().st_size
        except FileNotFoundError:
            failures.append({"kind": "tracked_file_missing", "path": normalized})
            continue

        if size > MAX_TRACKED_SIZE:
            failures.append({"kind": "oversized_tracked_file", "path": normalized, "size": size})

        if normalized == SELF:
            continue

        data = path.read_bytes()
        if is_probably_binary(data):
            continue
        text = data.decode("utf-8", errors="replace")
        checked_text += 1

        for kind, pattern in CONTENT_PATTERNS.items():
            match = pattern.search(text)
            if match:
                failures.append({
                    "kind": kind,
                    "path": normalized,
                    "line": text.count("\n", 0, match.start()) + 1,
                })

    result = {
        "schema": "openazrael.public_release_safety",
        "version": 1,
        "status": "PASS" if not failures else "FAIL",
        "tracked_files": len(files),
        "text_files_scanned": checked_text,
        "max_tracked_file_size": MAX_TRACKED_SIZE,
        "failed": failures,
        "scope": "current tracked tree only; history/privacy audit is documented separately",
    }
    print("OPENAZRAEL_PUBLIC_RELEASE_SAFETY " + json.dumps(result, separators=(",", ":")))
    print("OpenAzrael public-release current-tree safety:", result["status"])
    for item in failures:
        print(" -", item)
    return 0 if not failures else 1

if __name__ == "__main__":
    sys.exit(main())
