---
name: snow-utils-pat
description: "Create Snowflake Programmatic Access Tokens (PATs) for service accounts. Use when: setting up service user, creating PAT, configuring authentication policy, network policy for PAT. Triggers: programmatic access token, PAT, service account, snowflake authentication, replay pat, replay pat manifest, recreate pat, replay all manifests, replay all snow-utils, export manifest for sharing, setup from shared manifest, replay from shared manifest."
---

# Snowflake PAT Setup

Creates service users, network policies, authentication policies, and Programmatic Access Tokens for automation.

## Workflow

**FORBIDDEN ACTIONS - NEVER DO THESE:**

- NEVER run SQL queries to discover/find/check values (no SHOW ROLES, SHOW DATABASES, SHOW USERS)
- NEVER auto-populate empty .env values by querying Snowflake
- NEVER use flags that bypass user interaction: `--yes`, `-y`, `--auto-setup`, `--auto-approve`, `--quiet`, `--force`, `--non-interactive`
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER skip SQL in dry-run output - always show BOTH summary AND full SQL
- **NEVER display PAT tokens in diffs, logs, or ANY output** - always mask as `***REDACTED***`
- **NEVER show .env file contents after PAT is written** - use redacted placeholder
- **NEVER run raw SQL for cleanup** - ALWAYS use `pat.py remove` command (handles dependency order automatically)
- **NEVER create resources without showing SQL and getting confirmation first**
- If .env values are empty, prompt user or run check_setup.py

**Writing Sensitive Values (SA_PAT):**

When about to write/edit a sensitive value like `SA_PAT`:

1. **DO NOT show diff** - diffs expose the sensitive value being written
2. **Show message before write:**

   ```
   📝 Writing sensitive value to .env (diff hidden to protect sensitive data)
   
   Confirm write? [y/N]
   ```

3. **After write, show REDACTED confirmation:**

   ```
   DONE: Updated .env: SA_PAT='***REDACTED***'
   ```

**INTERACTIVE PRINCIPLE:** This skill is designed to be interactive. At every decision point, ASK the user and WAIT for their response before proceeding.

**📍 MANIFEST FILE:** `.snow-utils/snow-utils-manifest.md` (ALWAYS this exact path and filename - never search for other patterns like *.yaml or *.*)

**⚠️ CONNECTION USAGE:** This skill uses the **user's Snowflake connection** (SNOWFLAKE_DEFAULT_CONNECTION_NAME) to create the SA infrastructure. It requires admin_role (from manifest, defaults to ACCOUNTADMIN) to create users, network policies, and authentication policies. The output (SA_PAT) is then used by apps/demos to consume resources.

**🔄 IDEMPOTENCY NOTE:** Network rules use `CREATE OR REPLACE` (Snowflake does not support `IF NOT EXISTS` for network rules). Network policies use `CREATE IF NOT EXISTS` to preserve existing policies. Re-running create operations is safe for automation.

**📌 ROLE MODEL:**

- **admin_role** (from manifest, default ACCOUNTADMIN): Creates and owns all objects
- **SA_ROLE** (`{PROJECT}_ACCESS`): Consumer-only role for PAT restriction. Apps/demos grant it access to their resources.
- **SA_USER** (`{PROJECT}_RUNNER`): Service user with PAT, restricted to SA_ROLE

**ENVIRONMENT REQUIREMENT:** Once SNOWFLAKE_DEFAULT_CONNECTION_NAME is set in .env, ALL commands must use it. Python scripts (pat.py, network.py, extvolume.py) auto-load `.env` via `load_dotenv()`. For `snow sql` or other shell commands, use `set -a && source .env && set +a` before running.

### Step 0: Check Prerequisites (Manifest-Cached)

**First, check manifest for cached prereqs:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -A2 "## prereqs"
```

**If `tools_verified:` exists with a date:** Skip tool checks, continue to Step 1.

**Otherwise, check required tools:**

```bash
for t in uv snow; do command -v $t &>/dev/null && echo "$t: OK" || echo "$t: MISSING"; done
```

**If any tool is MISSING, stop and provide installation instructions:**

| Tool | Install Command |
|------|-----------------|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `snow` | `pip install snowflake-cli` or `uv tool install snowflake-cli` |

**STOP**: Do not proceed until all prerequisites are installed.

**After tools verified, write to manifest:**

```bash
mkdir -p .snow-utils && chmod 700 .snow-utils
# Create manifest with header if it doesn't exist
if [ ! -f .snow-utils/snow-utils-manifest.md ]; then
cat > .snow-utils/snow-utils-manifest.md << 'EOF'
# Snow-Utils Manifest

This manifest tracks Snowflake resources created by snow-utils skills.

---

## project_recipe
project_name: <PROJECT_NAME>

## prereqs
tools_verified: <TODAY_DATE>
skills:
EOF
fi
# Add this skill's source URL if not already present
grep -q "pat:" .snow-utils/snow-utils-manifest.md || \
  echo "  pat: https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat" >> .snow-utils/snow-utils-manifest.md
chmod 600 .snow-utils/snow-utils-manifest.md
```

> **`<PROJECT_NAME>` derivation:** Use the current directory name: `basename $(pwd)`. Example: if in `/home/user/hirc-duckdb-demo`, project_name = `hirc-duckdb-demo`. This enables manifest portability — another developer can recreate the project directory from the manifest.

### Step 1: Load and Merge Environment

1. **Check if .env exists:**

   ```bash
   ls -la .env 2>/dev/null || echo "missing"
   ```

2. **If .env missing**, copy from .env.example:

   ```bash
   cp <SKILL_DIR>/.env.example .env
   ```

   **If .env exists**, merge missing keys from .env.example:
   - Read existing .env
   - Add only keys that don't exist (preserve all existing values)
   - Keys to check: SNOWFLAKE_DEFAULT_CONNECTION_NAME, SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT_URL, SA_ROLE, SNOW_UTILS_DB, SA_USER, LOCAL_IP, SA_PAT

3. **Check connection details in .env:**

   ```bash
   grep -E "^SNOWFLAKE_(DEFAULT_CONNECTION_NAME|ACCOUNT|USER|ACCOUNT_URL)=" .env
   ```

**If SNOWFLAKE_DEFAULT_CONNECTION_NAME is empty:**

- List connections:

     ```bash
     snow connection list
     ```

- Ask user to select a connection
- Test connection and extract details:

     ```bash
     snow connection test -c <selected_connection> --format json
     ```

- Update .env with:
  - `SNOWFLAKE_DEFAULT_CONNECTION_NAME=<selected>`
  - `SNOWFLAKE_ACCOUNT=<account from output>`
  - `SNOWFLAKE_USER=<user from output>`
  - `SNOWFLAKE_ACCOUNT_URL=https://<host from output>`

