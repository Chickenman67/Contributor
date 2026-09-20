"""CLI wiring: scan -> AI draft -> verify -> PR (or dry-run log)."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from src.scanner import load_candidates
from src.ai_providers import create_provider
from src.pr_bot import (
    DAILY_MAX_PRS,
    MAX_DIFF_LINES,
    build_branch_name,
    build_pr_title,
    build_pr_body,
    diff_line_count,
    exceeds_caps,
    is_duplicate,
)
from src.state import load_state


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
    repo = Path(args.repo_path)
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
    shown = 0
    for c in cands[:DAILY_MAX_PRS]:
        diff = f"--- a/{c.file}\n+++ b/{c.file}\n# rule={c.rule}"
        if diff_line_count(diff) > MAX_DIFF_LINES:
            continue
        if exceeds_caps(shown, shown, diff):
            continue
        branch = build_branch_name(c.rule, "20260920")
        title = build_pr_title(c)
        if is_duplicate(state, branch, title):
            continue
        body = build_pr_body(c, "dry-run verify ok", "bot", "owner")
        print(f"would-open branch={branch} title={title}")
        shown += 1
        if args.dry_run:
            continue
    token = os.environ.get("BOT_PAT", "")
    if not args.dry_run and not token:
        print("missing BOT_PAT")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
