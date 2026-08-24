"""Phase 5C, Requirement 15 — repository safety check before any public push.

Scans exactly the set of files `git` would actually push (`git
ls-files` — the tracked working tree, not the whole local directory,
which intentionally also holds gitignored raw IEEE-CIS data and
generated artifacts that must NEVER be pushed) for:

  1. raw IEEE-CIS dataset filenames
  2. secret-shaped strings (API keys, private key headers, generic
     password/secret/token assignments)
  3. unusually large tracked files (default >2MB)
  4. local machine absolute paths (/Users/..., /home/..., C:\\Users\\...)
  5. tracked .env files
  6. generated evaluation artifacts that might carry restricted data
     (anything under data/, which should never be tracked at all)

Exit code is non-zero if any check fails — safe to wire into a
pre-push hook or CI gate later. This script never modifies anything
and never pushes; Phase 5C explicitly does not push to Git.

Run:
    python -m scripts.pre_submission_check
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATASET_FILENAMES = {
    "train_transaction.csv", "test_transaction.csv",
    "train_identity.csv", "test_identity.csv",
    "sample_submission.csv",
}

SECRET_PATTERNS = [
    (re.compile(r"sk-ant-api[0-9a-zA-Z\-_]{20,}"), "Anthropic API key"),
    (re.compile(r"sk-[a-zA-Z0-9]{32,}"), "generic sk- style API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key ID"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key block"),
    (re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9+/_\-]{16,}['\"]"), "hardcoded credential-shaped assignment"),
]

LOCAL_PATH_PATTERNS = [
    re.compile(r"/Users/[A-Za-z0-9_.\-]+/"),
    re.compile(r"/home/[A-Za-z0-9_.\-]+/"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\"),
]

MAX_TRACKED_FILE_BYTES = 2 * 1024 * 1024  # 2MB — generous for a code+docs repo with no model binaries committed

# Files/paths that are allowed to mention a path-shaped string without
# being a real local-machine leak (documentation illustrating a run
# command, this script's own patterns, etc.)
PATH_MENTION_ALLOWLIST = {
    "scripts/pre_submission_check.py",  # this file, contains the patterns themselves
}

TEXT_FILE_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".txt", ".ts", ".tsx", ".js", ".css", ".html"}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files"], cwd=PROJECT_ROOT).decode()
    return [PROJECT_ROOT / line for line in output.splitlines() if line.strip()]


def check_raw_dataset_files(files: list[Path]) -> list[str]:
    return [f"raw dataset file is tracked: {f.relative_to(PROJECT_ROOT)}" for f in files if f.name in RAW_DATASET_FILENAMES]


def check_data_directory_tracked(files: list[Path]) -> list[str]:
    problems = []
    for f in files:
        rel = f.relative_to(PROJECT_ROOT)
        parts = rel.parts
        if parts[0] == "data" and not rel.name.startswith(".gitkeep"):
            problems.append(f"unexpected tracked file under data/: {rel}")
    return problems


def check_env_files(files: list[Path]) -> list[str]:
    return [f"tracked .env-shaped file: {f.relative_to(PROJECT_ROOT)}" for f in files if f.name == ".env" or f.name.startswith(".env.")]


def check_large_files(files: list[Path]) -> list[str]:
    problems = []
    for f in files:
        if f.is_file() and f.stat().st_size > MAX_TRACKED_FILE_BYTES:
            problems.append(f"large tracked file ({f.stat().st_size // 1024}KB): {f.relative_to(PROJECT_ROOT)}")
    return problems


def check_secrets_and_local_paths(files: list[Path]) -> list[str]:
    problems = []
    for f in files:
        if f.suffix not in TEXT_FILE_SUFFIXES or not f.is_file():
            continue
        rel = str(f.relative_to(PROJECT_ROOT))
        try:
            text = f.read_text(errors="ignore")
        except Exception:  # noqa: BLE001
            continue

        for pattern, label in SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(f"possible secret ({label}) in {rel}")

        if rel not in PATH_MENTION_ALLOWLIST:
            for pattern in LOCAL_PATH_PATTERNS:
                if pattern.search(text):
                    problems.append(f"local machine path found in {rel}")
                    break
    return problems


def main() -> int:
    files = tracked_files()
    print(f"Scanning {len(files)} git-tracked files...\n")

    all_problems: list[str] = []
    all_problems += check_raw_dataset_files(files)
    all_problems += check_data_directory_tracked(files)
    all_problems += check_env_files(files)
    all_problems += check_large_files(files)
    all_problems += check_secrets_and_local_paths(files)

    if all_problems:
        print("FAIL — repository is NOT safe to make public:\n")
        for p in all_problems:
            print(f"  - {p}")
        print(f"\n{len(all_problems)} issue(s) found.")
        return 1

    print("PASS — no raw dataset files, no tracked data/ artifacts, no .env files,")
    print("no oversized files, no secret-shaped strings, no local machine paths found")
    print("in any git-tracked file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