**If connection details already present:** Skip to Step 2.

### Step 2: Check Infrastructure (Conditional)

**First, check memory for cached infra status:**

If memory has `infra_ready: true` with `snow_utils_db` value:

- Use cached value
- Skip infra check, go to Step 3

**Otherwise, read from .env:**

```bash
grep -E "^SNOW_UTILS_DB=" .env
```

**If SNOW_UTILS_DB has value:** Skip to Step 3.

**If empty**, run check_setup.py with --suggest flag:

```bash
uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup --suggest
```

Parse the JSON response:

- `ready: true` → Database exists, skip to Step 3
- `ready: false` → Need to create database

**If not ready**, use `ask_user_question` to confirm:

- Show suggested database name from JSON (`suggested_database`)
- Ask user to confirm or provide custom value

**If user confirms setup**, run:

```bash
uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup --database <DB> --run-setup
```

**After setup completes, update .env:**

- `SNOW_UTILS_DB=<value user confirmed>`

**Note:** SA_ROLE ({PROJECT}_ACCESS) is created in Step 5 by this skill, not by check_setup.

**Update memory:**

```
Update /memories/snow-utils-prereqs.md:
tools_checked: true
infra_ready: true
snow_utils_db: <VALUE>
```

### Step 2a: Admin Role from Manifest

**Purpose:** PAT skill requires elevated privileges for account-level objects. Get admin_role from manifest.

> **📍 MANIFEST FILE:** `.snow-utils/snow-utils-manifest.md` - always use this exact path, never search for other patterns

**Required privileges for PAT skill:**

| Privilege | Scope | Required For | Default Role |
|-----------|-------|--------------|--------------|
| CREATE USER | Account | Creating service user | USERADMIN+ |
| CREATE ROLE | Account | Creating SA_ROLE | USERADMIN+ |
| MANAGE GRANTS | Account | Granting role to user | SECURITYADMIN+ |
| CREATE AUTHENTICATION POLICY | Schema | Creating auth policy | Schema owner |

> **Note:** Only ACCOUNTADMIN has ALL these privileges by default.

**Ensure secured .snow-utils directory:**

```bash
mkdir -p .snow-utils && chmod 700 .snow-utils
```

**Check manifest for existing admin_role:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -A1 "## admin_role" | grep "snow-utils-pat:"
```

**If admin_role exists for snow-utils-pat:** Use it, continue to Step 2b (privilege verification).

**If admin_role NOT set for snow-utils-pat, check other skills:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -E "^snow-utils-(volumes|networks):" | head -1
```

**If another skill has admin_role, ask user:**

```
Found admin_role from another skill:
  snow-utils-volumes: ACCOUNTADMIN
  
PAT creation requires CREATE USER + CREATE ROLE + MANAGE GRANTS + CREATE AUTHENTICATION POLICY.

Options:
1. Use existing: ACCOUNTADMIN
2. Use Snowflake default: ACCOUNTADMIN
3. Specify a different role
```

**If NO admin_role exists anywhere, prompt:**

```
PAT creation requires these privileges:
  - CREATE USER (Account)
  - CREATE ROLE (Account)
  - MANAGE GRANTS (Account)
  - CREATE AUTHENTICATION POLICY (Schema)

Snowflake recommends: ACCOUNTADMIN (has all privileges by default)

Enter admin role for PAT [ACCOUNTADMIN]: 
```

**⚠️ STOP**: Wait for user input.

**IMMEDIATELY write to manifest (before ANY resource creation):**

```bash
chmod 700 .snow-utils

cat >> .snow-utils/snow-utils-manifest.md << 'EOF'

## admin_role
snow-utils-pat: <USER_ROLE>
EOF

chmod 600 .snow-utils/snow-utils-manifest.md
```

**Update memory:**

```
Update /memories/snow-utils-prereqs.md:
pat_admin_role: <USER_ROLE>
```

Continue to Step 2b.

### Step 2b: Verify Admin Role Privileges

**If admin_role is ACCOUNTADMIN:** Skip verification, continue to Step 3.

**If admin_role is a custom role**, verify it has required privileges:

```bash
set -a && source .env && set +a && snow sql --role <ADMIN_ROLE> -q "
SHOW GRANTS TO ROLE <ADMIN_ROLE>;
" --format json
```

**Check for these grants in the output:**

| Look For | Privilege | On |
|----------|-----------|-----|
| CREATE USER | `CREATE USER` | ACCOUNT |
| CREATE ROLE | `CREATE ROLE` | ACCOUNT |
| MANAGE GRANTS | `MANAGE GRANTS` | ACCOUNT |
| CREATE AUTHENTICATION POLICY | `CREATE AUTHENTICATION POLICY` | SCHEMA (SNOW_UTILS_DB.POLICIES) |

**If any privilege is missing**, use `ask_user_question` with options:

| Option | Action |
|--------|--------|
| Grant missing privileges | Show GRANT statements for user to execute with elevated role |
| Use a different role | Go back to Step 2a to select different role |
| Cancel | Stop workflow |

**If user chooses "Grant missing privileges":**

Show SQL for each missing privilege:

```sql
-- Run as ACCOUNTADMIN or SECURITYADMIN
GRANT CREATE USER ON ACCOUNT TO ROLE <ADMIN_ROLE>;
GRANT CREATE ROLE ON ACCOUNT TO ROLE <ADMIN_ROLE>;
GRANT MANAGE GRANTS ON ACCOUNT TO ROLE <ADMIN_ROLE>;
GRANT CREATE AUTHENTICATION POLICY ON SCHEMA <SNOW_UTILS_DB>.POLICIES TO ROLE <ADMIN_ROLE>;
```

**STOP**: Wait for user to confirm privileges have been granted, then re-verify.

Continue to Step 3.

### Step 3: Gather Requirements (User-Prefixed Demo-Context Naming)

**Detect demo context from current directory:**

```bash
basename $(pwd)
```

Example: `hirc-duckdb-demo` → demo context = `HIRC_DUCKDB_DEMO`

**Read existing values from .env:**

```bash
grep -E "^(SNOWFLAKE_USER|SA_ROLE|SNOW_UTILS_DB)=" .env
```

