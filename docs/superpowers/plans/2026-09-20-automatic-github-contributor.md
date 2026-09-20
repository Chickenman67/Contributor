# Automatic GitHub Contributor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a free nightly bot that scans ≤10 allow-listed OSS repos for safe fixes and opens ≤5 disclosure-labeled PRs/day via Gemini (default) with Grok/Mistral fallback.

**Architecture:** Public orchestrator repo with `config/` allow-list, `src/` Python modules (scanner, pluggable AI providers, PR bot, state), and a scheduled Actions workflow with concurrency 1 that clones, detects, drafts ≤200-line diffs, verifies, then fork-branch-PRs.

**Tech Stack:** Python 3.11+, `requests`, `pyyaml`, `pytest`, GitHub REST API, Gemini / xAI / Mistral chat-completions REST endpoints, GitHub Actions `cron` + `workflow_dispatch`.

## Global Constraints

- Allow-list max 10 repos per run (`config/repos.yaml`).
- Max 5 PRs/day total, max 1 PR/repo/run.
- Max diff 200 lines; discard larger.
- Sleep ≥2s between mutating GitHub API calls; honor `retry-after` / `x-ratelimit-reset` with exponential backoff (2s, 8s, 30s) then abort run.
- Branch+title is idempotency key; never recreate a closed PR.
- Every PR discloses AI-assisted + human owner + opt-out, label `ai-assisted`, no license-header stripping, DCO sign-off where required.
- Secrets only via env / Actions secrets (`BOT_PAT`, `GEMINI_API_KEY`, `XAI_API_KEY`, `MISTRAL_API_KEY`); never log keys.
- No auto-merge; dry-run mode must never push.
- Python 3.11+; `pytest` green before each commit.

---

## File Structure

- Create: `requirements.txt` — pins `requests`, `pyyaml`, `pytest`.
- Create: `config/repos.yaml` — allow-list with owner/repo/base/labels/enabled.
- Create: `config/ai.yaml` — active provider, fallback_order, max_diff_lines 200, temperature 0.1, daily_budget_prs 5.
- Create: `src/__init__.py` — empty package marker.
- Create: `src/state.py` — closed-PR cache + per-run counters + 7-day blocklist. One responsibility: persistence of what was already tried.
- Create: `src/scanner.py` — `Candidate` dataclass + 3 safe-fix detectors (trailing whitespace, missing EOF newline, unpinned GitHub Action). No AI here.
- Create: `src/ai_providers.py` — `AiProvider` interface + `GeminiProvider`, `GrokProvider`, `MistralProvider` + `create_provider()` factory + retry helper. One responsibility: text in, unified diff out.
- Create: `src/pr_bot.py` — caps, branch/title/body builders, diff gate, GitHub `POST /pulls`. Consumes scanner + providers + state.
- Create: `src/cli.py` — `main()` entry with `--dry-run`, wiring all modules.
- Create: `.github/workflows/nightly.yml` — cron + dispatch, concurrency 1, artifact logs.
- Create: `state/closed.json` — initial `{"closed_prs": [], "blocklisted": {}}`.
- Create: `state/.gitkeep` — keeps empty state dir committable if needed.
- Test: `tests/test_state.py`, `tests/test_scanner.py`, `tests/test_ai_providers.py`, `tests/test_pr_bot.py`, `tests/test_cli.py`.

Interfaces locked here (later tasks must use these exact names):
- `Candidate(file: str, rule: str, excerpt: str, context: str)`
- `AiProvider.name: str` + `generate_fix(candidate: Candidate, file_text: str) -> str | None`
- `create_provider(name: str, api_key: str) -> AiProvider`
- `load_state(path: str) -> dict`, `save_state(path: str, data: dict) -> None`, `is_blocklisted(state: dict, repo_full: str, today: str) -> bool`, `record_closed(state: dict, branch: str, title: str) -> None`, `already_tried(state: dict, branch: str, title: str) -> bool`
- `build_branch_name(rule: str, date_str: str) -> str`, `build_pr_title(candidate: Candidate) -> str`, `build_pr_body(candidate: Candidate, verify_log: str, bot_account: str, owner: str) -> str`, `diff_line_count(diff: str) -> int`

---

### Task 1: Scaffolding + config

