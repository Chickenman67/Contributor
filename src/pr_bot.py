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
