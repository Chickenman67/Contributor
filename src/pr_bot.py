"""PR construction, caps, and GitHub REST creation."""
from __future__ import annotations
import subprocess
import tempfile
import time
from pathlib import Path
import requests
from src.scanner import Candidate
from src.state import already_tried

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
        f"Signed-off-by: {bot_account} <{bot_account}@example.com>\n"
    )


def diff_line_count(diff: str) -> int:
    return len(diff.splitlines())


def exceeds_caps(total_opened: int, repo_opened: int, diff: str) -> bool:
    return (
        total_opened >= DAILY_MAX_PRS
        or repo_opened >= PER_REPO_MAX
        or diff_line_count(diff) > MAX_DIFF_LINES
    )


def is_duplicate(state: dict, branch: str, title: str) -> bool:
    return already_tried(state, branch, title)


def run_git(args: list[str], cwd: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=120
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def apply_patch_via_git(cwd: str, patch_text: str) -> bool:
    if "--- " not in patch_text and "diff --git" not in patch_text:
        return False
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".patch", delete=False, encoding="utf-8"
    ) as f:
        f.write(patch_text)
        patch_path = f.name
    try:
        rc, _ = run_git(["apply", "--whitespace=fix", patch_path], cwd)
        return rc == 0
    finally:
        try:
            Path(patch_path).unlink()
        except OSError:
            pass


def post_pull_request(token: str, owner: str, repo: str, title: str, head: str, base: str, body: str) -> requests.Response:
    time.sleep(2)
    backoffs = (2, 8, 30)
    resp: requests.Response | None = None
    for attempt in range(3):
        resp = requests.post(
            f"{API}/repos/{owner}/{repo}/pulls",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"title": title, "head": head, "base": base, "body": body},
            timeout=60,
        )
        if resp.status_code != 429 and not (500 <= resp.status_code < 600):
            return resp
        if attempt == 2:
            return resp
        retry_after = resp.headers.get("Retry-After") if resp.headers else None
        try:
            delay = int(str(retry_after)) if retry_after is not None else backoffs[attempt + 1]
        except (ValueError, TypeError):
            delay = backoffs[attempt + 1]
        time.sleep(delay)
    assert resp is not None
    return resp
