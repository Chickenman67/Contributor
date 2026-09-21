# Research: GitHub Actions Workflow Not Appearing in Actions Tab / API

## Executive Summary

A valid `.github/workflows/nightly.yml` on the master branch not appearing in GitHub Actions (both UI and `gh api` showing 0 workflows) can be caused by multiple factors. This document identifies all known causes with primary source citations.

---

## Root Cause Analysis

### 1. Workflow Not on Default Branch (Most Common)

**Cause**: GitHub only registers workflows for manual triggers (`workflow_dispatch`) and certain other events when the workflow file exists on the **default branch** (usually `main` or `master`).

**Evidence**:
- GitHub Docs: "This trigger only receives events when the workflow file is on the default branch." — [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#onworkflow_dispatch)
- GitHub Docs: "This event will only trigger a workflow run if the workflow file exists on the default branch." — [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)
- Stack Overflow: "Your workflow will not show up in the Actions tab until it's merged to the main branch... certain triggers (like push, workflow_dispatch) requires the new workflow to be merged to main branch first before showing up in Actions tab." — [Workflow not showing up in GitHub Actions](https://stackoverflow.com/questions/77161818/workflow-not-showing-up-in-github-actions)
- GitHub Community: "The workflow file must be committed in the default branch (master/main) if you want to use the workflow_dispatch event." — [Missing workflow_dispatch at the Action tab](https://github.com/orgs/community/discussions/25219)

**Fix**: Ensure the workflow file is pushed to the default branch (`main` or `master`), not just a feature branch.

---

### 2. Missing or Invalid `on:` Section

**Cause**: A workflow **must** have an `on:` section defining triggers. Without valid triggers, GitHub will not register the workflow.

**Evidence**:
- GitHub Docs: "To automatically trigger a workflow, use `on` to define which events can cause the workflow to run." — [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#on)
- Stack Overflow: "You need to put workflow_dispatch: under on:" — [Workflow is not shown so I cannot run it manually](https://stackoverflow.com/questions/67523882/workflow-is-not-shown-so-i-cannot-run-it-manually-github-actions)
- Stack Overflow: "Multiple syntax errors in your workflow: on section is not properly aligned i.e. push and workflow_dispatch should be at schedule level." — [GitHub not showing GitHub Actions workflow](https://stackoverflow.com/questions/76258332/github-not-showing-github-actions-workflow)

**Fix**: Ensure the workflow has a properly structured `on:` section at the top level of the YAML:
```yaml
on:
  workflow_dispatch:  # Required for manual "Run workflow" button
  # or other triggers like push, schedule, etc.
```

---

### 3. YAML Syntax / Validation Errors

**Cause**: Invalid YAML syntax (indentation errors, wrong keys, invalid glob patterns) causes GitHub to silently ignore the workflow file.

**Common Errors**:
- Using `branch:` instead of `branches:` for push triggers
- Incorrect indentation in `on:` section
- Invalid glob patterns (e.g., `v\d+` regex not allowed, `./path` not allowed)
- `workflow_dispatch` does not support `branches:` filter

**Evidence**:
- actionlint docs: "unexpected key 'branch' for 'push' section. expected one of 'branches', 'branches-ignore', 'paths', 'paths-ignore', 'tags', 'tags-ignore', 'types', 'workflows'" — [actionlint checks](https://github.com/rhysd/actionlint/blob/main/docs/checks.md)
- actionlint: "workflow_dispatch doesn't support branches" — [actionlint validation](https://github.com/rhysd/actionlint)
- Stack Overflow: "workflow_dispatch doesn't support branches. Fixing these should make your workflow valid and it should start appearing." — [GitHub not showing GitHub Actions workflow](https://stackoverflow.com/questions/76258332/github-not-showing-github-actions-workflow)

**Fix**: Validate with `actionlint`:
```bash
# Install and run
actionlint .github/workflows/nightly.yml
# Or use online playground: https://rhysd.github.io/actionlint/
```

---

### 4. Workflow in Disabled State

**Cause**: Workflows can be in states other than `active`: `disabled_manually`, `disabled_inactivity`, `disabled_fork`, `deleted`. The `gh workflow list` CLI **hides disabled workflows by default**.

**Evidence**:
- GitHub API docs: Workflow state enum: `active, deleted, disabled_fork, disabled_inactivity, disabled_manually` — [REST API endpoints for workflows](https://docs.github.com/en/rest/actions/workflows?apiVersion=2026-03-10)
- GitHub Docs: "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." — [Disabling and enabling a workflow](https://docs.github.com/en/actions/using-workflows/disabling-and-enabling-a-workflow)
- GitHub Docs: "When a public repository is forked, scheduled workflows are disabled by default." — [Disabling and enabling a workflow](https://docs.github.com/en/actions/using-workflows/disabling-and-enabling-a-workflow)
- gh CLI docs: "List workflow files, **hiding disabled workflows by default**." — [gh workflow list](https://cli.github.com/manual/gh_workflow_list)

**Fix**: Check for disabled workflows:
```bash
# List ALL workflows including disabled
gh workflow list --all
gh api repos/OWNER/REPO/actions/workflows --jq '.workflows[] | select(.state != "active")'
```

---

### 5. GitHub Actions Disabled at Repository/Organization Level

**Cause**: GitHub Actions can be disabled entirely for a repository or organization.

**Evidence**:
- GitHub Docs: "By default, GitHub Actions is enabled on all repositories and organizations. You can choose to disable GitHub Actions..." — [Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
- GitHub Docs: "If you see GitHub Actions is currently disabled for this repository... the repository or account may be in a separate GitHub-controlled disabled state." — [Managing GitHub Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)

**Fix**: Check Settings → Actions → General → "Actions permissions" is set to "Allow all actions" or "Allow select actions".

---

### 6. GitHub Workflow Indexer Stuck / Platform Bug

**Cause**: GitHub's internal workflow indexer can fail to parse triggers, especially with complex workflows (large inline scripts). This results in:
- API returning file path as workflow name instead of YAML `name:` value
- `workflow_dispatch` returning HTTP 422: "Workflow does not have 'workflow_dispatch' trigger"
- Event triggers silently not firing
- "Run workflow" button absent

**Evidence**:
- GitHub Community: "The GitHub Actions workflow indexer appears stuck... workflow_dispatch returns HTTP 422... The workflow name in the REST API returns the file path instead of the YAML name: value — indicating the file content was never fully parsed by the indexer." — [Workflow indexer not parsing triggers](https://github.com/orgs/community/discussions/189379)
- GitHub Community: "Workflow doesn't show up in UI workflow list or API... The actual workflow file is present in the .github/workflows directory, right next to other workflow files, of which some are present in the UI (and API) and some are not." — [Workflow doesn't show up in UI workflow list or API](https://github.com/orgs/community/discussions/144410)

**Fix**: 
1. Extract large inline scripts to external files (`.github/scripts/`) and reference via `require()`
2. Rename the workflow file to force new workflow ID
3. Make a no-op commit to default branch
4. Contact GitHub Support if persistent

---

### 7. API vs UI Discrepancy: gh CLI Default Behavior

**Cause**: `gh workflow list` hides disabled workflows by default. The API returns all workflows but the CLI filters them.

**Evidence**:
- gh CLI docs: "List workflow files, hiding disabled workflows by default." — [gh workflow list](https://cli.github.com/manual/gh_workflow_list)
- gh CLI: "`-a, --all Include disabled workflows`" — [gh workflow list](https://cli.github.com/manual/gh_workflow_list)

**Fix**: Always use `--all` flag when diagnosing:
```bash
gh workflow list --all
gh api repos/OWNER/REPO/actions/workflows
```

---

### 8. Private Repository Forks & Scheduled Workflows

**Cause**: In forks of public repositories, scheduled workflows are disabled by default.

**Evidence**:
- GitHub Docs: "When a public repository is forked, scheduled workflows are disabled by default." — [Disabling and enabling a workflow](https://docs.github.com/en/actions/using-workflows/disabling-and-enabling-a-workflow)
- GitHub Blog: "Scheduled workflows will be disabled by default in new forks of public repositories." — [GitHub Actions will disable scheduled workflows](https://news.ycombinator.com/item?id=24655458)

**Fix**: Enable workflows for forks in Settings → Actions → General → "Fork pull request workflows".

---

### 9. Branch Protection / Required Status Checks

**Cause**: Not a direct cause of workflow invisibility, but branch protection rules requiring status checks can prevent merges if workflow doesn't run.

**Evidence**: 
- GitHub Docs: "If a workflow is skipped due to branch filtering, path filtering, or a commit message, then checks associated with that workflow will remain in a 'Pending' state. A pull request that requires those checks to be successful will be blocked from merging." — [Workflow syntax - paths filter](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#onpushpull_requestpull_request_targetpathspaths-ignore)

---

## Diagnostic Checklist

Run these commands in order to diagnose:

```bash
# 1. Verify file exists on default branch
gh api repos/OWNER/REPO/contents/.github/workflows/nightly.yml?ref=main

# 2. Check workflow content (decode base64)
gh api repos/OWNER/REPO/contents/.github/workflows/nightly.yml?ref=main --jq '.content' | base64 -d

# 3. List ALL workflows via API (includes disabled)
gh api repos/OWNER/REPO/actions/workflows --jq '.workflows[] | {name, path, state, updated_at}'

# 4. List ALL workflows via CLI (includes disabled)
gh workflow list --all

# 5. Validate YAML syntax
actionlint .github/workflows/nightly.yml

# 6. Check repo Actions settings
gh api repos/OWNER/REPO/actions/permissions

# 7. Try manual dispatch (tests if workflow_dispatch is registered)
gh workflow run nightly.yml --ref main
```

---

## Quick Fix Steps

| # | Check | Command / Action |
|---|-------|------------------|
| 1 | File on default branch? | `git checkout main && git pull && ls .github/workflows/nightly.yml` |
| 2 | Valid `on:` section? | Check YAML has `on:` at top level with valid triggers |
| 3 | YAML syntax valid? | `actionlint .github/workflows/nightly.yml` |
| 4 | Workflow disabled? | `gh workflow list --all` → look for `disabled_*` states |
| 5 | Actions enabled in repo? | Settings → Actions → General → "Allow all actions" |
| 6 | Indexer stuck? | Rename file, push no-op commit, or extract inline scripts |
| 7 | Using `gh api` correctly? | `gh api repos/OWNER/REPO/actions/workflows` (not `gh workflow list`) |

---

## Key GitHub API Endpoints for Debugging

| Endpoint | Purpose |
|----------|---------|
| `GET /repos/{owner}/{repo}/actions/workflows` | List all workflows (includes disabled) |
| `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}` | Get specific workflow (can use filename) |
| `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` | Manually trigger workflow_dispatch |
| `PUT /repos/{owner}/{repo}/actions/workflows/{workflow_id}/enable` | Enable disabled workflow |
| `GET /repos/{owner}/{repo}/contents/.github/workflows/{file}?ref={branch}` | Verify file exists on branch |

---

## References

1. [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
2. [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
3. [Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
4. [Disabling and enabling a workflow](https://docs.github.com/en/actions/using-workflows/disabling-and-enabling-a-workflow)
5. [REST API endpoints for workflows](https://docs.github.com/en/rest/actions/workflows)
6. [gh workflow list](https://cli.github.com/manual/gh_workflow_list)
7. [actionlint - Static checker for GitHub Actions](https://github.com/rhysd/actionlint)
8. [Workflow indexer not parsing triggers (GitHub Community)](https://github.com/orgs/community/discussions/189379)
9. [Missing workflow_dispatch at the Action tab (GitHub Community)](https://github.com/orgs/community/discussions/25219)
10. [Workflow not showing up in GitHub Actions (Stack Overflow)](https://stackoverflow.com/questions/77161818/workflow-not-showing-up-in-github-actions)
11. [GitHub not showing GitHub Actions workflow (Stack Overflow)](https://stackoverflow.com/questions/76258332/github-not-showing-github-actions-workflow)
12. [Workflow is not shown so I cannot run it manually (Stack Overflow)](https://stackoverflow.com/questions/67523882/workflow-is-not-shown-so-i-cannot-run-it-manually-github-actions)