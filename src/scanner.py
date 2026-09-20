"""Safe-fix detectors only: whitespace, EOF newline, unpinned Actions."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
MAX_BYTES = 200_000


@dataclass
class Candidate:
    file: str
    rule: str
    excerpt: str
    context: str


def _iter_files(repo_path: str) -> list[Path]:
    root = Path(repo_path)
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        out.append(p)
    return sorted(out)


def _detect_trailing_whitespace(path: Path, rel: str) -> list[Candidate]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    for i, line in enumerate(text.splitlines(), start=1):
        if line != line.rstrip():
            return [Candidate(file=rel, rule="trailing-whitespace", excerpt=f"line {i}: {line[:80]}", context=text[:2000])]
    return []


def _detect_missing_eof_newline(path: Path, rel: str) -> list[Candidate]:
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    if not raw:
        return []
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return []
    if not raw.endswith(b"\n"):
        return [Candidate(file=rel, rule="missing-eof-newline", excerpt="file does not end with newline", context="add trailing newline")]
    return []


def _detect_unpinned_action(path: Path, rel: str) -> list[Candidate]:
    if path.suffix not in {".yml", ".yaml"}:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- uses:") and "@v" in s and len(s.split("@")[-1].strip()) <= 4:
            return [Candidate(file=rel, rule="unpinned-action", excerpt=s[:120], context=text[:2000])]
    return []


def load_candidates(repo_path: str) -> list[Candidate]:
    cands: list[Candidate] = []
    for path in _iter_files(repo_path):
        rel = path.relative_to(repo_path).as_posix()
        cands.extend(_detect_trailing_whitespace(path, rel))
        cands.extend(_detect_missing_eof_newline(path, rel))
        cands.extend(_detect_unpinned_action(path, rel))
    return cands