**NAMING CONVENTION (User-Prefixed Demo-Context):**

> 💡 **TIP:** Using `{USER}_{DEMO}` prefix is recommended for shared accounts. This prevents naming collisions when multiple users create resources in the same account. The pattern `KAMESHS_MYAPP_RUNNER` clearly identifies the owner and purpose.

Both SA_ROLE and service user should use user-prefixed demo context for consistency:

| Variable | Pattern | Example (user=KAMESHS, demo=myapp) |
|----------|---------|--------------------------------|
| SA_ROLE | `{USER}_{DEMO}_ACCESS` | `KAMESHS_MYAPP_ACCESS` |
| SA_USER | `{USER}_{DEMO}_RUNNER` | `KAMESHS_MYAPP_RUNNER` |

**Prompt for naming preference first:**

Use `ask_user_question`:

```
💡 Service Account Naming

Using a user prefix is recommended for shared accounts to avoid collisions.

☑ Use prefix: KAMESHS_MYAPP_RUNNER (recommended)
☐ No prefix: MYAPP_RUNNER
```

**Then prompt for skill-specific values with appropriate defaults:**

```
PAT Configuration for demo: <DEMO_CONTEXT>

1. Service user name [default: <USER>_<DEMO>_RUNNER or <DEMO>_RUNNER based on choice]:
2. PAT role [default: <USER>_<DEMO>_ACCESS or <DEMO>_ACCESS based on choice]:
3. Admin role for setup [default: from manifest, or ACCOUNTADMIN]:
4. Database for policy objects [default: from SNOW_UTILS_DB]:
```

**Auth policy expiry settings (ALWAYS ask user to confirm):**

Use `ask_user_question` with preset options:

```
PAT Expiry Profile:

☐ Default (15/365 days) - Snowflake defaults
☐ Short (7/30 days) - Tight security, testing
☐ Medium (30/90 days) - Standard development
☐ Custom - I'll specify values
```

| Profile | Default Expiry | Max Expiry | Use Case |
|---------|---------------|------------|----------|
| Default | 15 days | 365 days | Snowflake defaults |
| Short | 7 days | 30 days | Tight security, testing |
| Medium | 30 days | 90 days | Standard development |
| Custom | (prompt) | (prompt) | User-specified |

**If user selects "Custom":**

```
5. PAT default expiry days [default: 15]:
6. PAT max expiry days [default: 365]:
```

**STOP**: Wait for user input on ALL values including expiry settings.

**After user provides input, update .env:**

- `SA_USER=<confirmed_value>`
- `SA_ROLE=<confirmed_value>`

### Step 3a: Check for Existing PAT

**Check if PAT already exists for the user (using elevated role):**

```bash
set -a && source .env && set +a && snow sql --role <ADMIN_ROLE> -q "SHOW USER PATS FOR USER <SA_USER>" --format json
```

> ⚠️ **IMPORTANT:** All account-level operations from this step onwards MUST use `--role <ADMIN_ROLE>` (from manifest) to ensure proper privileges.

**If PAT exists**, use `ask_user_question` to ask:

| Option | Action |
|--------|--------|
| Rotate existing | Use `pat.py rotate` - regenerates token, keeps all policies intact |
| Remove and recreate | Use `pat.py remove` then `pat.py create` - fresh start with new policies |
| Cancel | Stop workflow |

**If user chooses "Rotate existing":**

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  rotate --user <SA_USER> --role <SA_ROLE>
```

Then skip to Step 6 (Verify Connection).

**If user chooses "Remove and recreate":**

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  remove --user <SA_USER> --db <SNOW_UTILS_DB> --yes
```

Then continue to Step 4.

**If no PAT exists:** Continue to Step 4.

### Step 4: Preview (Dry Run)

**Execute:**

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <SA_USER> --role <SA_ROLE> --db <SNOW_UTILS_DB> --dry-run
```

**🔴 CRITICAL: ALWAYS SHOW SUMMARY + FULL SQL**

> This is MANDATORY on EVERY display - even after pause/resume, context restart, or re-confirmation.
> **FORBIDDEN:** Showing only summary. User MUST see BOTH parts EVERY time.

**Template (ALWAYS use this exact structure):**

**Part 1 - Resource Summary (brief):**

```
Resources to create:
  User:              HIRC_DUCKDB_DEMO_RUNNER
  Role:              HIRC_DUCKDB_DEMO_ACCESS
  Network Rule:      KAMESHS_SNOW_UTILS.NETWORKS.HIRC_DUCKDB_DEMO_RUNNER_NETWORK_RULE
  Network Policy:    HIRC_DUCKDB_DEMO_RUNNER_NETWORK_POLICY
  Auth Policy:       KAMESHS_SNOW_UTILS.POLICIES.HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY
  PAT Name:          HIRC_DUCKDB_DEMO_RUNNER_PAT
```

**Part 2 - Full SQL (MANDATORY - do not skip on first display):**

```sql
-- Step 1: Create service user
-- Uses admin_role from manifest (defaults to ACCOUNTADMIN)
USE ROLE <ADMIN_ROLE>;
CREATE USER IF NOT EXISTS HIRC_DUCKDB_DEMO_RUNNER
    TYPE = SERVICE
    COMMENT = 'HIRC_DUCKDB_DEMO service account - managed by snow-utils-pat';
GRANT ROLE HIRC_DUCKDB_DEMO_ACCESS TO USER HIRC_DUCKDB_DEMO_RUNNER;

-- Step 2: Create network rule and policy
USE ROLE <ADMIN_ROLE>;
CREATE NETWORK RULE KAMESHS_SNOW_UTILS.NETWORKS.HIRC_DUCKDB_DEMO_RUNNER_NETWORK_RULE
    MODE = INGRESS
    TYPE = IPV4
    VALUE_LIST = ('192.168.1.1/32')
    COMMENT = 'HIRC_DUCKDB_DEMO network rule - managed by snow-utils-pat';

-- Step 3: Create authentication policy
USE ROLE <ADMIN_ROLE>;
CREATE SCHEMA IF NOT EXISTS KAMESHS_SNOW_UTILS.POLICIES;
CREATE OR ALTER AUTHENTICATION POLICY KAMESHS_SNOW_UTILS.POLICIES.HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY
    AUTHENTICATION_METHODS = ('PROGRAMMATIC_ACCESS_TOKEN')
    PAT_POLICY = (
        DEFAULT_EXPIRY_IN_DAYS = 15
        MAX_EXPIRY_IN_DAYS = 365
        NETWORK_POLICY_EVALUATION = ENFORCED_REQUIRED
    )
    COMMENT = 'HIRC_DUCKDB_DEMO PAT auth policy - managed by snow-utils-pat';