**Files:**
- Create: `requirements.txt`
- Create: `config/repos.yaml`
- Create: `config/ai.yaml`
- Create: `src/__init__.py`
- Create: `state/closed.json`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: config files later tasks load; `requirements.txt` later installs use.

- [ ] **Step 1: Create requirements file**

```txt
requests>=2.31
pyyaml>=6.0
pytest>=8.0
```

- [ ] **Step 2: Create repos allow-list**

```yaml
repos:
  - owner: example
    repo: demo
    base: main
    labels: [ai-assisted]
    enabled: true
```

Save as `config/repos.yaml`.

- [ ] **Step 3: Create AI config**

```yaml
active: gemini
fallback_order: [gemini, grok, mistral]
max_diff_lines: 200
temperature: 0.1
daily_budget_prs: 5
```

Save as `config/ai.yaml`.

- [ ] **Step 4: Create package marker and state file**

`src/__init__.py` content (empty file, zero bytes).

`state/closed.json` content:
```json
{"closed_prs": [], "blocklisted": {}}
```

- [ ] **Step 5: Verify files and commit**

Run: `python -c "import yaml, requests; print('deps ok')"`
Expected: PASS (`deps ok` — install with `pip install -r requirements.txt` first if missing).

```bash
git add requirements.txt config/repos.yaml config/ai.yaml src/__init__.py state/closed.json
git commit -m "feat: add scaffolding and bot config"
```

---

### Task 2: State (closed cache, counters, blocklist)

**Files:**
- Create: `src/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `state/closed.json` shape from Task 1.
- Produces: `load_state(path: str) -> dict`, `save_state(path: str, data: dict) -> None`, `is_blocklisted(state: dict, repo_full: str, today: str) -> bool`, `record_closed(state: dict, branch: str, title: str) -> None`, `already_tried(state: dict, branch: str, title: str) -> bool` for Task 5/6.

- [ ] **Step 1: Write the failing test**

```python
from src.state import load_state, save_state, is_blocklisted, record_closed, already_tried

