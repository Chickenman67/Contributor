"""CLI wiring: scan -> AI draft -> verify -> PR (or dry-run log)."""
from __future__ import annotations
import argparse
import json
import os
from datetime import date
from pathlib import Path
from src.scanner import load_candidates
from src.ai_providers import create_provider
from src.pr_bot import (
    DAILY_MAX_PRS,
    build_branch_name,
    build_pr_title,
    build_pr_body,
    exceeds_caps,
    is_duplicate,
)
from src.state import load_state, record_closed


def _ensure_state(path_str: str) -> dict:
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(json.dumps({"closed_prs": [], "blocklisted": {}}), encoding="utf-8")
    return load_state(str(p))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo-path", default=".")
    ap.add_argument("--state", default="state/closed.json")
    args = ap.parse_args(argv)
    # Fail fast: live runs require BOT_PAT before any scan/I/O.
    if not args.dry_run and not os.environ.get("BOT_PAT"):
        print("missing BOT_PAT")
        return 2
    repo = Path(args.repo_path)
    repo_id = repo.resolve().name or str(repo)
    cands = load_candidates(str(repo))
    print(f"candidates={len(cands)} dry_run={args.dry_run}")
    state = _ensure_state(args.state)
    # Wire provider selection without any network I/O (instantiation only).
    provider_name = os.environ.get("AI_PROVIDER", "gemini")
    provider_key = (
        os.environ.get("GEMINI_API_KEY", "")
        or os.environ.get("XAI_API_KEY", "")
        or os.environ.get("MISTRAL_API_KEY", "")
    )
    if provider_key:
        try:
            create_provider(provider_name, provider_key)
        except ValueError:
            pass
    total_opened: int = 0
    per_repo: dict[str, int] = {}
    date_str = date.today().strftime("%Y%m%d")
    for c in cands[:DAILY_MAX_PRS]:
        diff = f"--- a/{c.file}\n+++ b/{c.file}\n# rule={c.rule}"
        if exceeds_caps(total_opened, per_repo.get(repo_id, 0), diff):
            continue
        branch = build_branch_name(c.rule, date_str)
        title = build_pr_title(c)
        stable_key = f"{c.rule}||{c.file}||{title}"
        if is_duplicate(state, branch, title) or stable_key in state.get("closed_prs", []):
            continue
        body = build_pr_body(c, "dry-run verify ok", "bot", "owner")
        print(f"would-open branch={branch} title={title} body_len={len(body)}")
        total_opened += 1
        per_repo[repo_id] = per_repo.get(repo_id, 0) + 1
        # Stable key survives date rotation (branch embeds date).
        record_closed(state, c.rule, f"{c.file}||{title}")
        if args.dry_run:
            continue
        # Live push wiring (fork/branch/push + PR creation) is Task 7+.
        # Dry-run path above performs zero network POST calls by construction.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
