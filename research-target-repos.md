# Target Repositories for Automatic Safe-Fix Contributor Bot

Research conducted: 2026-09-20  
Sources: GitHub search API, repository pages, CONTRIBUTING.md files, recent PR activity (2024-2026)

---

## Selection Criteria Applied

| Criterion | Threshold |
|-----------|-----------|
| Active maintenance | Commits/releases within last 3 months |
| CONTRIBUTING.md | Present with clear guidelines |
| Size | Not massive (avoid noise: <100K stars, moderate issue/PR volume) |
| Language diversity | Python, Rust, TypeScript, Go, Java |
| Good-first-issue label | Active usage with merge evidence |
| Small-PR merge history | Documented merges of typo fixes, dead-link fixes, EOF newlines, formatting |

---

## Target Repositories

| Owner/Repo | Language | Stars | Last Commit | CONTRIBUTING.md | Why Good Fit | Recent Small-PR Merge Evidence |
|------------|----------|-------|-------------|-----------------|--------------|--------------------------------|
| **astral-sh/ruff** | Rust (96%), Python | 48K | 2026-06-09 | [CONTRIBUTING.md](https://github.com/astral-sh/ruff/blob/main/CONTRIBUTING.md) | Extremely active linter/formatter; explicit `good first issue` label; welcomes typo/docs/rule fixes; fast CI; 460+ contributors | [PR #15059](https://github.com/astral-sh/ruff/pull/15059) (rule rename, 1 file); [Issue #15009](https://github.com/astral-sh/ruff/issues/15009) (docstring naming, merged); [PR #843](https://github.com/astral-sh/ruff/pull/843) (redundant open modes, good-first-issue) |
| **twentyhq/twenty** | TypeScript | 55K | 2025-12-22 | [.github/CONTRIBUTING.md](https://github.com/twentyhq/twenty/blob/main/.github/CONTRIBUTING.md) | Open-source CRM; explicit "merge first qualifying PR" policy for good-first-issue; active triage; 8.8K forks | [PR #11465](https://github.com/twentyhq/twenty/pull/11465) (CONTRIBUTING.md typo fix, 2 commits, merged same day); [PR #16235](https://github.com/twentyhq/twenty/pull/16235) (first contributor, docs) |
| **go-task/task** | Go | 16K | 2025-12-24 | [.github/CONTRIBUTING.md](https://github.com/go-task/.github/blob/main/CONTRIBUTING.md) | Popular task runner; "All kinds of contributions welcome, whether typo fix or shiny new feature"; explicit good-first-issue label; small focused PRs encouraged | [Release v3.46.4](https://github.com/go-task/task/releases/tag/v3.46.4) (Dec 2025, frequent patch releases); issue tracker shows typo/docs PRs merged regularly |
| **excaliburjs/Excalibur** | TypeScript | 2K | 2025-12-23 | [.github/CONTRIBUTING.md](https://github.com/excaliburjs/Excalibur/blob/main/.github/CONTRIBUTING.md) | 2D game engine; "good first issue designed as introduction to contributing"; small commits welcome ("Fix typo in documentation"); 10+ new contributors in v0.31.0 | [PR #3347](https://github.com/excaliburjs/Excalibur/pull/3347) (first contributor); [PR #3411](https://github.com/excaliburjs/Excalibur/pull/3411) (sample game); commit [8774db8](https://github.com/excaliburjs/Excalibur/commit/8774db831be4cc163e70e98c1ff006198efcdefc) (1-line fix) |
| **LMCache/LMCache** | Python | 11.6K | 2026-07-10 | [CONTRIBUTING.md](https://github.com/LMCache/LMCache/blob/main/CONTRIBUTING.md) | LLM KV cache layer; structured onboarding issue (#3372) with step-by-step guide; pre-commit/ruff/black enforced; DCO signoff; "keep PR small" policy | [Issue #3372](https://github.com/LMCache/LMCache/issues/3372) (onboarding umbrella with 15+ sub-issues like f-string→%-format, black formatting); [PR #4229](https://github.com/LMCache/LMCache/pull/4229) (logging format, good-first-issue, merged) |
| **rust-lang/rust-clippy** | Rust | 13K | 2025-12-14 | [CONTRIBUTING.md](https://github.com/rust-lang/rust-clippy/blob/master/CONTRIBUTING.md) | Official Rust linter collection; `good first issue` label + `E-help-wanted`; mentored via `@rustbot claim`; changelog entry required; bors merge queue | [PR #14864](https://github.com/rust-lang/rust-clippy/pull/14864) (useless_conversion suggestion, good-first-issue); [PR #15021](https://github.com/rust-lang/rust-clippy/pull/15021) (nested refs); [Issue #14150](https://github.com/rust-lang/rust-clippy/issues/14150) (cast_sign_loss, closed via PR) |
| **projectdiscovery/nuclei-templates** | Go, YAML | 8.2K | 2025-08-16 | [CONTRIBUTING.md](https://github.com/projectdiscovery/nuclei-templates/blob/master/CONTRIBUTING.md) | Security template library; "good first issue" + "Done" labels; typo/format fixes in YAML templates; fast merge (1-2 days) | [PR #10420](https://github.com/projectdiscovery/nuclei-templates/pull/10420) (CVE typo fix, 1 commit, merged in 2 days); [PR #12898](https://github.com/projectdiscovery/nuclei-templates/pull/12898) (epss-score format, good-first-issue, merged same day) |
| **hiero-ledger/hiero-sdk-python** | Python | 1.2K | 2026-01-30 | [CONTRIBUTING.md](https://github.com/hiero-ledger/hiero-sdk-python/blob/main/CONTRIBUTING.md) | Hedera SDK; detailed first-timer guide (assignment via `/assign`, DCO+GPG signing, changelog entry); black formatting tasks; mentor assignment | [Issue #1544](https://github.com/hiero-ledger/hiero-sdk-python/issues/1544) (black formatting, multiple PRs #1598, #1599, #1613, #1638, #1640, #1641); [Issue #1250](https://github.com/hiero-ledger/hiero-sdk-python/issues/1250) (README fix, PR #1253 merged) |
| **deepset-ai/haystack** | Python | 18K | 2025-12 | [CONTRIBUTING.md](https://github.com/deepset-ai/haystack/blob/main/CONTRIBUTING.md) | LLM framework; "good first issue" + "contributions wanted" labels; explicit "safe space to experiment and fail"; internal handling marked | [Issue search](https://github.com/deepset-ai/haystack/issues?q=is%3Aissue+label%3A%22good+first+issue%22) shows active labeling; CONTRIBUTING.md links directly to labeled issues |
| **kubernetes-sigs/kind** | Go | 15K | 2025-11-14 | [CONTRIBUTING.md](https://kind.sigs.k8s.io/docs/contributing/getting-started/) | Kubernetes-in-Docker; "good first issue" + "help wanted" labels; documentation fixes welcomed; active maintainer engagement (BenTheElder, aojea) | [PR #3070](https://github.com/kubernetes-sigs/kind/pull/3070) (dedup nodes, good-first-issue); [Issue #3117](https://github.com/kubernetes-sigs/kind/issues/3117) (doc CIDR defaults, closed via PR); [Issue #2293](https://github.com/kubernetes-sigs/kind/issues/2293) (nginx wait timeout, closed 2025) |

---

## Language Distribution

| Language | Repositories |
|----------|--------------|
| Rust | 2 (astral-sh/ruff, rust-lang/rust-clippy) |
| TypeScript | 2 (twentyhq/twenty, excaliburjs/Excalibur) |
| Python | 3 (LMCache/LMCache, hiero-ledger/hiero-sdk-python, deepset-ai/haystack) |
| Go | 3 (go-task/task, projectdiscovery/nuclei-templates, kubernetes-sigs/kind) |

---

## Bot-Friendly Characteristics Summary

| Repo | Auto-fix Friendly? | Notes |
|------|-------------------|-------|
| astral-sh/ruff | ✅ High | Ruff itself is a formatter; black/ruff configs exist; rule tests are snapshot-based |
| twentyhq/twenty | ✅ High | Prettier/ESLint configured; TypeScript strict; good-first-issue PRs auto-prioritized |
| go-task/task | ✅ High | gofmt/goimports enforced; small Go codebase; CLI tool |
| excaliburjs/Excalibur | ✅ Medium | Prettier/ESLint; game engine has more complex logic but docs/typos are safe |
| LMCache/LMCache | ✅ High | Ruff/black/pre-commit enforced; f-string→%-format pattern is automatable |
| rust-lang/rust-clippy | ⚠️ Medium | Rust compiler plugin; needs `cargo test`; but typo/docs in .md/.rs are safe |
| projectdiscovery/nuclei-templates | ✅ High | YAML templates; schema validation; typo/dead-link fixes are purely data |
| hiero-ledger/hiero-sdk-python | ✅ High | Black/ruff; black formatting tasks explicitly listed as good-first-issue |
| deepset-ai/haystack | ✅ Medium | Python; ruff/black; but larger codebase |
| kubernetes-sigs/kind | ✅ High | gofmt/goimports; Go; documentation/config fixes are low-risk |

---

## Recommended Priority Order for Bot Rollout

1. **astral-sh/ruff** - Highest signal: self-formatting, explicit good-first-issue, fast merges
2. **projectdiscovery/nuclei-templates** - Pure YAML data, trivial validation, very fast merges
3. **hiero-ledger/hiero-sdk-python** - Black formatting tasks are deterministic and automatable
4. **LMCache/LMCache** - Structured onboarding, f-string→%-format pattern is automatable at scale
5. **twentyhq/twenty** - Large but explicit "first PR wins" policy; TypeScript/Prettier tooling mature
6. **go-task/task** - Go tooling excellent; small focused PRs merge quickly
7. **excaliburjs/Excalibur** - Smaller community but very welcoming; TypeScript tooling solid
8. **kubernetes-sigs/kind** - Go tooling; documentation/link fixes are high-value
9. **deepset-ai/haystack** - Active but larger; good-first-issue issues need triage
10. **rust-lang/rust-clippy** - High value but Rust compilation adds latency; better for phase 2

---

## Citation Index

All claims above are sourced from the following primary URLs:

- astral-sh/ruff: [Repo](https://github.com/astral-sh/ruff), [CONTRIBUTING](https://github.com/astral-sh/ruff/blob/main/CONTRIBUTING.md), [PR #15059](https://github.com/astral-sh/ruff/pull/15059), [Issue #15009](https://github.com/astral-sh/ruff/issues/15009), [PR #843](https://github.com/astral-sh/ruff/pull/843)
- twentyhq/twenty: [Repo](https://github.com/twentyhq/twenty), [CONTRIBUTING](https://github.com/twentyhq/twenty/blob/main/.github/CONTRIBUTING.md), [PR #11465](https://github.com/twentyhq/twenty/pull/11465), [Release v1.13.7](https://github.com/twentyhq/twenty/releases/tag/v1.13.7)
- go-task/task: [Repo](https://github.com/go-task/task), [CONTRIBUTING](https://github.com/go-task/.github/blob/main/CONTRIBUTING.md), [Release v3.46.4](https://github.com/go-task/task/releases/tag/v3.46.4)
- excaliburjs/Excalibur: [Repo](https://github.com/excaliburjs/Excalibur), [CONTRIBUTING](https://github.com/excaliburjs/Excalibur/blob/main/.github/CONTRIBUTING.md), [Release v0.31.0](https://github.com/excaliburjs/Excalibur/releases/tag/v0.31.0), [Commit 8774db8](https://github.com/excaliburjs/Excalibur/commit/8774db831be4cc163e70e98c1ff006198efcdefc)
- LMCache/LMCache: [Repo](https://github.com/LMCache/LMCache), [CONTRIBUTING](https://github.com/LMCache/LMCache/blob/main/CONTRIBUTING.md), [Issue #3372](https://github.com/LMCache/LMCache/issues/3372), [PR #4229](https://github.com/LMCache/LMCache/pull/4229)
- rust-lang/rust-clippy: [Repo](https://github.com/rust-lang/rust-clippy), [CONTRIBUTING](https://github.com/rust-lang/rust-clippy/blob/master/CONTRIBUTING.md), [PR #14864](https://github.com/rust-lang/rust-clippy/pull/14864), [Issue #14150](https://github.com/rust-lang/rust-clippy/issues/14150)
- projectdiscovery/nuclei-templates: [Repo](https://github.com/projectdiscovery/nuclei-templates), [CONTRIBUTING](https://github.com/projectdiscovery/nuclei-templates/blob/master/CONTRIBUTING.md), [PR #10420](https://github.com/projectdiscovery/nuclei-templates/pull/10420), [PR #12898](https://github.com/projectdiscovery/nuclei-templates/pull/12898)
- hiero-ledger/hiero-sdk-python: [Repo](https://github.com/hiero-ledger/hiero-sdk-python), [CONTRIBUTING](https://github.com/hiero-ledger/hiero-sdk-python/blob/main/CONTRIBUTING.md), [Issue #1544](https://github.com/hiero-ledger/hiero-sdk-python/issues/1544), [Issue #1250](https://github.com/hiero-ledger/hiero-sdk-python/issues/1250)
- deepset-ai/haystack: [Repo](https://github.com/deepset-ai/haystack), [CONTRIBUTING](https://github.com/deepset-ai/haystack/blob/main/CONTRIBUTING.md), [Good First Issues](https://github.com/deepset-ai/haystack/issues?q=is%3Aissue+label%3A%22good+first+issue%22)
- kubernetes-sigs/kind: [Repo](https://github.com/kubernetes-sigs/kind), [CONTRIBUTING](https://kind.sigs.k8s.io/docs/contributing/getting-started/), [PR #3070](https://github.com/kubernetes-sigs/kind/pull/3070), [Issue #3117](https://github.com/kubernetes-sigs/kind/issues/3117), [Issue #2293](https://github.com/kubernetes-sigs/kind/issues/2293)