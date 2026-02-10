# Snow-Utils Skills Testing Guide

This document tracks test scenarios for PAT, Networks, and Volumes skills.

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
| 5a | Step 5a: Network resources | Check manifest after network step | Manifest shows network rule ✓, network policy ✓, other pending | |
| 5b | Step 5b: PAT resources | Check manifest after PAT step | Manifest shows user/role/auth/PAT ✓ | |
| 5c | Step 5c: Secure .env | After PAT creation | `ls -la .env` shows `-rw-------` (chmod 600) | |
| 6 | PAT verification | After create | Runs `snow sql -x` successfully | |

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

## Volumes Skill Tests

### Phase 1: Fresh Creation

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| V1 | Admin role prompt | "Create an external volume" | Prompts for admin_role (default: ACCOUNTADMIN) | |
| V2 | Cross-skill awareness | Run after PAT sets admin_role | Asks "Use existing USERADMIN or ACCOUNTADMIN?" | |
| V3 | Manifest immediate write | After admin_role input | `.snow-utils/snow-utils-manifest.md` updated immediately | |
| V4 | Secured directory | After manifest write | `ls -la .snow-utils/` shows `drwx------` (chmod 700) | |
| V5 | Secured manifest file | After manifest write | `ls -la .snow-utils/snow-utils-manifest.md` shows `-rw-------` (chmod 600) | |
| V6 | Prefix explanation | Gather requirements step | Shows prefix examples (bucket, role, volume naming) | |
| V7 | Dry-run preview | After requirements gathered | Shows BOTH summary AND full SQL/JSON | |
| V8 | User confirmation | After dry-run | Waits for explicit "yes" before creating | |
| V9 | --output json (create) | `extvolume create --bucket test --output json` | Clean JSON output, no click.echo noise | |

### Phase 2: Existing Resource Handling

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| V10 | Pre-check existing volume | Run skill again after creation | Shows use/delete/recreate options | |
| V11 | --yes flag (delete) | `extvolume delete --bucket test --yes` | Skips confirmation prompt | |
| V12 | --output json (delete) | `extvolume delete --bucket test --yes --output json` | Returns `{"status": "success", "deleted": [...]}` | |

### Phase 3: Manifest Flows

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| V13 | Cleanup section | Check manifest after creation | Shows cleanup SQL with `USE ROLE <admin_role>` | |
| V14 | Remove flow | "Remove the external volume" | Reads manifest, uses admin_role for DROP | |
| V15 | Verify command | After create | `extvolume verify --volume-name X` succeeds | |

### Phase 4: Privilege Escalation Hints

| # | Feature | Test Command / Prompt | Expected Behavior | Status |
|---|---------|----------------------|-------------------|--------|
| V16 | App needs elevated access | "My app needs to create Iceberg tables" | Suggests GRANT CREATE ICEBERG TABLE to SA_ROLE | |
| V17 | No admin in app .env | Check skill guidance | Never suggests putting admin_role in app .env | |

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
set -a && source .env && set +a && uv run --project snow-utils-pat snow-utils-pat remove --user $SA_USER --db $SNOW_UTILS_DB
```

### Full Networks Cleanup

```bash
set -a && source .env && set +a && uv run --project snow-utils-networks snow-utils-networks rule delete --name $NW_RULE_NAME --db $NW_RULE_DB
```

### Full Volumes Cleanup

```bash
set -a && source .env && set +a && uv run --project snow-utils-volumes snow-utils-volumes delete --bucket $BUCKET --delete-bucket --force --yes
```

### Reset Test Environment

```bash
rm -rf .snow-utils/
rm -f .env
```
