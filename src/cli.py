"""CLI wiring: scan -> AI draft -> verify -> PR (or dry-run log)."""
from __future__ import annotations
import argparse
import json
import os
from datetime import date
from pathlib import Path
import yaml
from src.scanner import load_candidates
from src.ai_providers import create_provider
from src.pr_bot import (
    DAILY_MAX_PRS,
    MAX_DIFF_LINES,
    apply_patch_via_git,
    build_branch_name,
    build_pr_body,
    build_pr_title,
    diff_line_count,
    exceeds_caps,
    is_duplicate,
    post_pull_request,
    run_git,
)
from src.state import load_state, record_closed, save_state

ALLOWED_REPOS = {"Chickenman67/Contributor"}


def _ensure_state(path_str: str) -> dict:
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(json.dumps({"closed_prs": [], "blocklisted": {}}), encoding="utf-8")
    return load_state(str(p))


def _load_ai_config() -> dict:
    try:
        with open("config/ai.yaml", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except OSError:
        return {}


def _provider_order(cfg: dict) -> list[str]:
    active = str(cfg.get("active", os.environ.get("AI_PROVIDER", "gemini")))
    fallbacks = cfg.get("fallback_order", [active]) or [active]
    order = [active] + [p for p in fallbacks if p != active]
    seen: list[str] = []
    for p in order:
        if p not in seen:
            seen.append(p)
    return seen


def _api_key_for(provider: str) -> str:
    mapping = {
        "gemini": "GEMINI_API_KEY",
        "grok": "XAI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
    }
    return os.environ.get(mapping.get(provider, ""), "")


def _deterministic_fix(target: Path, rule: str) -> bool:
    """Fix trivial rules without AI. Returns True if the file changed."""
    try:
        if rule == "trailing-whitespace":
            lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
            fixed = [
                (ln.rstrip("\r\n").rstrip() + "\n") if ln.strip() else ln
                for ln in lines
            ]
            if fixed != lines:
                target.write_text("".join(fixed), encoding="utf-8")
                return True
            return False
        if rule == "missing-eof-newline":
            raw = target.read_bytes()
            if raw and not raw.endswith(b"\n"):
                target.write_bytes(raw + b"\n")
                return True
            return False
    except (OSError, UnicodeDecodeError):
        return False
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo-path", default=".")
    ap.add_argument("--state", default="state/closed.json")
    args = ap.parse_args(argv)
    # Fail fast: live runs require BOT_PAT before any scan/I/O.
    token = os.environ.get("BOT_PAT", "")
    if not args.dry_run and not token:
        print("missing BOT_PAT")
        return 2
    repo = Path(args.repo_path)
    repo_id = repo.resolve().name or str(repo)
    cands = load_candidates(str(repo))
    print(f"candidates={len(cands)} dry_run={args.dry_run}")
    state = _ensure_state(args.state)
    # Wire provider selection without any network I/O (instantiation only).
    cfg = _load_ai_config()
    provider_name = os.environ.get("AI_PROVIDER", str(cfg.get("active", "gemini")))
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
    if args.dry_run:
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
        return 0

    # Live path: own repo only. Never PR external repos.
    full = os.environ.get("GITHUB_REPOSITORY", "Chickenman67/Contributor")
    if full not in ALLOWED_REPOS:
        print(f"live refused for {full}: only {sorted(ALLOWED_REPOS)} allowed")
        return 2
    owner, repo_name = full.split("/", 1)
    base = "master"
    try:
        with open("config/repos.yaml", encoding="utf-8") as f:
            repos_cfg = yaml.safe_load(f) or {}
        for r in repos_cfg.get("repos", []):
            if f"{r.get('owner')}/{r.get('repo')}" == full:
                base = str(r.get("base", base))
    except OSError:
        pass
    bot_account = os.environ.get("BOT_ACCOUNT", "Chickenman67")
    total_opened = 0
    per_repo = 0
    date_str = date.today().strftime("%Y%m%d")
    order = _provider_order(cfg)
    cwd = str(repo)
    for c in cands:
        if total_opened >= DAILY_MAX_PRS or per_repo >= 1:
            break
        target = Path(cwd) / c.file
        try:
            file_text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        diff: str | None = None
        if c.rule in ("trailing-whitespace", "missing-eof-newline"):
            if not _deterministic_fix(target, c.rule):
                print(f"skip {c.file}: already fixed")
                continue
            rc, _diff = run_git(["diff", "--", c.file], cwd)
            run_git(["checkout", "--", c.file], cwd)
            if rc != 0 or not _diff.strip():
                print(f"skip {c.file}: empty diff after deterministic fix")
                continue
            diff = _diff
            print(f"deterministic fix for {c.file} ({c.rule})")
        else:
            for pname in order:
                key = _api_key_for(pname)
                if not key:
                    print(f"provider {pname}: skipped (no key)")
                    continue
                try:
                    provider = create_provider(pname, key)
                    diff = provider.generate_fix(c, file_text[:8000])
                except Exception as e:  # noqa: BLE001 - network/SDK errors skip to next provider
                    print(f"provider {pname} error: {e}")
                    continue
                if diff:
                    break
                print(f"provider {pname}: no diff ({provider.last_error[:150]})")
            if not diff:
                print(f"skip {c.file}: no AI diff")
                continue
        if exceeds_caps(total_opened, per_repo, diff):
            print(f"skip {c.file}: over caps/diff size")
            continue
        branch = build_branch_name(c.rule, date_str)
        title = build_pr_title(c)
        if is_duplicate(state, branch, title) or any(
            k.endswith(f"||{title}") for k in state.get("closed_prs", [])
        ):
            continue
        rc, _ = run_git(["checkout", "-b", branch], cwd)
        if rc != 0:
            run_git(["checkout", branch], cwd)
            print(f"skip {c.file}: branch exists")
            continue
        if not apply_patch_via_git(cwd, diff):
            print(f"skip {c.file}: patch did not apply")
            run_git(["checkout", base], cwd)
            run_git(["branch", "-D", branch], cwd)
            continue
        rc, stat = run_git(["diff", "--stat"], cwd)
        verify_log = stat[:2000] if rc == 0 else "verify: diff stat unavailable"
        rc, full_diff = run_git(["diff"], cwd)
        if rc != 0 or not full_diff.strip() or diff_line_count(full_diff) > MAX_DIFF_LINES:
            print(f"skip {c.file}: empty/oversize real diff")
            run_git(["checkout", base], cwd)
            run_git(["branch", "-D", branch], cwd)
            continue
        body = build_pr_body(c, verify_log, bot_account, owner)
        run_git(["add", c.file], cwd)
        rc, _ = run_git(["commit", "-m", title], cwd)
        if rc != 0:
            print(f"skip {c.file}: commit failed")
            run_git(["checkout", base], cwd)
            run_git(["branch", "-D", branch], cwd)
            continue
        rc, out = run_git(["push", "origin", branch], cwd)
        if rc != 0:
            print(f"push failed for {branch}: {out[-500:]}")
            run_git(["checkout", base], cwd)
            continue
        try:
            resp = post_pull_request(token, owner, repo_name, title, branch, base, body)
        except Exception as e:  # noqa: BLE001
            print(f"PR POST error: {e}")
            run_git(["checkout", base], cwd)
            break
        if resp.status_code == 201:
            print(f"opened PR: {title} ({branch})")
            record_closed(state, branch, title)
            total_opened += 1
            per_repo += 1
        else:
            print(f"PR POST {resp.status_code}: {resp.text[:500]}")
            record_closed(state, branch, title)
            if resp.status_code in (429, 422) or 500 <= resp.status_code < 600:
                run_git(["checkout", base], cwd)
                break
        run_git(["checkout", base], cwd)
    save_state(args.state, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