ALTER USER HIRC_DUCKDB_DEMO_RUNNER SET AUTHENTICATION POLICY KAMESHS_SNOW_UTILS.POLICIES.HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY;

-- Step 4: Create PAT
ALTER USER IF EXISTS HIRC_DUCKDB_DEMO_RUNNER ADD PAT HIRC_DUCKDB_DEMO_RUNNER_PAT ROLE_RESTRICTION = HIRC_DUCKDB_DEMO_ACCESS;
```

**COMMENT Pattern:** `{DEMO_CONTEXT} {resource_type} - managed by snow-utils-pat`

**Demo Context Inference:**

- Derived from SA_USER by stripping suffixes: `_RUNNER`, `_SA`, `_SERVICE`, `_USER`
- Example: `HIRC_DUCKDB_DEMO_RUNNER` → `HIRC_DUCKDB_DEMO`
- Can be overridden via root CLI option: `pat.py --comment "MY_PROJECT" create ...`

> **⚠️ CRITICAL:** `--comment` is a GLOBAL option - it MUST come BEFORE the subcommand!
>
> ```bash
> # ✅ CORRECT - global option before subcommand
> pat.py --comment "MY_PROJECT" create --user ${SA_USER} ...
> 
> # ❌ WRONG - will fail with "No such option"
> pat.py create --user ${SA_USER} --comment "MY_PROJECT" ...
> ```

This enables:

- Easy identification of resources by demo/project context
- Filtering resources by skill: `SHOW USERS WHERE COMMENT LIKE '%snow-utils-pat%'`
- Cleanup discovery across multiple demos

**❌ WRONG:** Showing only summary table.
**✅ RIGHT:** Summary table + Full SQL block together.

> 🔄 **On pause/resume:** Re-display this SAME summary + SQL before asking for confirmation again.

**STOP**: Wait for explicit user approval ("yes", "ok", "proceed") before creating resources.

### Step 5a: Create Network Resources

> Step 4 already showed SQL and got user approval. Now executing.

**Execute:**

```bash
uv run --project <SKILL_DIR>/../snow-utils-networks python <SKILL_DIR>/../snow-utils-networks/scripts/network.py \
  rule create --name <SA_USER>_NETWORK_RULE --db <SNOW_UTILS_DB> --schema NETWORKS \
  --policy <SA_USER>_NETWORK_POLICY --output json
```

**CLI shows progress:**

- DONE: Network rule created
- DONE: Network policy created

> **Note:** Policy assignment to user happens after Step 5b creates the user.

Proceed to Step 5b.

**On failure:** Present error and remediation steps. Do NOT proceed to Step 5b.

### Step 5b: Create PAT Resources

> Step 4 already showed SQL and got user approval. Now executing.

**Execute:**

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <SA_USER> --role <SA_ROLE> --db <SNOW_UTILS_DB> --skip-network --output json
```

**CLI shows progress:**

- DONE: Role and user configured
- DONE: Auth policy created
- DONE: PAT created

> **Note:** `--skip-network` tells pat.py that network resources were created in Step 5a.

**Assign network policy to user** (now that user exists):

```bash
uv run --project <SKILL_DIR>/../snow-utils-networks python <SKILL_DIR>/../snow-utils-networks/scripts/network.py \
  policy assign --name <SA_USER>_NETWORK_POLICY --user <SA_USER>
```

Proceed to Step 5c.

**On failure:** Present error and remediation steps.

### Step 5c: Update .env and Write Manifest

> Step 4 already showed SQL and got user approval. Now updating .env with PAT.

**Update .env with the PAT token (single-quoted for safe parsing):**

```bash
# Use single quotes to handle special characters in PAT
sed -i '' "s/^SA_PAT=.*/SA_PAT='<PAT_TOKEN_VALUE>'/" .env
```

> Note: Diff hidden to protect sensitive value.

**Set restrictive permissions:**

```bash
chmod 600 .env
```

**Show REDACTED confirmation (NOT the actual value):**

```
DONE: .env updated:
  - SA_PAT='***REDACTED***'
  - Permissions: -rw------- (600)
```

**Write manifest** to `.snow-utils/snow-utils-manifest.md`:

```bash
mkdir -p .snow-utils
```

```markdown
# Snow-Utils Manifest

This manifest records all Snowflake resources created by snow-utils skills.

---

<!-- START -- snow-utils-pat -->
## PAT Resources: {COMMENT_PREFIX}

**Created:** {TIMESTAMP}
**User:** {SA_USER}
**Role:** {SA_ROLE}
**Database:** {SNOW_UTILS_DB}
**Comment:** {COMMENT_PREFIX}
**Default Expiry (days):** {DEFAULT_EXPIRY}
**Max Expiry (days):** {MAX_EXPIRY}
**Actual Expiry:** {ACTUAL_EXPIRY}
**Status:** COMPLETE

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Network Rule | {SA_USER}_NETWORK_RULE | {SNOW_UTILS_DB}.NETWORKS | DONE |
| 2 | Network Policy | {SA_USER}_NETWORK_POLICY | Account | DONE |
| 3 | Policy Assignment | → {SA_USER} | Account | DONE |
| 4 | Service Role | {SA_ROLE} | Account | DONE |
| 5 | Service User | {SA_USER} | Account | DONE |
| 6 | Auth Policy | {SA_USER}_AUTH_POLICY | {SNOW_UTILS_DB}.POLICIES | DONE |
| 7 | PAT | {SA_USER}_PAT | Attached to {SA_USER} | DONE |

### Cleanup Instructions

Run this command to remove all resources:

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  remove --user {SA_USER} --db {SNOW_UTILS_DB}
```
<!-- END -- snow-utils-pat -->
```

### Step 6: Verify Connection (MANDATORY)

**Always verify the PAT works after creation:**

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  verify --user <SA_USER> --role <SA_ROLE>
```

**Verification uses:**

- `snow sql -x` with `SNOWFLAKE_PASSWORD` set to the PAT token
- Runs `SELECT current_timestamp()` to confirm authentication works

**If verification fails:**

- Check network policy allows current IP
- Verify auth policy is attached to user
- Run with `--debug` flag for detailed output

### Step 7: Resource Manifest Format Reference

> **When to write:** Manifest is updated PROGRESSIVELY in Steps 5a, 5b, 5c - NOT here.
> This section defines the FORMAT to use.