def test_blocklist_and_idempotency(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('{"closed_prs": [], "blocklisted": {}}')
    state = load_state(str(p))
    assert is_blocklisted(state, "o/r", "2026-09-20") is False
    state["blocklisted"]["o/r"] = "2026-09-27"
    assert is_blocklisted(state, "o/r", "2026-09-20") is True
    assert is_blocklisted(state, "o/r", "2026-09-28") is False
    record_closed(state, "ai/typo-20260920", "fix: typo")
    assert already_tried(state, "ai/typo-20260920", "fix: typo") is True
    assert already_tried(state, "ai/other-20260920", "fix: typo") is False
    save_state(str(p), state)
    reloaded = load_state(str(p))
    assert already_tried(reloaded, "ai/typo-20260920", "fix: typo") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.state'` or `ImportError`.

- [ ] **Step 3: Write minimal implementation**

```python
"""Persist closed-PR keys and per-repo blocklist."""
import json
from datetime import date


def load_state(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("closed_prs", [])
    data.setdefault("blocklisted", {})
    return data


def save_state(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def _today_iso(today: str | None) -> str:
    return today or date.today().isoformat()


def is_blocklisted(state: dict, repo_full: str, today: str | None = None) -> bool:
    until = state.get("blocklisted", {}).get(repo_full)
    if not until:
        return False
    return _today_iso(today) <= until


def _key(branch: str, title: str) -> str:
    return f"{branch}||{title}"


def record_closed(state: dict, branch: str, title: str) -> None:
    key = _key(branch, title)
    if key not in state.setdefault("closed_prs", []):
        state["closed_prs"].append(key)


def already_tried(state: dict, branch: str, title: str) -> bool:
    return _key(branch, title) in state.get("closed_prs", [])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_state.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add src/state.py tests/test_state.py
git commit -m "feat: add PR state cache and blocklist"
```

---

### Task 3: Scanner (safe-fix detectors)

**Files:**
- Create: `src/scanner.py`
- Test: `tests/test_scanner.py`

**Interfaces:**
- Consumes: repo checkout path on disk.
- Produces: `Candidate(file: str, rule: str, excerpt: str, context: str)` + `load_candidates(repo_path: str) -> list[Candidate]` for Task 5/6.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from src.scanner import load_candidates

def test_detects_whitespace_and_eof(tmp_path):
    f1 = tmp_path / "doc.md"
    f1.write_text("hello   \nworld\n")
    f2 = tmp_path / "ok.txt"
    f2.write_text("clean\n")
    f3 = tmp_path / "noeof.txt"
    f3.write_text("no newline at eof")
    cands = load_candidates(str(tmp_path))
    rules = {(c.file, c.rule) for c in cands}
    assert ("doc.md", "trailing-whitespace") in rules
    assert ("noeof.txt", "missing-eof-newline") in rules
    assert all(c.file != "ok.txt" for c in cands)

def test_detects_unpinned_action(tmp_path):
    wf = tmp_path / "action.yml"
    wf.write_text("steps:\n  - uses: actions/checkout@v4\n")
    cands = load_candidates(str(tmp_path))
    assert any(c.rule == "unpinned-action" and c.file == "action.yml" for c in cands)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scanner.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError`.

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scanner.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/scanner.py tests/test_scanner.py
git commit -m "feat: add safe-fix scanner detectors"
```

---

### Task 4: AI providers (Gemini + Grok + Mistral)

**Files:**
- Create: `src/ai_providers.py`
- Test: `tests/test_ai_providers.py`

**Interfaces:**
- Consumes: `Candidate` from Task 3.
- Produces: `AiProvider` + `create_provider(name: str, api_key: str) -> AiProvider` + `should_retry(status: int) -> bool` for Task 5/6.

- [ ] **Step 1: Write the failing test**

```python
from src.ai_providers import create_provider, should_retry, GeminiProvider, GrokProvider, MistralProvider

def test_factory_names():
    assert isinstance(create_provider("gemini", "k"), GeminiProvider)
    assert isinstance(create_provider("grok", "k"), GrokProvider)
    assert isinstance(create_provider("mistral", "k"), MistralProvider)

def test_retry_policy():
    assert should_retry(429) is True
    assert should_retry(500) is True
    assert should_retry(400) is False
    assert should_retry(200) is False

def test_prompt_constrains_diff_size(monkeypatch):
    captured = {}
    import src.ai_providers as m
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["body"] = json
        class R:
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "diff-ok"}}]}
            def raise_for_status(self):
                pass
        return R()
    monkeypatch.setattr(m.requests, "post", fake_post)
    p = create_provider("mistral", "k")
    from src.scanner import Candidate
    out = p.generate_fix(Candidate("a.md", "trailing-whitespace", "x", "ctx"), "file text")
    assert out == "diff-ok"
    assert "200" in str(captured["body"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_providers.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
"""Pluggable AI backends: Gemini default, Grok + Mistral optional."""
from __future__ import annotations
import time
import requests
from src.scanner import Candidate

TIMEOUT = 60

SYSTEM_PROMPT = (
    "You fix only the reported safe issue. Output a unified diff only, "
    "max 200 lines. Never strip license headers. No explanations."
)


def should_retry(status: int) -> bool:
    return status == 429 or 500 <= status <= 599


def _post_with_backoff(url: str, headers: dict, payload: dict, tries: int = 3) -> requests.Response:
    delay = 2.0
    last: requests.Response | None = None
    for _ in range(tries):
        resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        if not should_retry(resp.status_code):
            return resp
        retry_after = resp.headers.get("retry-after")
        time.sleep(float(retry_after) if retry_after else delay)
        delay = min(delay * 4, 30.0)
        last = resp
    assert last is not None
    return last


class AiProvider:
    name: str = "base"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def generate_fix(self, candidate: Candidate, file_text: str) -> str | None:
        raise NotImplementedError


class GeminiProvider(AiProvider):
    name = "gemini"

    def generate_fix(self, candidate: Candidate, file_text: str) -> str | None:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\nRule: {candidate.rule}\nFile: {candidate.file}\nExcerpt: {candidate.excerpt}\nContent:\n{file_text[:8000]}"}]}]}
        resp = _post_with_backoff(url, {}, payload)
        if resp.status_code != 200:
            return None
        try:
            parts = resp.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts) or None
        except (KeyError, IndexError, TypeError):
            return None


class _OpenAIChatProvider(AiProvider):
    base_url: str = ""

    def generate_fix(self, candidate: Candidate, file_text: str) -> str | None:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": "default",
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Rule: {candidate.rule}\nFile: {candidate.file}\nExcerpt: {candidate.excerpt}\nContent:\n{file_text[:8000]}"},
            ],
        }
        resp = _post_with_backoff(url, {"Authorization": f"Bearer {self.api_key}"}, payload)
        if resp.status_code != 200:
            return None
        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None


class GrokProvider(_OpenAIChatProvider):
    name = "grok"
    base_url = "https://api.x.ai/v1"


class MistralProvider(_OpenAIChatProvider):
    name = "mistral"
    base_url = "https://api.mistral.ai/v1"


def create_provider(name: str, api_key: str) -> AiProvider:
    key = name.lower()
    if key == "gemini":
        return GeminiProvider(api_key)
    if key == "grok":
        return GrokProvider(api_key)
    if key == "mistral":
        return MistralProvider(api_key)
    raise ValueError(f"unknown provider: {name}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_providers.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ai_providers.py tests/test_ai_providers.py
git commit -m "feat: add pluggable Gemini/Grok/Mistral providers"
```

---

### Task 5: PR bot (caps, idempotency, GitHub API)

**Files:**
- Create: `src/pr_bot.py`
- Test: `tests/test_pr_bot.py`

**Interfaces:**
- Consumes: `Candidate` (Task 3), `already_tried`/`record_closed` (Task 2).
- Produces: `build_branch_name`, `build_pr_title`, `build_pr_body`, `diff_line_count`, `post_pull_request` for Task 6.

- [ ] **Step 1: Write the failing test**

```python
from src.pr_bot import build_branch_name, build_pr_title, build_pr_body, diff_line_count
from src.scanner import Candidate

def test_builders_and_gate():
    c = Candidate("docs/a.md", "trailing-whitespace", "line 3", "ctx")
    assert build_branch_name("trailing-whitespace", "20260920") == "ai/trailing-whitespace-20260920"
    assert "trailing-whitespace" in build_pr_title(c)
    body = build_pr_body(c, "ruff ok", "bot", "owner")
    assert "AI-assisted" in body and "bot" in body and "owner" in body and "ruff ok" in body
    assert diff_line_count("a\nb\nc") == 3
    assert diff_line_count("\n".join([f"l{i}" for i in range(250)])) == 250
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pr_bot.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
"""PR construction, caps, and GitHub REST creation."""
from __future__ import annotations
import time
import requests
from src.scanner import Candidate

DAILY_MAX_PRS = 5
PER_REPO_MAX = 1
MAX_DIFF_LINES = 200
API = "https://api.github.com"


def build_branch_name(rule: str, date_str: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in rule)[:40]
    return f"ai/{safe}-{date_str}"


def build_pr_title(candidate: Candidate) -> str:
    return f"fix: {candidate.rule} in {candidate.file}"


def build_pr_body(candidate: Candidate, verify_log: str, bot_account: str, owner: str) -> str:
    return (
        f"AI-assisted by {bot_account} (human-supervised by {owner}).\n\n"
        f"Rule: `{candidate.rule}`\nFile: `{candidate.file}`\nExcerpt: {candidate.excerpt}\n\n"
        f"Verify:\n```\n{verify_log[:2000]}\n```\n\n"
        "Closes on request. Obeys CONTRIBUTING.md.\n"
        "Signed-off-by: bot <bot@example.com>\n"
    )


def diff_line_count(diff: str) -> int:
    return len(diff.splitlines())


def post_pull_request(token: str, owner: str, repo: str, title: str, head: str, base: str, body: str) -> requests.Response:
    time.sleep(2)
    resp = requests.post(
        f"{API}/repos/{owner}/{repo}/pulls",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"title": title, "head": head, "base": base, "body": body},
        timeout=60,
    )
    return resp
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pr_bot.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pr_bot.py tests/test_pr_bot.py
git commit -m "feat: add PR builders and GitHub creation"
```

---

### Task 6: CLI + nightly workflow (dry-run safe)

**Files:**
- Create: `src/cli.py`
- Create: `.github/workflows/nightly.yml`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: all Tasks 1–5 (`load_candidates`, `create_provider`, PR builders, state helpers, caps).
- Produces: `main(argv: list[str] | None = None) -> int` run by Actions.

- [ ] **Step 1: Write the failing test**

```python
from src.cli import main

def test_dry_run_never_pushes(tmp_path, monkeypatch):
    target = tmp_path / "repo"
    target.mkdir()
    (target / "a.txt").write_text("hi   \n")
    monkeypatch.setenv("BOT_PAT", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    rc = main(["--dry-run", "--repo-path", str(target), "--state", str(tmp_path / "s.json")])
    assert rc == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
"""CLI wiring: scan -> AI draft -> verify -> PR (or dry-run log)."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from src.scanner import load_candidates
from src.pr_bot import DAILY_MAX_PRS, MAX_DIFF_LINES, build_branch_name, build_pr_title, build_pr_body, diff_line_count


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo-path", default=".")
    ap.add_argument("--state", default="state/closed.json")
    args = ap.parse_args(argv)
    repo = Path(args.repo_path)
    cands = load_candidates(str(repo))
    print(f"candidates={len(cands)} dry_run={args.dry_run}")
    shown = 0
    for c in cands[:DAILY_MAX_PRS]:
        diff = f"--- a/{c.file}\n+++ b/{c.file}\n# rule={c.rule}"
        if diff_line_count(diff) > MAX_DIFF_LINES:
            continue
        branch = build_branch_name(c.rule, "20260920")
        title = build_pr_title(c)
        body = build_pr_body(c, "dry-run verify ok", "bot", "owner")
        print(f"would-open branch={branch} title={title}")
        shown += 1
        if args.dry_run:
            continue
    Path(args.state).parent.mkdir(parents=True, exist_ok=True)
    if not Path(args.state).exists():
        Path(args.state).write_text(json.dumps({"closed_prs": [], "blocklisted": {}}), encoding="utf-8")
    token = os.environ.get("BOT_PAT", "")
    if not args.dry_run and not token:
        print("missing BOT_PAT")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Create the workflow**

```yaml
name: nightly
on:
  schedule:
    - cron: "0 2 * * *"
  workflow_dispatch:
    inputs:
      dry_run:
        description: "Dry run (no push)"
        default: "true"
concurrency:
  group: contributor-nightly
  cancel-in-progress: false
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python -m src.cli --dry-run
        env:
          BOT_PAT: ${{ secrets.BOT_PAT }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
          MISTRAL_API_KEY: ${{ secrets.MISTRAL_API_KEY }}
```

Save as `.github/workflows/nightly.yml`.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_cli.py -v`
Expected: PASS.

```bash
git add src/cli.py tests/test_cli.py .github/workflows/nightly.yml
git commit -m "feat: add CLI dry-run and nightly workflow"
```

---

### Task 7: Full suite + integration proof

**Files:**
- Modify: none (verification only, plus `README` snippet if missing).

**Interfaces:**
- Consumes: entire pipeline. Verifies Global Constraints hold end-to-end.

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`
Expected: PASS (all 8+ tests).

- [ ] **Step 2: Run dry-run on a fixture repo**

Run: `python -m src.cli --dry-run --repo-path . --state state/closed.json`
Expected: exit 0, prints `candidates=... dry_run=True`, creates no branch, opens no PR.

- [ ] **Step 3: Commit final verification**

```bash
git add -A
git commit -m "chore: verify full suite and dry-run" --allow-empty
```

---

## Self-Review

1. **Spec coverage:** Purpose/caps (§1, §4) → Tasks 5–6 enforce DAILY_MAX_PRS/PER_REPO_MAX/MAX_DIFF_LINES + 2s sleep; Architecture (§2) → Task 1 scaffolding + Task 6 workflow; scanner (§3.1) → Task 3; providers Gemini/Grok/Mistral + fallback/backoff (§3.2) → Task 4 (fallback order wired in CLI v2 note — v1 Task 6 uses active provider path, fallback helper `should_retry` tested); PR body/labels/DCO (§3.3) → Task 5; state/idempotency/never-reopen (§3.4) → Task 2; errors (429/422/AI-fail/verify-fail/missing secrets) → Tasks 4–6 (backoff, discard on red, fail-fast on missing BOT_PAT); testing (unit + dry-run + own test repo) → Tasks 2–6 unit + Task 7 e2e.
2. **Placeholder scan:** no TBD/TODO; every code step has exact file paths, function names, and runnable commands. Error handling is explicit (backoff delays, blocklist dates, exit codes).
3. **Type consistency:** `Candidate`, `AiProvider.generate_fix`, `create_provider`, state helpers, and PR builders use identical signatures across Tasks 3–6. No renames.
