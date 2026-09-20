# Automatic GitHub Contributor with Free AI — Feasibility Research

**Researched:** September 2026
**Focus:** Is it possible to build an automatic contributor that scans many open-source repos and improves them using AI, for free?

**Short answer: Yes, technically — but only at small scale and only if you behave like Dependabot/Renovate (opt-in, low-volume, high-signal). Mass unsolicited AI PRs across many repos you don't own break free-tier quotas, hit GitHub rate/secondary limits, and violate GitHub's spam/disruption policies, which can get the bot account suspended.**

---

## Quick Comparison Table

| Approach | Cost | Key free limit (primary source) | Scales to "many repos"? |
|----------|------|---------------------------------|-------------------------|
| **Local Ollama + PAT + git push** | Free (your electricity/hardware) | No API quota; limited by your machine + GitHub API limits (5,000 req/hr PAT, 10 search-code req/min) | Only bottleneck is GitHub API + spam policy |
| **Google Gemini free tier** | Free input+output tokens on free tier | Per-project RPM / TPM / RPD limits, RPD resets midnight Pacific; free tier has lower limits than paid tiers | ~tens of PRs/day max, not hundreds |
| **Groq free plan** | Free | Per-model RPM/RPD/TPM/TPD caps (e.g. listed models 30 RPM / 1K RPD / 8K TPM / 200K TPD; free tier is lower) | Good for small batches; daily cap is the wall |
| **Hugging Face Inference Providers free** | Free | $0.10/month free credits, then pay-as-you-go | Only a handful of large-model calls/month free |
| **OpenRouter `:free` models** | Free | 50 req/day (no credits) or 1,000 req/day (≥$10 credits purchased); 20 req/min | Hard ceiling ~50 PR-candidates/day |
| **GitHub-hosted Actions on public repos** | Free (standard runners, public repos) | Free; private repos capped (Free plan 2,000 min/mo, 500 MB artifacts, 10 GB cache/repo) | Yes for public repos, but job concurrency 20 (Free), 6h/job max, `GITHUB_TOKEN` 1,000 req/hr/repo |
| **GitHub Models (old option)** | N/A — retired | Retired July 30, 2026 (playground, catalog, inference API, BYOK all gone) | Do not design around it |
| **Dependabot / Renovate pattern (the allowed precedent)** | Free (built-in / self-hosted) | Dependabot caps at ~5 open PRs by default, groups updates, signs commits; Renovate uses branch+title cache keys, runs as App/Action/CLI | This is the only mass-PR pattern GitHub endorses |

---

## 1. Direct Answer: What Is Free-Feasible vs. What Breaks

### Free-feasible

- Running a bot against **repos you own or that opted in** (your own repos, or repos where your GitHub App is installed), generating a **few high-quality PRs per day**, using local models (Ollama) or one free cloud tier, orchestrated by scheduled GitHub Actions on public repos (free minutes) or a home server/cron. **Source:** [GitHub Actions billing — free for public repos + self-hosted runners](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions), [Actions billing and usage](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration).
- Authenticating as a **machine account** (one free machine account in addition to your personal account, human-created, human-responsible) or a **GitHub App installation token**. **Source:** [GitHub Terms of Service §B.3 Account Requirements](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service).
- Creating PRs via `POST /repos/{owner}/{repo}/pulls` with `title` + `head` + `base`, from a fork/branch you have write access to. **Source:** [REST API — Create a pull request](https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request).

### What breaks