**Manifest Location:** `.snow-utils/snow-utils-manifest.md`

**Create directory if needed:**

```bash
mkdir -p .snow-utils
```

**If manifest doesn't exist, create with header:**

```markdown
# Snow-Utils Manifest

This manifest records all Snowflake resources created by snow-utils skills.
Each skill section is bounded by START/END markers for easy identification.
CoCo uses this manifest to track, audit, and cleanup resources.

---
```

#### Progressive Manifest Writing

**Update manifest AFTER EACH resource is successfully created (not at the end).**

This enables recovery if CoCo loses context mid-creation.

**After Step 1 (Network Rule created):**

```markdown
<!-- START -- snow-utils-pat -->
## PAT Resources: {COMMENT_PREFIX}

**Created:** {TIMESTAMP}
**User:** {SA_USER}
**Role:** {SA_ROLE}
**Database:** {SNOW_UTILS_DB}
**Comment:** {COMMENT_PREFIX}
**Default Expiry (days):** {DEFAULT_EXPIRY}
**Max Expiry (days):** {MAX_EXPIRY}
**Actual Expiry:** {ACTUAL_EXPIRY}
**Status:** IN_PROGRESS

### Resources (creation order)

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Network Rule | {SA_USER}_NETWORK_RULE | {SNOW_UTILS_DB}.NETWORKS | DONE |
| 2 | Network Policy | {SA_USER}_NETWORK_POLICY | Account | PENDING |
| 3 | Auth Policy | {SA_USER}_AUTH_POLICY | {SNOW_UTILS_DB}.POLICIES | PENDING |
| 4 | Service User | {SA_USER} | Account | PENDING |
| 5 | PAT | {SA_USER}_PAT | Attached to {SA_USER} | PENDING |
<!-- END -- snow-utils-pat -->
```

**After each subsequent resource, update status from `PENDING` to `DONE`.**

**After all resources created, update Status to COMPLETE and add cleanup instructions section:**

```markdown
<!-- START -- snow-utils-pat -->
## PAT Resources: {COMMENT_PREFIX}

**Created:** {TIMESTAMP}
**User:** {SA_USER}
**Role:** {SA_ROLE}
**Database:** {SNOW_UTILS_DB}
**Comment:** {COMMENT_PREFIX}
**Default Expiry (days):** {DEFAULT_EXPIRY}
**Max Expiry (days):** {MAX_EXPIRY}
**Actual Expiry:** {ACTUAL_EXPIRY}
**Status:** COMPLETE

### Resources (creation order)

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Network Rule | {SA_USER}_NETWORK_RULE | {SNOW_UTILS_DB}.NETWORKS | DONE |
| 2 | Network Policy | {SA_USER}_NETWORK_POLICY | Account | DONE |
| 3 | Auth Policy | {SA_USER}_AUTH_POLICY | {SNOW_UTILS_DB}.POLICIES | DONE |
| 4 | Service User | {SA_USER} | Account | DONE |
| 5 | PAT | {SA_USER}_PAT | Attached to {SA_USER} | DONE |

### Cleanup Instructions

> **🚨 CRITICAL: ALWAYS USE CLI COMMAND FOR CLEANUP**
>
> The CLI command handles dependency order, syntax, and error recovery automatically.
> **NEVER run raw SQL for cleanup** - use the script command below.

#### CLI Cleanup (REQUIRED)

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py remove --user {SA_USER} --db {SNOW_UTILS_DB} --drop-user
```

#### SQL Reference (FALLBACK ONLY - if CLI unavailable)

<details>
<summary>Manual SQL cleanup (dependency order - reverse of creation)</summary>

```sql
USE ROLE {ADMIN_ROLE};
-- 1. Remove PAT first (depends on user)
ALTER USER {SA_USER} REMOVE PAT {SA_USER}_PAT;
-- 2. Unassign auth policy (MUST do before drop)
ALTER USER {SA_USER} UNSET AUTHENTICATION POLICY;
-- 3. Unassign network policy (MUST do before drop) - NOTE: underscore required!
ALTER USER {SA_USER} UNSET NETWORK_POLICY;
-- 4. Drop user (now safe - no policy dependencies)
DROP USER IF EXISTS {SA_USER};
-- 5. Drop auth policy
DROP AUTHENTICATION POLICY IF EXISTS {SNOW_UTILS_DB}.POLICIES.{SA_USER}_AUTH_POLICY;
-- 6. Drop network policy (frees the rule)
DROP NETWORK POLICY IF EXISTS {SA_USER}_NETWORK_POLICY;
-- 7. Drop network rule (last - policy depended on it)
DROP NETWORK RULE IF EXISTS {SNOW_UTILS_DB}.NETWORKS.{SA_USER}_NETWORK_RULE;
```

</details>
<!-- END -- snow-utils-pat -->
```

#### Export for Sharing Flow

**Trigger phrases:** "export manifest for sharing"

**Purpose:** Create a portable copy of the manifest for another developer. See BEST_PRACTICES "Export for Sharing Flow" for the full specification.

**Summary:**

1. Verify ALL skill sections have `Status: COMPLETE`
2. Read `project_name` from `## project_recipe`
3. Ask user for export location (default: project root)
4. Create `{project_name}-manifest.md` with:
   - `<!-- COCO_INSTRUCTION -->` at top
   - `## shared_info` with origin metadata
   - ALL statuses set to `REMOVED`
   - `# ADAPT: user-prefixed` markers on user-prefixed values
   - Cleanup instructions stripped

**Setup from shared manifest:** See hirc-duckdb-demo SKILL.md for the full "setup from shared manifest" flow (project directory creation, manifest placement, then replay with name adaptation).

#### Remove Flow (Manifest-Driven Cleanup)

> **🚨 CRITICAL: Cleanup MUST be driven by the manifest.**
>
> The manifest contains the exact CLI command to run. NEVER construct cleanup SQL manually.

**On `remove` / `cleanup` / `delete` request:**

