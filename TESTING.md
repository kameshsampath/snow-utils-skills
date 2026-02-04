# Snow-Utils Skills Testing Guide

This document tracks test scenarios for PAT and Networks skills.

## Prerequisites

- Cortex CLI installed and configured
- Snowflake connection available
- Clean environment (no existing test resources)

---

## PAT Skill Tests

### Phase 1: Fresh Creation

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| 2 | Auth policy expiry | "Create a PAT for service account" | Prompts for expiry (defaults 15/365), waits for confirmation | |
| 3 | Contextual COMMENTs | Create PAT for `MYAPP_RUNNER` | SQL shows `COMMENT = 'MYAPP ... - managed by snow-utils-pat'` | |
| 5 | Progressive manifest | Create PAT, check manifest mid-way | Manifest shows IN_PROGRESS with ✓/pending status | |
| 6 | .env chmod 600 | After PAT creation | `ls -la .env` shows `-rw-------` | |
| 7 | PAT verification | After create | Runs `snow sql -x` successfully | |

### Phase 2: Existing Resource Handling

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| 1 | Pre-check existing PAT | Run skill again after creation | Shows rotate/remove/recreate options | |
| 4 | --comment override | "Create PAT with comment CUSTOM_PROJECT" | Uses CUSTOM_PROJECT instead of inferred | |

### Phase 3: Manifest Flows

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| 8 | Remove flow | "Remove the PAT" | Reads manifest first, cleans up, removes section | |
| 9 | Replay flow | "Replay PAT creation from manifest" | Shows info summary, single confirmation | |
| 10 | Resume flow | Interrupt creation, then "Resume PAT creation" | Shows completed/pending, continues from pending | |

---

## Networks Skill Tests

### Phase 1: Fresh Creation

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| 12 | NLP multi-select (create) | "Create a network rule" | Multi-select for IP sources appears | |
| 15 | GitHub Actions IPv4 | Select GitHub Actions option | Only IPv4 ranges included (verify in SQL preview) | |
| 16 | Contextual COMMENTs | Create rule | SQL shows `COMMENT = '... - managed by snow-utils-networks'` | |
| 17 | Progressive manifest | Create rule, check manifest | Manifest updated after each resource | |

### Phase 2: Existing Resource Handling

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| 11 | Pre-check existing rule | Run skill again after creation | Shows update/remove/recreate options | |
| 13 | NLP multi-select (update) | Choose "Update existing" | Same multi-select appears | |
| 14 | Custom CIDRs follow-up | Select "Custom CIDRs" | Prompts for comma-separated values | |

### Phase 3: Manifest Flows

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| 18 | Remove flow | "Remove the network rule" | Reads manifest, drops policy before rule | |
| 19 | Replay flow | "Replay network rule from manifest" | Shows info with IP sources, single confirmation | |
| 20 | Resume flow | Interrupt creation, then "Resume" | Continues from pending resource | |

---

## Test Execution Log

### Date: ____

**Tester:** ____
**Environment:** ____

#### Phase 1 Results

| Test # | Result | Notes |
|--------|--------|-------|
| 2 | | |
| 3 | | |
| 5 | | |
| 6 | | |
| 7 | | |
| 12 | | |
| 15 | | |
| 16 | | |
| 17 | | |

#### Phase 2 Results

| Test # | Result | Notes |
|--------|--------|-------|
| 1 | | |
| 4 | | |
| 11 | | |
| 13 | | |
| 14 | | |

#### Phase 3 Results

| Test # | Result | Notes |
|--------|--------|-------|
| 8 | | |
| 9 | | |
| 10 | | |
| 18 | | |
| 19 | | |
| 20 | | |

---

## Cleanup Commands

### Full PAT Cleanup

```bash
set -a && source .env && set +a && uv run --project snow-utils-pat python snow-utils-pat/scripts/pat.py remove --user $SA_USER --db $SNOW_UTILS_DB
```

### Full Networks Cleanup

```bash
set -a && source .env && set +a && uv run --project snow-utils-networks python snow-utils-networks/scripts/network.py rule delete --name $NW_RULE_NAME --db $NW_RULE_DB
```

### Reset Test Environment

```bash
rm -rf .snow-utils/
rm -f .env
```
