# Automatic GitHub Contributor — Design (v1)

**Date:** 2026-09-20
**Status:** Approved in brainstorming, pending spec review
**Scope:** Few favorite OSS repos, safe fixes only, Python, scheduled Actions, Gemini default + Grok + Mistral optional
**Research basis:** `research-automatic-github-contributor.md`

## 1. Purpose & Success Criteria

Build a free, low-volume bot that improves a hand-picked allow-list of OSS repos with safe, verifiable fixes and opens human-reviewable PRs without tripping free-tier quotas or GitHub spam policy.

Success for v1:
- Nightly run processes ≤10 allow-listed repos, opens ≤5 PRs/day total, ≤1 per repo.
- All PRs are safe-fix class, ≤200 lines, CI/lint green before push, with disclosure + repro.
- Zero account warnings; any 429/422-spam stops the run and blocklists the repo.
- Dry-run mode works without pushing; integration test on own test repo passes.

Non-goals (v1): mass scanning hundreds of repos, deep refactors/security rewrites, paid inference, GitHub App distribution, auto-merge.

## 2. Architecture (Approved)

Public orchestrator repo (yours) containing config + Python bot + scheduled workflow.

```
config/repos.yaml      # allow-list: owner/repo, base branch, labels, max 1 PR
config/ai.yaml         # provider selection + fallback order + budgets
src/scanner.py         # clone + safe-fix detectors
src/ai_fix.py          # provider interface: gemini.py, grok.py, mistral.py
src/pr_bot.py          # verify + fork-branch-push + POST /pulls
src/state.py           # closed-PR cache + per-run counters
.github/workflows/nightly.yml  # cron + workflow_dispatch, concurrency 1
tests/                 # unit + dry-run integration
```

Flow: cron → shallow clone allow-list → detectors emit candidates → active AI provider drafts minimal unified diff → local verify (lint/tests) → skip if red → check branch+title idempotency + closed cache → fork → branch `ai/<rule>-<yyyymmdd>` → push → `POST /repos/{owner}/{repo}/pulls` via PAT secret → label `ai-assisted`.

Auth v1: fine-grained or classic PAT stored as Actions secret (`BOT_PAT`), minimal scopes. GitHub App is deferred to v2 (opt-in distribution).

## 3. Components

### 3.1 scanner.py — safe-fix detectors only
- codespell/typo scan (docs + comments), dead markdown links, formatting (ruff/black --check equivalent), pinned GitHub Action SHAs, obvious lint (trailing whitespace, EOF newline).
- Emits: `{file, rule, excerpt, suggested_hunk_context}`. No functional changes.
- Each detector is isolated: `detect_<rule>(repo_path) -> list[Candidate]`, independently testable.

### 3.2 ai_fix.py — pluggable providers
Interface: `generate_fix(candidate, file_context) -> unified_diff | None`

- `config/ai.yaml`:
  ```yaml
  active: gemini
  fallback_order: [gemini, grok, mistral]
  max_diff_lines: 200
  temperature: 0.1
  daily_budget_prs: 5
  ```
- Backends:
  - **Gemini** (default, free tier): per-project RPM/TPM/RPD, RPD resets midnight Pacific. Env: `GEMINI_API_KEY`.
  - **Grok** (xAI API, optional): own RPM/TPM caps per model/key. Env: `XAI_API_KEY`. Must confirm model + free/trial limits from xAI docs before enabling.
  - **Mistral** (La Plateforme, optional): own rate limits per key. Env: `MISTRAL_API_KEY`. Must confirm free tier from Mistral docs before enabling.
- Rules: 1 active provider per run; fallback only on 429/5xx/auth-fail to next in `fallback_order`. Each backend honors `retry-after` + exponential backoff, 20 req/min ceiling default, prompt constrained to safe-fix class + ≤200 lines + no license-header stripping.

### 3.3 pr_bot.py — verify + PR
- Runs target's fast checks if present (e.g., `ruff`, `codespell`, markdown link check); discards diff on failure.
- Idempotency: branch name + PR title as cache key; never recreate closed PR (persist `state/closed.json` in orchestrator repo or Actions cache).
- PR body must include: `AI-assisted by {bot_account} (human-supervised by {owner})`, rule name, repro/verify log, `Closes on request`, DCO `Signed-off-by` where repo requires it, no stripping of license headers.
- Labels: `ai-assisted`. Obeys `CONTRIBUTING.md` / templates per repo config.

### 3.4 state.py + config
- `config/repos.yaml` example:
  ```yaml
  repos:
    - owner: example
      repo: demo
      base: main
      labels: [ai-assisted]
      enabled: true
  ```
- Per-run counters: total PRs, per-repo PRs. Hard stop at caps.

## 4. Data Flow + Guardrails

1. Load `repos.yaml` + `ai.yaml`, init counters.
2. For each enabled repo (≤10): shallow clone default/base branch.
3. Run detectors → ranked candidates (typos/links/lint first).
4. For top candidate(s): call active provider → diff → verify → if green and under caps, check idempotency/closed cache → fork/branch/push → open PR.
5. Sleep ≥2s between mutating API calls. Honor `x-ratelimit-*` / `retry-after`. Stop run on 429 exhaustion or 422-spam signal.
6. Log every decision (skip reasons) as Actions artifacts.

Caps enforced in code, not just config: `DAILY_MAX_PRS=5`, `PER_REPO_MAX=1`, `MAX_DIFF_LINES=200`, `SEARCH_CALLS ≤10/min`.

## 5. Error Handling

- 429/rate-limit: exponential backoff (2s, 8s, 30s), then abort run gracefully (exit 0 with `rate_limited=true` output, no retry storm).
- 422 validation/spam on PR create: mark repo blocklisted for 7 days in `state/`, stop further PRs that run, open no issue/comment.
- AI empty/invalid/oversize diff: discard, log `ai_rejected`, try next candidate (max 3 candidates/repo/run).
- Verify red: discard diff, never push.
- Missing secrets (`BOT_PAT`, provider key): fail fast with clear message before any clone.
- First-time-contributor fork restrictions: use fork + PR flow; if fork PR blocked, log and skip.

## 6. Testing

- Unit: idempotency keys, cap enforcement, provider backoff/fallback selection, diff-size gate, closed-cache never-reopen.
- Dry-run: `python -m src.pr_bot --dry-run` clones + detects + drafts but never pushes; asserts log output.
- Integration: own `test-target` repo with intentional typos; nightly workflow in `dry-run` must produce expected diff artifact, live run opens 1 PR.
- Manual gate v1: no auto-merge; human merges upstream.

## 7. Ops / Security

- Secrets only via Actions secrets; never log keys or full diffs with tokens.
- Bot username/bio discloses automation. Every PR states AI-assisted + owner + opt-out.
- Respect maintainer objection/block immediately: add to `disabled_repos` and never touch again.
- License: only emit patches compatible with target license (inbound=outbound); preserve headers; add sign-off where DCO required.

## 8. Open Items Resolved in Brainstorming

- Target: few favorite OSS repos (not mass scan, not own-only).
- Fix class: safe fixes only.
- AI: Gemini default, Grok + Mistral as optional pluggable backends (keys required, limits to be confirmed from xAI/Mistral primary docs during implementation).
- Runtime: scheduled Actions.
- Stack: Python.
- Approach A chosen over self-hosted Ollama (B) and full GitHub App (C, deferred to v2).