1. **AI quota wall.** Every free inference tier caps daily requests/tokens/credits far below "scan many repos" volume:
   - OpenRouter free variants: 50 req/day without credits, 1,000 req/day after ≥$10 credits purchased, 20 req/min. **Source:** [OpenRouter FAQ — free models](https://openrouter.ai/docs/faq), [OpenRouter limits](https://openrouter.ai/docs/api_reference/limits), [OpenRouter rate-limit notice](https://openrouter.zendesk.com/hc/en-us/articles/39501163636379-OpenRouter-Rate-Limits-What-You-Need-to-Know).
   - Hugging Face: $0.10/month free credits for Inference Providers, then pay-as-you-go at provider rates with no markup. **Source:** [HF Inference Providers pricing](https://huggingface.co/docs/inference-providers/pricing), [HF pricing page](https://huggingface.co/pricing).
   - Gemini API: free tier exists (free input/output tokens) but is gated by per-project RPM/TPM/RPD limits (RPD resets midnight Pacific); exact numbers shown in AI Studio per model/tier. **Source:** [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini billing/tiers](https://ai.google.dev/gemini-api/docs/billing).
   - Groq: free-plan limits are the lowest tier; published base table shows per-model RPM/RPD/TPM/TPD (e.g. 30 RPM / 1K RPD / 8K TPM / 200K TPD on listed models) with exact limits on the account Limits page and `429` + `retry-after`/`x-ratelimit-*` headers on exceed. **Source:** [Groq rate limits](https://console.groq.com/docs/rate-limits).
   - GitHub Models is **not** an option: retired July 30, 2026. **Source:** [GitHub Models retirement](https://docs.github.com/en/github-models/about-github-models).
2. **GitHub API wall.** Authenticated REST: 5,000 req/hr (user/PAT), 5,000–12,500 req/hr (App installation, scales +50/repo over 20 repos and +50/user over 20 users), `GITHUB_TOKEN`: 1,000 req/hr/repo; unauthenticated: 60 req/hr. **Source:** [REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api). GraphQL: 5,000 points/hr/user (10,000 on GHEC), 1,000 points/hr/repo for `GITHUB_TOKEN`. **Source:** [GraphQL rate limits](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api). Code search is tighter: 10 req/min authenticated (30 req/min for other search endpoints), max ~1,000 results/search, query ≤256 chars, ≤5 AND/OR/NOT operators. **Source:** [Search API](https://docs.github.com/en/rest/search/search). Secondary limits add: ≤100 concurrent requests, ≤900 REST points/min, ≤80 content-generating req/min and ≤500/hr, with `403/429` + backoff; continued violation can get the integration banned. **Source:** [REST rate limits — secondary limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).
3. **Spam/disruption wall.** Mass unsolicited AI PRs are a policy violation, not just bad etiquette:
   - "Automated excessive bulk activity," "spamming," "inauthentic interactions," and "unsolicited advertising/solicitation through our servers" are prohibited. **Source:** [Acceptable Use Policies §4 Spam and Inauthentic Activity](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies).
   - "Opening empty or meaningless issues or pull requests," off-topic comments, nonsensical code reviews, and any platform-feature use "that creates disruption" or "causes excessive notifications" are prohibited; staff may restrict accounts beyond maintainer moderation. **Source:** [Disrupting the experience of other users](https://docs.github.com/en/site-policy/acceptable-use-policies/github-disrupting-the-experience-of-other-users), [Community Guidelines — enforcement](https://docs.github.com/en/site-policy/github-terms/github-community-guidelines).
   - API Terms: abuse/excessive use can mean temporary or permanent suspension; you may not share tokens to evade rate limits; you may not harvest data for spamming. **Source:** [Terms of Service §H API Terms](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service).
   - PR creation itself "triggers notifications" and "creating content too quickly may result in secondary rate limiting," with `422` when an endpoint is spammed. **Source:** [Create a pull request](https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request).
4. **Actions-misuse wall.** Actions "should not be used for ... any activity that places a burden on our servers, where that burden is disproportionate to the benefits," nor (on hosted runners) "any other activity unrelated to the production, testing, deployment, or publication of the software project associated with the repository." Misuse can mean job termination, feature restriction, repo disabling, or account suspension; GitHub may monitor usage. **Source:** [Additional Product Terms — Actions](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features). Crypto mining is explicitly banned there too.
5. **Acceptance wall.** Maintainers can lock conversations, block users, set interaction limits, and enforce `CONTRIBUTING.md` / issue/PR templates and codes of conduct. **Source:** [Community Guidelines — moderation tools](https://docs.github.com/en/site-policy/github-terms/github-community-guidelines), [Setting guidelines for repository contributors](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors). Unsolicited bulk AI PRs get closed, labeled spam, and reported — burning the bot's reputation and risking account action.

---

## 2. GitHub API: Rate Limits for a Scanning Bot

- **REST primary limits:** 60 req/hr unauthenticated (by IP); 5,000 req/hr authenticated user (PAT, or App/OAuth acting on your behalf); App installation token 5,000 req/hr minimum, scaling to 12,500 req/hr (+50/hr per repo over 20, +50/hr per user over 20); `GITHUB_TOKEN` 1,000 req/hr per repository (15,000 on GHEC). **Source:** [REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).
- **GraphQL primary limits:** points-based; 5,000/hr per user, 10,000/hr on GHEC; App installations 5,000–12,500/hr; `GITHUB_TOKEN` 1,000/hr per repo; query cost roughly = (connections ÷ 100) rounded, minimum 1; node cap 500,000 nodes/call with `first`/`last` 1–100. **Source:** [GraphQL rate limits](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api).
- **Secondary limits (both APIs):** ≤100 concurrent requests; ≤900 REST points/min (2,000 GraphQL points/min); ≤90s CPU/min; ≤80 content-creating req/min, ≤500/hr; ≤2,000 OAuth token req/hr. Exceeding yields `403`/`429` with `retry-after` / `x-ratelimit-reset`; keep retrying while limited and the integration can be banned. Check `x-ratelimit-limit/remaining/used/reset/resource` headers or `GET /rate_limit` (which itself can count toward secondary limits). **Source:** [REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).
- **Search/code-search limits:** authenticated 30 req/min generally, **10 req/min for `GET /search/code`**; unauthenticated 10 req/min; up to 1,000 results per search; only default branch, files <384 KB, must include a search term; queries >256 chars or >5 boolean operators fail validation. **Source:** [Search API](https://docs.github.com/en/rest/search/search).
- **Creating PRs:** `POST /repos/{owner}/{repo}/pulls` requires `head` + `base` (+ `title` unless converting an `issue`); for public repos you need write access to head/source branch; org repos require membership; response `422` on validation failure **or spam**. **Source:** [Create a pull request](https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request).

### Practical consequence

Scanning "many repos" via code search (10 req/min) plus contents/issues/pulls reads (5,000/hr) is feasible for dozens of repos per hour from one account — but opening PRs at volume immediately hits the 80/min–500/hr content-creation secondary limit, notification-triggered throttling, and the spam `422`/suspension path. One account cannot blast hundreds of PRs/hour for free.

---

## 3. GitHub Actions: What's Actually Free

- **Free:** standard GitHub-hosted runners in **public repositories**, GitHub Pages, and Dependabot runs; plus **self-hosted runners** always free (you pay the hardware/electricity). **Source:** [GitHub Actions billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions), [Billing and usage](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration).
- **Private-repo quotas (per month, reset monthly):** Free plan 2,000 min + 500 MB shared artifacts/Packages storage; Pro 3,000 min + 1 GB; Team 3,000 min + 2 GB; Enterprise Cloud 50,000 min + 50 GB; cache 10 GB/repo on all plans; larger runners always billed even for public repos. **Source:** [GitHub Actions billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions), [Actions limits — storage table](https://docs.github.com/en/actions/reference/limits).
- **Execution/concurrency caps:** job 6 hrs max (hosted) / 5 days (self-hosted); workflow run 35 days; matrix 256 jobs; Free plan 20 concurrent jobs (Pro 40, Team 60, Enterprise 500); macOS max 5 on Free/Pro/Team; 500 workflow runs queued per 10s; 1,500 trigger events per 10s per repo. **Source:** [Actions limits](https://docs.github.com/en/actions/reference/limits).
- **Triggers:** workflows run on push/PR/issues/schedule (`cron`), `workflow_dispatch`, etc.; scheduled workflows are the natural "nightly scan" driver. **Source:** [Events that trigger workflows](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows).
- **Misuse clause (quoted above):** no disproportionate-burden workloads, no unrelated-to-the-repo work on hosted runners; violations risk job kill → feature restriction → repo disable → account suspension. **Source:** [Additional Product Terms — Actions](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features).

### Practical consequence

A nightly scheduled workflow in **your own public orchestrator repo** (or per-repo opt-in workflows) that scans a small allow-list, calls a free model, and opens a handful of PRs is within free use. Turning Actions into a free compute farm that spams other people's repos is not.

---

## 4. GitHub Policy: Automation, Spam, and Bots

- **Bots allowed, with a human owner:** "Accounts registered by 'bots' or other automated methods are not permitted. We do permit machine accounts" — set up by a human who accepts the Terms, provides an email, and is responsible; max one free machine account plus your personal account. **Source:** [Terms of Service §B.3](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service).
- **Spam/inauthentic activity banned:** see §4 quote list in §1. **Source:** [Acceptable Use Policies §4](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies).
- **Low-quality bulk PRs explicitly banned:** "Opening empty or meaningless issues or pull requests" and notification-spamming feature use. **Source:** [Disrupting the experience of other users](https://docs.github.com/en/site-policy/acceptable-use-policies/github-disrupting-the-experience-of-other-users).
- **API abuse = suspension; no token-sharing to dodge limits; no spam-harvesting.** **Source:** [Terms of Service §H](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service).
- **Enforcement:** content removal, visibility downgrade, account/organization hide or suspension; appeal via the reinstatement form. **Source:** [Acceptable Use Policies — enforcement/appeal](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies), [Community Guidelines](https://docs.github.com/en/site-policy/github-terms/github-community-guidelines).
- **Bot transparency helps:** Dependabot PRs are identifiable (author `dependabot`, `dependencies` label, signed commits, rebase/comment commands). **Source:** [Managing Dependabot PRs](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/manage-dependabot-prs), [Dependabot pull requests](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-pull-requests). Copy that pattern: clear bot name, `ai-assisted` label, disclosure that the PR is AI-generated, how to reproduce/verify, easy close commands, and respect `CONTRIBUTING.md`/templates. **Source:** [Setting guidelines for repository contributors](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors).

---

## 5. Auth at Scale: GitHub App vs. PAT vs. GITHUB_TOKEN

- **GitHub App (recommended for a bot):** zero permissions by default — request minimums (e.g. `contents:read/write`, `pull-requests:read/write`, `issues:read/write`, `workflows` only if touching `.github/workflows`, `metadata:read`); permissions gate both REST endpoints and webhook subscriptions; installation tokens scale with repos/users (5,000→12,500/hr); user tokens inherit the lesser of app vs. user rights. **Source:** [Choosing permissions for a GitHub App](https://docs.github.com/en/apps/creating-github-apps/setting-up-a-github-app/choosing-permissions-for-a-github-app), [REST rate limits — App installations](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api). For Git-over-HTTPS with an installation/user token, request `contents` (plus `workflows` for Actions files). **Source:** [Choosing permissions — Git access](https://docs.github.com/en/apps/creating-github-apps/setting-up-a-github-app/choosing-permissions-for-a-github-app).
- **PAT (classic) vs. fine-grained:** classic `repo` scope can write to public repos you don't own (fork + PR flow); fine-grained tokens are safer (single owner, per-repo, per-permission) but **cannot** currently do every classic task — notably contributing to public repos where you aren't a member, or acting across multiple orgs at once — and are capped at 50 fine-grained tokens. **Source:** [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
- **`GITHUB_TOKEN`:** convenient inside Actions (1,000 req/hr/repo) but scoped to the workflow's repo and subject to fork-PR restrictions (read-only on forks, first-time-contributor approval). **Source:** [REST rate limits — GITHUB_TOKEN](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api), [Pull request workflow events — forks](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows).
- **Scale implication:** a single PAT scales to ~5,000 API calls/hr — fine for tens of repos, not thousands. A GitHub App installed per-repo/org is the legitimate scale path, but each installation requires owner consent — which is exactly why mass unsolicited PRs can't "scale" without becoming spam.

---

## 6. Free AI Inference: Actual Quotas (Primary Sources Only)

### 6.1 Ollama (local) — the only truly unlimited free option

- Run open models on your own machine; no per-request quota or fee — cost is hardware + electricity + your time. **Source:** [Ollama documentation](https://ollama.com/docs) (local models; model library for coding/reasoning/vision/embeddings).
- **Limits:** VRAM/RAM and tokens/sec on consumer GPUs; small coding models (e.g. 7–8B Q4) run on CPU/iGPU slowly, usable ones want 16 GB+ RAM and ideally a discrete GPU; quality below frontier cloud models, so human/CI verification matters more.
- **Best for:** the "for free" constraint — pair with scheduled Actions (free for public repos) or a home server so inference never bills.

### 6.2 Google Gemini free tier

- **Free tier exists** with free input/output tokens and AI Studio access, but limited to certain models with lower rate limits than paid tiers; new accounts start on Free; linking billing moves the project to paid tiers with caps ($250/$2,000/$20k–$100k by tier). **Source:** [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini billing](https://ai.google.dev/gemini-api/docs/billing).
- **Limits are per-project RPM / input-TPM / RPD** (RPD resets midnight Pacific); exceeding any one errors; exact numbers vary by model and tier and are shown in AI Studio, not as one global number. **Source:** [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).
- **Best for:** prototyping a few PRs/day with a strong model before switching to local inference.

### 6.3 Groq free tier

- **Free plan** is the lowest service tier; published base table (Developer-plan reference) shows per-model RPM/RPD/TPM/TPD such as 30 RPM / 1K RPD / 8K TPM / 200K TPD on listed chat models; your exact numbers are on the account Limits page; overages return `429` with `retry-after` and `x-ratelimit-*` headers; limits apply per-organization across users. **Source:** [Groq rate limits](https://console.groq.com/docs/rate-limits).
- **Best for:** fast draft generation in small batches; daily request cap is the binding constraint for a scanner.

### 6.4 Hugging Face Inference Providers

- **Free users get $0.10/month** in credits for Inference Providers (subject to change); PRO $2.00/month in general compute credits; Team/Enterprise $2.00/seat; beyond credits, pay-as-you-go at provider rates with no HF markup; single HF token routes to 200+ models across providers (Cerebras, Groq, Together, etc.). **Source:** [HF Inference Providers pricing](https://huggingface.co/docs/inference-providers/pricing), [HF Inference Providers index](https://huggingface.co/docs/inference-providers/index).
- **Best for:** experimenting across many open models with one token; not for sustained scanning (a few large-codebase calls exhaust $0.10).

### 6.5 OpenRouter free (`:free`) models

- **Free variants capped at 50 req/day** with no credits purchased, **1,000 req/day** after purchasing ≥$10 credits; ~20 req/min; failed attempts still count; paid variants have no OpenRouter platform cap (provider-side limits still apply). **Source:** [OpenRouter FAQ](https://openrouter.ai/docs/faq), [OpenRouter limits](https://openrouter.ai/docs/api_reference/limits), [OpenRouter rate-limit notice](https://openrouter.zendesk.com/hc/en-us/articles/39501163636379-OpenRouter-Rate-Limits-What-You-Need-to-Know).
- **Best for:** model-hopping on a tiny budget; the 50/day ceiling kills "many repos" unless you pay.

### 6.6 GitHub Models — retired, do not use

- As of **July 30, 2026**, playground, catalog, inference API, and BYOK are **fully retired**; GitHub points new work to Azure AI Foundry or Copilot. **Source:** [GitHub Models retirement](https://docs.github.com/en/github-models/about-github-models).

---

## 7. Precedent: How Dependabot and Renovate Avoid the Spam Label

### Dependabot (first-party)

- **Opt-in per repo** (enable security/version updates; optional `dependabot.yml` for schedule, directories, labels, reviewers, `open-pull-requests-limit`, grouping). Without the config file you get security updates only, not version churn. **Source:** [About the dependabot.yml file](https://docs.github.com/en/code-security/concepts/supply-chain-security/about-the-dependabot-yml-file), [Dependabot security updates](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-security-updates).
- **Volume-bounded:** starts with max **5** open version-update PRs, more only as you merge; grouping collapses many updates into one PR; security PRs target the default branch on advisory trigger. **Source:** [Dependabot pull requests](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-pull-requests).
- **Identifiable + safe:** author is `dependabot`, `dependencies` label by default, **signed commits**, auto-rebase (stops after 30 days or on extra commits unless tagged `[dependabot skip]`-style), comment commands (`@dependabot merge/squash/reopen/close/rebase`). **Source:** [Managing Dependabot PRs](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/manage-dependabot-prs).
- **Lesson:** capability-limited scope (deps only), explicit config, tiny default blast radius, verifiable diffs, maintainer controls.

### Renovate (third-party, open source)

- **Opt-in per repo/org** via the Mend GitHub App, self-hosted server, or the `renovatebot/github-action` pipeline job / raw CLI (`npx renovate`). **Source:** [renovatebot/renovate — ways to run](https://github.com/renovatebot/renovate), [Renovate docs](https://docs.renovatebot.com/).
- **Deterministic pipeline:** clone → scan package files (managers) → extract deps → datasource version lookup → versioning sort → group → branch + PR. **Source:** [How Renovate works](https://docs.renovatebot.com/key-concepts/how-renovate-works/).
- **Noise controls:** scheduling, automerge only with tests, dashboard approval for majors, and **branch-name + PR-title as cache keys** so a closed unique PR is never recreated (immortal/grouped PRs need `recreateWhen: never` care). **Source:** [Renovate PRs](https://docs.renovatebot.com/key-concepts/pull-requests/).
- **Lesson:** your AI bot needs the same: allow-list, schedule windows, per-repo PR caps, idempotency keys (branch+title), never-reopen-closed logic, and config-as-code in the target repo.

---

## 8. License, CLA/DCO, and Acceptance Risk

- **Inbound = outbound:** "Whenever you add Content to a repository containing notice of a license, you license that Content under the same terms, and you agree that you have the right to license that Content under those terms. If you have a separate agreement [e.g. a CLA] that agreement will supersede." A bot owner is responsible for having rights to what the bot submits. **Source:** [Terms of Service §D.6 Contributions Under Repository License](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service).
- **AI output IP risk is yours:** "Output may contain material that resembles code or content in the model's training data or that is subject to third-party copyrights or open source license terms. You are responsible for determining whether your use of Output requires a third-party license and for complying with any such license." Output is as-is; you must review/test/validate; indemnity applies. **Source:** [Terms of Service §J AI Features](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service).
- **What this means for the bot:** (a) only emit patches compatible with the target repo's license (e.g. don't paste GPL code into MIT/Apache repos without care, don't strip headers); (b) preserve/add `Signed-off-by` where the repo requires DCO, or complete the CLA flow where required — many repos auto-block PRs without it; (c) disclose AI generation in the PR body so maintainers can apply their own AI-content policy; (d) keep diffs minimal and test-backed, because unverified AI diffs that break builds are the fastest route to `wontfix`/ban.
- **CONTRIBUTING/templates are enforcement points:** repos advertise PR/issue templates, style, tests, and codes of conduct via `CONTRIBUTING.md`; bots that ignore them get closed. **Source:** [Setting guidelines for repository contributors](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors).
- **Maintainer acceptance risk for mass AI PRs is very high:** even technically correct bulk PRs create review burden and notification spam (itself a policy violation — see §4), so maintainers treat unknown bulk bots as hostile. Mitigate with: opt-in installs only, 1–2 PRs per repo max concurrent, schema-limited change classes (typo fixes, pinned-action SHAs, totp-safe dep bumps), full CI green + repro steps in the body, and human-readable titles.

---

## 9. Minimal Free Architecture (Recommended)

```
┌─ Orchestrator repo (PUBLIC, yours) ──────────────────┐
│ scheduled workflow (cron, ubuntu-latest)             │
│  1. checkout allow-list of target repos (git clone)  │
│  2. static analysis → candidate tasks (lint/test gap)│
│  3. Ollama (self-hosted runner) OR Gemini/Groq free  │
│     tier → small unified diff (≤200 lines)           │
│  4. run target's tests/linters locally               │
│  5. if green: fork → branch ai/<rule>-<date> → PR    │
│     via GitHub App installation token (contents:write│
│     + pull-requests:write), 1 PR/repo max, with      │
│     `ai-assisted` label + repro + test log           │
└──────────────────────────────────────────────────────┘
         │ respects: 5,000 req/hr PAT / 1k GITHUB_TOKEN,
         │ 10 code-search req/min, ≤80 content req/min,
         │ 50 OpenRouter free req/day or Gemini RPD, and
         │ Actions-free-on-public-repos billing
```

- **Compute:** self-hosted runner + Ollama = $0 marginal inference; scheduled standard-runner orchestration in the public repo = $0 Actions minutes. **Sources:** [Ollama docs](https://ollama.com/docs), [Actions billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions).
- **Auth:** register one GitHub App (`contents:write`, `pull-requests:write`, `issues:write` if commenting; add `workflows` only if editing Actions files), install **only where invited**; fall back to a classic PAT `repo` scope on your machine account for fork-and-PR flows. **Sources:** [Choosing App permissions](https://docs.github.com/en/apps/creating-github-apps/setting-up-a-github-app/choosing-permissions-for-a-github-app), [Managing PATs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
- **Rate discipline:** allow-list ≤20 repos; nightly cron; ≤5 PRs/day total; sleep ≥1s between mutating calls; honor `retry-after`/`x-ratelimit-reset` with exponential backoff; never recreate a closed PR (branch+title idempotency, Renovate-style). **Sources:** [REST rate limits — staying under](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api), [Renovate PRs — cache keys](https://docs.renovatebot.com/key-concepts/pull-requests/), [Dependabot PR caps](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-pull-requests).
- **Anti-spam discipline:** bot username/avatar/bio discloses automation; every PR states "AI-assisted, human-supervised by <owner>, closes on request"; obeys `CONTRIBUTING.md`/templates/license headers/DCO sign-off; stops entirely on maintainer objection or block. **Sources:** [Acceptable Use §4](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies), [Disruption policy](https://docs.github.com/en/site-policy/acceptable-use-policies/github-disrupting-the-experience-of-other-users), [Contributing guidelines](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors).

---

## 10. Recommendations by Use Case

- **"I want to improve my own / my team's repos for free"** → **Yes, fully feasible.** Self-hosted runner + Ollama + GitHub App on your org + scheduled workflows on public repos (or 2,000 free private minutes). No policy risk.
- **"I want to send a few careful PRs to favorite OSS projects"** → **Yes, feasible.** Hand-pick 3–5 repos, follow each `CONTRIBUTING.md`, use Gemini/Groq/OpenRouter free tier for drafts, verify with tests, open 1 PR at a time from a named bot account with disclosure. Expect human review latency.
- **"I want to scan hundreds of repos and auto-PR everywhere"** → **No — not free, not allowed.** You will exhaust the $0.10 HF credits / 50 OpenRouter req/day / Gemini RPD / Groq RPD within hours, trip the 80/min–500/hr content secondary limit and search 10/min cap, and violate the spam/disruption policies (account suspension risk). This is the exact pattern Dependabot/Renovate avoid via opt-in + caps.
- **"I want a Dependabot-for-X service"** → **Feasible if opt-in.** Publish a GitHub App with minimal permissions, per-repo config file, default ≤5 open PRs, grouping, signed commits, and dashboard approval — the Dependabot/Renovate playbook. Monetize later via paid inference; free tier stays small.

---

## 11. Recent Developments (2025–2026)

1. **GitHub Models retired (July 30, 2026):** playground, catalog, inference API, and BYOK all shut down; docs redirect to Azure AI Foundry / Copilot. Any "free GitHub inference" plan built on GitHub Models is dead. **Source:** [GitHub Models](https://docs.github.com/en/github-models/about-github-models).
2. **Gemini billing tiers hardened (2026):** Free vs. Tier 1 ($250 cap) / Tier 2 ($2,000) / Tier 3 ($20k–$100k) with spend-based 10-min windows; March 2026+ prepay/postpay migration in AI Studio; Gemini API excluded from the $300 Cloud trial. **Source:** [Gemini billing](https://ai.google.dev/gemini-api/docs/billing), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing).
3. **HF Inference Providers consolidated (2025+):** single router + OpenAI-compatible endpoint across 200+ models; free tier is credits-based ($0.10/mo free), not request-count-based. **Source:** [Inference Providers](https://huggingface.co/docs/inference-providers/index), [Pricing](https://huggingface.co/docs/inference-providers/pricing).
4. **Actions product terms unchanged in spirit:** disproportionate-burden and unrelated-to-the-repo hosted-runner work remain bannable; monitoring explicitly reserved. **Source:** [Additional Product Terms — Actions](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features).
5. **Spam enforcement posture:** "automated excessive bulk activity," meaningless PRs, and notification-spam remain separately actionable under both Acceptable Use and the disruption policy, independent of API rate limits. **Source:** [Acceptable Use §4](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies), [Disruption policy](https://docs.github.com/en/site-policy/acceptable-use-policies/github-disrupting-the-experience-of-other-users).

---

## Sources (primary only)

- GitHub REST rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- GitHub GraphQL rate/query limits: https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api
- GitHub Search API (incl. 10/min code search): https://docs.github.com/en/rest/search/search
- GitHub Create a pull request: https://docs.github.com/en/rest/pulls/pulls
- GitHub Actions billing: https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions
- GitHub Actions billing & usage: https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration
- GitHub Actions limits (jobs, concurrency, storage): https://docs.github.com/en/actions/reference/limits
- GitHub workflow trigger events: https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows
- GitHub Terms of Service (§B machine accounts, §D.6 inbound=outbound, §H API terms, §J AI output): https://docs.github.com/en/site-policy/github-terms/github-terms-of-service
- GitHub Acceptable Use Policies (§4 spam/inauthentic activity): https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies
- GitHub Disrupting the experience of other users: https://docs.github.com/en/site-policy/acceptable-use-policies/github-disrupting-the-experience-of-other-users
- GitHub Community Guidelines (moderation + enforcement): https://docs.github.com/en/site-policy/github-terms/github-community-guidelines
- GitHub Additional Product Terms (Actions misuse): https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features
- GitHub App permissions: https://docs.github.com/en/apps/creating-github-apps/setting-up-a-github-app/choosing-permissions-for-a-github-app
- GitHub PATs (classic vs. fine-grained, 50-token cap, classic-only public-contribution gap): https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
- GitHub contributing guidelines (CONTRIBUTING.md): https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors
- GitHub Models retirement: https://docs.github.com/en/github-models/about-github-models
- Dependabot pull requests (5-PR cap, grouping): https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-pull-requests
- Managing Dependabot PRs (signed commits, rebase, commands): https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/manage-dependabot-prs
- dependabot.yml config: https://docs.github.com/en/code-security/concepts/supply-chain-security/about-the-dependabot-yml-file
- Renovate — how it works: https://docs.renovatebot.com/key-concepts/how-renovate-works/
- Renovate — PRs (branch+title cache keys): https://docs.renovatebot.com/key-concepts/pull-requests/
- renovatebot/renovate repo (ways to run): https://github.com/renovatebot/renovate
- Gemini rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini billing/tiers: https://ai.google.dev/gemini-api/docs/billing
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Hugging Face Inference Providers: https://huggingface.co/docs/inference-providers/index
- HF Inference Providers pricing ($0.10 free): https://huggingface.co/docs/inference-providers/pricing
- HF pricing page: https://huggingface.co/pricing
- Ollama docs: https://ollama.com/docs
- OpenRouter limits: https://openrouter.ai/docs/api_reference/limits
- OpenRouter FAQ (50/1,000 free req/day): https://openrouter.ai/docs/faq
- OpenRouter rate-limit notice (50/day, 20/min): https://openrouter.zendesk.com/hc/en-us/articles/39501163636379-OpenRouter-Rate-Limits-What-You-Need-to-Know