1. **Check manifest exists:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md 2>/dev/null || echo "NOT_FOUND"
   ```

2. **If manifest NOT_FOUND:**
   - Inform user: "No manifest found. Cannot determine resources to clean up."
   - Ask: "Do you want to specify cleanup parameters manually?"
   - If yes, ask for SA_USER and SNOW_UTILS_DB values

3. **If manifest EXISTS:**
   - Read the `<!-- START -- snow-utils-pat -->` to `<!-- END -- snow-utils-pat -->` section
   - Find the **"CLI Cleanup (REQUIRED)"** section in manifest
   - **Execute the command exactly as written in the manifest**

   Example manifest excerpt:

   ```markdown
   #### CLI Cleanup (REQUIRED)
   
   ```bash
   uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py remove --user KAMESHS_PAT_DEMO_RUNNER --db KAMESHS_SNOW_UTILS --drop-user
   ```

   ```

4. **Before executing, show user:**

   ```
   🗑️  Cleanup from manifest:
   
   Will remove resources for: {SA_USER}
   Using command from manifest:
   
   <CLI command from manifest>
   
   Proceed? [yes/no]
   ```

5. **On confirmation:** Execute the CLI command from manifest

6. **After cleanup success:**
   - Update the manifest section: change `Status: COMPLETE` to `Status: REMOVED`
   - Add removal timestamp: `**Removed:** {TIMESTAMP}`
   - **DO NOT delete the manifest** - preserve for audit/reference
   - User can manually delete `.snow-utils/` folder if desired

   Example updated manifest section after cleanup:

   ```markdown
   ## PAT Resources: {COMMENT_PREFIX}

   **Created:** 2026-02-04 10:30:00
   **Removed:** 2026-02-04 14:45:00
   **User:** {SA_USER}
   **Role:** {SA_ROLE}
   **Default Expiry (days):** 90
   **Max Expiry (days):** 365
   **Actual Expiry:** 2026-04-05
   **Status:** REMOVED
   ```

> **Why preserve manifest?** The manifest serves as audit trail and reference for recreating resources.
> User can manually delete if no longer needed.

#### Replay Flow (Minimal Approvals)

> **🚨 GOAL:** Replay is for less technical users who trust the setup. Minimize friction.
> CoCo constructs summary from manifest (no dry-run needed), gets ONE confirmation, then executes.

**Trigger phrases:** "replay pat", "replay pat manifest", "recreate pat", "replay from manifest"

> **📍 Manifest Location:** `.snow-utils/snow-utils-manifest.md` (in current working directory)

**IMPORTANT:** This is the **snow-utils-pat** skill. Only replay sections marked `<!-- START -- snow-utils-pat -->`. If manifest contains other skills (Volumes, Networks), ignore them - use the appropriate skill for those.

**If user asks to replay/recreate from manifest:**

1. **Read manifest from current project directory:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md
   ```

2. **Find section** `<!-- START -- snow-utils-pat -->`
   - If section NOT found: "No PAT resources in manifest. Nothing to replay for PAT."
   - If section found: Continue to step 3

3. **Reconstruct .env (if missing or incomplete):**

   > **Portable Manifest:** When replaying from a shared manifest, `.env` may not exist. Reconstruct it using manifest values + one user input.

   ```bash
   # Check if .env exists and has connection details
   grep -q "^SNOWFLAKE_DEFAULT_CONNECTION_NAME=." .env 2>/dev/null || echo "NEEDS_SETUP"
   ```

   **If NEEDS_SETUP:**

   a. Copy `.env.example` from skill directory:

      ```bash
      cp <SKILL_DIR>/.env.example .env
      ```

   b. Ask user: "Which Snowflake connection?" then:

      ```bash
      snow connection list
      ```

      **⚠️ STOP**: Wait for user to select a connection.

   c. Test connection and extract details:

      ```bash
      snow connection test -c <selected_connection> --format json
      ```

      Write to .env: `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_ACCOUNT_URL`

   d. **Infer from manifest `snow-utils-pat` section:**

      ```bash
      SA_USER=$(grep -A30 "<!-- START -- snow-utils-pat" .snow-utils/snow-utils-manifest.md | grep "^\*\*User:\*\*" | head -1 | sed 's/\*\*User:\*\* //')
      SA_ROLE=$(grep -A30 "<!-- START -- snow-utils-pat" .snow-utils/snow-utils-manifest.md | grep "^\*\*Role:\*\*" | head -1 | sed 's/\*\*Role:\*\* //')
      SNOW_UTILS_DB=$(grep -A30 "<!-- START -- snow-utils-pat" .snow-utils/snow-utils-manifest.md | grep "^\*\*Database:\*\*" | head -1 | sed 's/\*\*Database:\*\* //')
      PAT_DEFAULT_EXPIRY=$(grep -A30 "<!-- START -- snow-utils-pat" .snow-utils/snow-utils-manifest.md | grep "^\*\*Default Expiry (days):\*\*" | head -1 | sed 's/\*\*Default Expiry (days):\*\* //')
      PAT_MAX_EXPIRY=$(grep -A30 "<!-- START -- snow-utils-pat" .snow-utils/snow-utils-manifest.md | grep "^\*\*Max Expiry (days):\*\*" | head -1 | sed 's/\*\*Max Expiry (days):\*\* //')
      ```

   e. **Validate extracted values** (grep validation):

      ```bash
      for var in SA_USER SA_ROLE SNOW_UTILS_DB PAT_DEFAULT_EXPIRY PAT_MAX_EXPIRY; do
        val=$(eval echo \$$var)
        [ -z "$val" ] && echo "WARNING: Could not extract ${var} from manifest"
      done
      ```

      If any value is empty, ask user to enter manually or abort.
      Note: `PAT_DEFAULT_EXPIRY` and `PAT_MAX_EXPIRY` are optional — if missing, use defaults (90/365).

   f. **Detect shared manifest and offer name adaptation:**

      If manifest contains `# ADAPT: user-prefixed` markers, extract `shared_by` from `## shared_info` and Bob's `SNOWFLAKE_USER`. If prefixes differ, show the **combined summary + adaptation screen** (see BEST_PRACTICES "Name Adaptation During Replay"). If not shared, skip adaptation.

   g. Write values (adapted or original) to `.env` (only if not already set):

      ```bash
      for var in SA_USER SA_ROLE SNOW_UTILS_DB; do
        val=$(eval echo \$$var)
        [ -n "$val" ] && (grep -q "^${var}=" .env && \
          sed -i '' "s/^${var}=.*/${var}=${val}/" .env || \
          echo "${var}=${val}" >> .env)
      done
      ```

   h. Leave `SA_PAT` empty — it will be created fresh during this replay.

   **If .env exists and has all values:** Skip to step 4.

4. **Check Status field and act accordingly:**

| Status | Action |
|--------|--------|
| `REMOVED` | Proceed with creation (resources don't exist) |
| `COMPLETE` | Warn: "Resources already exist. Run 'remove' first or choose 'recreate' to cleanup and recreate." |
| `IN_PROGRESS` | Use Resume Flow instead (partial creation) |

5. **If Status is NOT `REMOVED`**, stop and inform user of appropriate action.

6. **If Status is `REMOVED`**, extract values and display pre-populated summary:

```
ℹ️  Replay from manifest — values pre-populated (no questions to re-answer):

  Resources to create:
    • Network Rule:   {SA_USER}_NETWORK_RULE
    • Network Policy: {SA_USER}_NETWORK_POLICY
    • Auth Policy:    {SA_USER}_AUTH_POLICY
    • Service User:   {SA_USER}
    • PAT:            {SA_USER}_PAT

  Configuration (from manifest):
    User:     {SA_USER}           (from manifest **User:** field)
    Role:     {SA_ROLE}           (from manifest **Role:** field)
    Database: {SNOW_UTILS_DB}     (from manifest **Database:** field)
    Comment:  {COMMENT_PREFIX}    (from manifest **Comment:** field)

  Expiry settings (from manifest):
    Default Expiry: {DEFAULT_EXPIRY} days
    Max Expiry:     {MAX_EXPIRY} days
    Previous Expiry Date: {ACTUAL_EXPIRY}  (new expiry will be recalculated)

Proceed with creation? [yes/no]
```

7. **On "yes":** Run actual command (ONE bash approval, NO further prompts):

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  --comment "{COMMENT_PREFIX}" create --user {SA_USER} --role {SA_ROLE} --db {SNOW_UTILS_DB}
```

- CLI shows progress for each step automatically
- **NO additional user prompts until complete**

8. **Update manifest** status back to `COMPLETE` after successful creation

#### Resume Flow (Partial Creation Recovery)

**If manifest shows Status: IN_PROGRESS:**

1. **Read which resources have status `DONE`** (already created)
2. **Display resume info:**

```

ℹ️  Resuming from partial creation:

  DONE: Network Rule
  DONE: Network Policy

- Auth Policy:    PENDING
- Service User:   PENDING
- PAT:            PENDING

Continue from Auth Policy creation? [yes/no]

```

1. **On "yes":** Continue from first `PENDING` resource
2. **Update manifest** as each remaining resource is created

**Display success summary to user:**

```

PAT Setup Complete!

Resources Created:
  User:           {SA_USER}
  Role:           {SA_ROLE}
  Network Rule:   {SNOW_UTILS_DB}.NETWORKS.{SA_USER}_NETWORK_RULE
  Network Policy: {SA_USER}_NETWORK_POLICY
  Auth Policy:    {SNOW_UTILS_DB}.POLICIES.{SA_USER}_AUTH_POLICY
  PAT:            ***REDACTED*** (saved to .env as SNOWFLAKE_PASSWORD)

Manifest updated: .snow-utils/snow-utils-manifest.md

```

## Replay All Flow (Multi-Skill Sequential)

**Trigger phrases:** "replay all manifests", "replay all snow-utils", "recreate all from manifest"

> **Purpose:** Replay ALL skills from manifest in timestamp order. Safer than individual replay when dependencies exist.

**If user asks to replay all:**

1. **Read manifest from current project directory:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md
   ```

2. **Find ALL skill sections** matching `<!-- START -- snow-utils-* -->`

3. **Extract Created timestamp from each section** and sort ascending:

   ```
   Found 3 skill sections:
   
   | # | Skill | Created | Status |
   |---|-------|---------|--------|
   | 1 | snow-utils-networks | 2026-02-04T14:30:00 | REMOVED |
   | 2 | snow-utils-pat | 2026-02-04T14:35:00 | REMOVED |
   | 3 | snow-utils-volumes | 2026-02-04T15:00:00 | REMOVED |
   ```

4. **Check all statuses:**
   - If ANY section has `Status: COMPLETE`: Warn user which skills already exist
   - If ANY section has `Status: IN_PROGRESS`: Warn user to resume that skill first
   - Only proceed if ALL sections have `Status: REMOVED`

5. **Display replay plan with single confirmation:**

```
ℹ️  Replay All will recreate resources in original order:

  1. Networks (2026-02-04T14:30:00)
     → Network Rule, Network Policy
  
  2. PAT (2026-02-04T14:35:00)
     → Service User, Auth Policy, PAT
  
  3. Volumes (2026-02-04T15:00:00)
     → S3 Bucket, IAM Role, External Volume

Proceed with sequential creation? [yes/no]
```

1. **On "yes":** Execute each skill's replay in order:

   **For each skill in timestamp order:**
   - Extract values from that skill's manifest section
   - Execute the appropriate create command
   - Update that section's status to `COMPLETE`
   - If ANY skill fails: STOP immediately, report which skill failed
   - Do NOT continue to next skill on failure

2. **On completion:** Display summary:

```
✅ Replay All Complete!

  ✓ Networks:  COMPLETE
  ✓ PAT:       COMPLETE  
  ✓ Volumes:   COMPLETE

All resources recreated successfully.
```

**On failure:**

```
❌ Replay All Failed at: PAT

  ✓ Networks:  COMPLETE (rolled back: NO)
  ✗ PAT:       FAILED - <error message>
  - Volumes:   SKIPPED

Fix the PAT issue, then run "replay all" again to continue.
```

## PAT Security

**🚨 CRITICAL: NEVER display PAT tokens in ANY output:**

- Diff output (use `***REDACTED***` placeholder)
- Log messages
- Console output
- Summary displays
- Error messages
- Debug output

**Always mask as:** `***REDACTED***`

**When showing .env changes (MANDATORY redaction):**

```diff
# ❌ WRONG - NEVER show actual token
+ SA_PAT='ver:1-hint:12345-secret:abcdef...'

# ✅ CORRECT - Always redact
+ SA_PAT='***REDACTED***'
```

**When updating .env programmatically:**

```bash
# Use single quotes to handle special characters in PAT
sed -i '' "s/^SA_PAT=.*/SA_PAT='<TOKEN>'/" .env

# NEVER echo/cat the .env file after adding PAT
# NEVER use `git diff` that shows .env contents with PAT
```

**If you accidentally display a PAT:**

1. Immediately inform the user
2. Recommend rotating the PAT: `pat.py rotate --user <SA_USER> --role <SA_ROLE>`

## Tools

### check_setup.py (from common)

**Description:** Pre-flight check for snow-utils infrastructure. Prompts interactively.

**Usage:**

```bash
uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup
```

**DO NOT ADD ANY FLAGS.**

**Options:**

- `--quiet`, `-q`: Exit 0 if ready, 1 if not (scripting only)

### pat.py

**Description:** Creates and manages Snowflake PATs with network and auth policies.

**CRITICAL RULES FOR COCO:**

| Rule | Description |
|------|-------------|
| **Always confirm** | NEVER execute create, remove, or rotate without explicit user confirmation |
| **Show what will happen** | Display SQL preview or summary BEFORE asking for confirmation |
| **One operation at a time** | Don't chain multiple destructive operations |
| **Fail fast** | Check prerequisites before running; stop with clear error if not met |

**Pre-Check Rules (Fail Fast):**

| Command | Pre-Check | If Fails |
|---------|-----------|----------|
| `create` | User doesn't exist | Stop: "User {SA_USER} already exists. Use `rotate` to refresh token or `remove` first." |
| `rotate` | PAT exists for user | Stop: "No existing PAT found for {SA_USER}. Use `create` instead." |
| `remove` | User/resources exist | Proceed gracefully (idempotent with IF EXISTS) |

**Command Selection Rules:**

| Scenario | Command | When to Use |
|----------|---------|-------------|
| New PAT needed | `create` | User has no existing PAT, or chose "Remove and recreate" in Step 3a |
| PAT exists, refresh token | `rotate` | User chose "Rotate existing" in Step 3a - keeps all policies |
| Full cleanup | `remove` | User explicitly requests cleanup, or "Remove and recreate" before create |
| Test connection | `verify` | After create or rotate to confirm PAT works |

**Confirmation Flow:**

1. **create**: Show SQL preview (Step 4) → Ask "Proceed with creation?" → Execute only on "yes"
2. **remove**: Show resources to be deleted → Ask "Confirm deletion of these resources?" → Execute only on "yes"  
3. **rotate**: Show current PAT info → Ask "Rotate PAT for user X?" → Execute only on "yes"

**Post-Operation Rules:**

| Command | After Success |
|---------|---------------|
| `create` | Update manifest progressively → Update .env (SA_PAT) → Run `verify` → Mark manifest COMPLETE |
| `rotate` | Update .env (SA_PAT with new token) → Run `verify` |
| `remove` | Read manifest first for exact names → Clear SA_PAT from .env → Remove skill section from manifest |
| `replay` | Read manifest → Single info confirmation → Execute all steps → Update manifest progressively |
| `resume` | Read manifest (IN_PROGRESS) → Show completed/PENDING → Continue from first PENDING |

**Commands:**

| Command | Description |
|---------|-------------|
| `create` | Create service user, policies, and PAT |
| `remove` | Remove all PAT-related resources (dependency-aware order) |
| `rotate` | Regenerate PAT token, keeps all policies intact |
| `verify` | Test PAT connection using `snow sql -x` |

#### create

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <SA_USER> --role <SA_ROLE> --db <SNOW_UTILS_DB> --output json
```

**With custom expiry settings:**

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <SA_USER> --role <SA_ROLE> --db <SNOW_UTILS_DB> \
  --default-expiry-days 7 --max-expiry-days 30 --output json
```

**Options:**

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--user` | Yes | - | Service user name |
| `--role` | Yes | - | PAT role restriction |
| `--admin-role` | No | From manifest | Role for creating policies |
| `--db` | Yes | - | Database for policy objects |
| `--dry-run` | No | false | Preview SQL without executing |
| `--output json` | No | text | Machine-readable output |
| `--local-ip` | No | auto-detect | Override IP for network rule |
| `--default-expiry-days` | No | 15 | PAT default expiry (Snowflake default) |
| `--max-expiry-days` | No | 365 | PAT max expiry (Snowflake default) |

#### remove

Removes all PAT-related resources in correct dependency order:
PAT → Auth Policy (unset) → User → Auth Policy (drop) → Network Policy → Network Rule

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  remove --user <SA_USER> --db <SNOW_UTILS_DB>
```

**Options:**

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--user` | Yes | - | Service user to remove |
| `--db` | Yes | - | Database containing policies |
| `--admin-role` | No | From manifest | Role for dropping resources |
| `--dry-run` | No | false | Preview DROP statements |

#### rotate

Regenerates PAT token while keeping all existing policies intact.

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  rotate --user <SA_USER> --role <SA_ROLE>
```

**Options:**

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--user` | Yes | - | Service user with existing PAT |
| `--role` | Yes | - | Role restriction for new PAT |
| `--admin-role` | No | From manifest | Role for rotation |

**After rotation:** Updates SA_PAT in .env with new token.

#### verify

Tests PAT authentication using `snow sql -x` (external/passwordless auth).

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  verify --user <SA_USER> --role <SA_ROLE>
```

**Options:**

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--user` | Yes | - | Service user to verify |
| `--role` | Yes | - | Role to test with |
| `--debug` | No | false | Show detailed connection info |

**Verification runs:** `SELECT current_timestamp()` to confirm auth works.

## Stopping Points

- Step 1: If connection checks fail
- Step 2: If infra check needed (prompts user)
- Step 3: After gathering requirements
- Step 3a: If PAT exists (ask rotate/recreate/cancel)
- Step 4: After dry-run preview (get approval)

## Output

- Service user (TYPE = SERVICE)
- Network rule with local IP
- Network policy (ENFORCED_REQUIRED)
- Authentication policy (PROGRAMMATIC_ACCESS_TOKEN only)
- PAT token (saved to .env as SA_PAT, masked in output)
- Updated .env with all values
- Cleanup manifest (snow-utils-manifest.md)

## Troubleshooting

**Infrastructure not set up:** Run `python -m snow_utils_common.check_setup` from common - it will prompt and offer to create.

**Network policy blocking:** Ensure your IP is in the network rule. Use --local-ip to specify.

**PAT already exists:** Use --rotate to replace existing PAT.

**Connection verification failed:** Check network policy allows your IP.

**Cannot drop database (policy attached):** Run `pat.py remove --drop-user` - it handles dependency order automatically. **NEVER run raw SQL for cleanup.**

**Cannot drop network rule (associated with policies):** Run `pat.py remove` - it detaches rules from policies before dropping. **NEVER run raw SQL for cleanup.**

## Security Notes

- PAT tokens stored in .env with proper escaping
- PAT tokens NEVER displayed in diffs or logs (masked as ***REDACTED***)
- Network policy restricts access to specified IPs only
- Auth policy enforces PAT-only authentication
- Tokens have configurable expiry (default 30 days)
