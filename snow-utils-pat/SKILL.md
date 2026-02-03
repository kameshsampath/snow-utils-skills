---
name: snow-utils-pat
description: "Create Snowflake Programmatic Access Tokens (PATs) for service accounts. Use when: setting up service user, creating PAT, configuring authentication policy, network policy for PAT. Triggers: programmatic access token, PAT, service account, snowflake authentication."
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
- NEVER display PAT tokens in diffs, logs, or output - always mask as `***REDACTED***`
- If .env values are empty, prompt user or run check_setup.py

**INTERACTIVE PRINCIPLE:** This skill is designed to be interactive. At every decision point, ASK the user and WAIT for their response before proceeding.

**⚠️ CONNECTION USAGE:** This skill uses the **user's Snowflake connection** (SNOWFLAKE_DEFAULT_CONNECTION_NAME) to create the SA infrastructure. It requires SA_ADMIN_ROLE (defaults to ACCOUNTADMIN) to create users, network policies, and authentication policies. The output (SA_PAT) is then used by apps/demos to consume resources.

**📌 ROLE MODEL:**

- **SA_ADMIN_ROLE** (ACCOUNTADMIN): Creates and owns all objects
- **SA_ROLE** (`{PROJECT}_ACCESS`): Consumer-only role for PAT restriction. Apps/demos grant it access to their resources.
- **SA_USER** (`{PROJECT}_RUNNER`): Service user with PAT, restricted to SA_ROLE

**ENVIRONMENT REQUIREMENT:** Once SNOWFLAKE_DEFAULT_CONNECTION_NAME is set in .env, ALL commands must use it. Always `source .env` before running any script commands.

### Step 0: Check Prerequisites (with Memory Caching)

**First, check memory for cached prereqs:**

```
Check memory at /memories/snow-utils-prereqs.md for:
- tools_checked: true → skip tool check
- infra_ready: true → skip infra check in Step 2
- sa_role, snow_utils_db → use cached values
```

**If `tools_checked: true` in memory:** Skip to Step 1.

**Otherwise, check required tools:**

```bash
command -v uv >/dev/null 2>&1 && echo "uv: OK" || echo "uv: MISSING"
command -v snow >/dev/null 2>&1 && echo "snow: OK" || echo "snow: MISSING"
```

**If any tool is MISSING, stop and provide installation instructions:**

| Tool | Install Command |
|------|-----------------|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `snow` | `pip install snowflake-cli` or `uv tool install snowflake-cli` |

**STOP**: Do not proceed until all prerequisites are installed.

**After tools verified, update memory:**

```
Create/update /memories/snow-utils-prereqs.md:
tools_checked: true
```

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
   - Keys to check: SNOWFLAKE_DEFAULT_CONNECTION_NAME, SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT_URL, SA_ROLE, SNOW_UTILS_DB, SA_USER, SA_ADMIN_ROLE, LOCAL_IP, SA_PAT

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

If memory has `infra_ready: true` with `sa_role` and `snow_utils_db` values:

- Use cached values
- Skip infra check, go to Step 3

**Otherwise, read from .env:**

```bash
grep -E "^(SA_ROLE|SNOW_UTILS_DB)=" .env
```

**If BOTH have values:** Skip to Step 3.

**If either is empty**, run check_setup.py with JSON output:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup --output json
```

Parse the JSON response to determine status:

- `ready: true` → Infrastructure exists, skip to Step 3
- `ready: false` → Need to create infrastructure

**If not ready**, use `ask_user_question` to confirm:

- Show suggested values from JSON (`defaults.role`, `defaults.database`)
- Ask user to confirm or provide custom values

**If user confirms setup**, run:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup --role <ROLE> --db <DB> --user <USER> --admin-role <SA_ADMIN_ROLE> --setup
```

**After setup completes, update .env:**

- `SA_ROLE=<value user confirmed>`
- `SNOW_UTILS_DB=<value user confirmed>`
- `SA_ADMIN_ROLE=<value user confirmed>`

**Update memory:**

```
Update /memories/snow-utils-prereqs.md:
tools_checked: true
infra_ready: true
sa_role: <VALUE>
snow_utils_db: <VALUE>
sa_admin_role: <VALUE>
```

### Step 3: Gather Requirements (Demo-Context Naming)

**Detect demo context from current directory:**

```bash
basename $(pwd)
```

Example: `hirc-duckdb-demo` → demo context = `HIRC_DUCKDB_DEMO`

**Read existing values from .env:**

```bash
grep -E "^(SNOWFLAKE_USER|SA_ROLE|SNOW_UTILS_DB)=" .env
```

**NAMING CONVENTION (Demo-Context):**

Both SA_ROLE and service user should use demo context for consistency:

| Variable | Pattern | Example (demo=hirc-duckdb-demo) |
|----------|---------|--------------------------------|
| SA_ROLE | `{DEMO}_ACCESS` | `HIRC_DUCKDB_DEMO_ACCESS` |
| SA_USER | `{DEMO}_RUNNER` | `HIRC_DUCKDB_DEMO_RUNNER` |

**Prompt for skill-specific values with demo-aware defaults:**

```
PAT Configuration for demo: <DEMO_CONTEXT>

1. Service user name [default: <DEMO>_RUNNER]:
2. PAT role [default: <DEMO>_ACCESS]:
3. Admin role for setup [default: from .env or ACCOUNTADMIN]:
4. Database for policy objects [default: from SNOW_UTILS_DB]:
5. PAT expiry days [default: 30]:
```

**STOP**: Wait for user input.

**After user provides input, update .env:**

- `SA_USER=<confirmed_value>`
- `SA_ROLE=<confirmed_value>`
- `SA_ADMIN_ROLE=<confirmed_value>`

### Step 3.5: Check for Existing PAT

**Check if PAT already exists for the user:**

```bash
set -a && source .env && set +a && snow sql -q "SHOW USER PATS FOR USER <SA_USER>" --format json
```

**If PAT exists**, use `ask_user_question` to ask:

| Option | Action |
|--------|--------|
| Rotate existing | Use `pat.py rotate` - regenerates token, keeps all policies intact |
| Remove and recreate | Use `pat.py remove` then `pat.py create` - fresh start with new policies |
| Cancel | Stop workflow |

**If user chooses "Rotate existing":**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  rotate --user <SA_USER> --role <SA_ROLE>
```

Then skip to Step 6 (Verify Connection).

**If user chooses "Remove and recreate":**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  remove --user <SA_USER> --db <SNOW_UTILS_DB> --yes
```

Then continue to Step 4.

**If no PAT exists:** Continue to Step 4.

### Step 4: Preview (Dry Run)

**Execute:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <SA_USER> --role <SA_ROLE> --db <SNOW_UTILS_DB> --dry-run
```

**CRITICAL: SHOW BOTH SUMMARY AND FULL SQL**

After running dry-run, display output in TWO parts:

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
-- Uses SA_ADMIN_ROLE from .env (defaults to ACCOUNTADMIN)
USE ROLE <SA_ADMIN_ROLE>;
CREATE USER IF NOT EXISTS HIRC_DUCKDB_DEMO_RUNNER
    TYPE = SERVICE
    COMMENT = 'Service user for PAT access';
GRANT ROLE HIRC_DUCKDB_DEMO_ACCESS TO USER HIRC_DUCKDB_DEMO_RUNNER;

-- Step 2: Create network rule and policy
USE ROLE <SA_ADMIN_ROLE>;
CREATE NETWORK RULE KAMESHS_SNOW_UTILS.NETWORKS.HIRC_DUCKDB_DEMO_RUNNER_NETWORK_RULE
    MODE = INGRESS
    TYPE = IPV4
    VALUE_LIST = ('192.168.1.1/32')
    COMMENT = 'Created by snow-utils';

-- Step 3: Create authentication policy
USE ROLE <SA_ADMIN_ROLE>;
CREATE SCHEMA IF NOT EXISTS KAMESHS_SNOW_UTILS.POLICIES;
CREATE OR ALTER AUTHENTICATION POLICY KAMESHS_SNOW_UTILS.POLICIES.HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY
    AUTHENTICATION_METHODS = ('PROGRAMMATIC_ACCESS_TOKEN')
    PAT_POLICY = (
        default_expiry_in_days = 30,
        max_expiry_in_days = 90,
        network_policy_evaluation = ENFORCED_REQUIRED
    );

ALTER USER HIRC_DUCKDB_DEMO_RUNNER SET AUTHENTICATION POLICY KAMESHS_SNOW_UTILS.POLICIES.HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY;

-- Step 4: Create PAT
ALTER USER IF EXISTS HIRC_DUCKDB_DEMO_RUNNER ADD PAT HIRC_DUCKDB_DEMO_RUNNER_PAT ROLE_RESTRICTION = HIRC_DUCKDB_DEMO_ACCESS;
```

**FORBIDDEN:** Showing only summary without SQL. User MUST see BOTH parts on first display.

**STOP**: Wait for explicit user approval ("yes", "ok", "proceed") before creating resources.

### Step 5: Create Resources

**Execute:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <SA_USER> --role <SA_ROLE> --db <SNOW_UTILS_DB> --output json
```

**On success:**

- Token is written to .env as SA_PAT
- Show connection verification result
- **Write cleanup manifest** (see Step 7)

**On failure:** Present error and remediation steps.

### Step 6: Verify Connection

If `--skip-verify` was not used, connection is already verified.

Otherwise:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  verify --user <SA_USER>
```

### Step 7: Write Success Summary and Cleanup Manifest

**After successful creation, append to `snow-utils-manifest.md` in project directory.**

If file doesn't exist, create with header:

```markdown
# Snow-Utils Manifest

This manifest tracks resources created by snow-utils skills.
Each section can be cleaned up independently.
```

**Append skill section:**

```markdown
## snow-utils-pat
Created: <TIMESTAMP>

| Type | Name | Location |
|------|------|----------|
| User | HIRC_DUCKDB_DEMO_RUNNER | Account |
| Role | HIRC_DUCKDB_DEMO_ACCESS | Account |
| Network Rule | HIRC_DUCKDB_DEMO_RUNNER_NETWORK_RULE | KAMESHS_SNOW_UTILS.NETWORKS |
| Network Policy | HIRC_DUCKDB_DEMO_RUNNER_NETWORK_POLICY | Account |
| Auth Policy | HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY | KAMESHS_SNOW_UTILS.POLICIES |
| PAT | HIRC_DUCKDB_DEMO_RUNNER_PAT | User: HIRC_DUCKDB_DEMO_RUNNER |

### Cleanup (execute in order)

```sql
-- Uses SA_ADMIN_ROLE from .env (defaults to ACCOUNTADMIN)
USE ROLE <SA_ADMIN_ROLE>;
-- 1. Remove PAT
ALTER USER HIRC_DUCKDB_DEMO_RUNNER REMOVE PAT HIRC_DUCKDB_DEMO_RUNNER_PAT;
-- 2. Unset auth policy (MUST do before drop)
ALTER USER HIRC_DUCKDB_DEMO_RUNNER UNSET AUTHENTICATION POLICY;
-- 3. Drop auth policy
DROP AUTHENTICATION POLICY IF EXISTS KAMESHS_SNOW_UTILS.POLICIES.HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY;
-- 4. Unset network policy
ALTER USER HIRC_DUCKDB_DEMO_RUNNER UNSET NETWORK POLICY;
-- 5. Drop network policy
DROP NETWORK POLICY IF EXISTS HIRC_DUCKDB_DEMO_RUNNER_NETWORK_POLICY;
-- 6. Drop network rule
DROP NETWORK RULE IF EXISTS KAMESHS_SNOW_UTILS.NETWORKS.HIRC_DUCKDB_DEMO_RUNNER_NETWORK_RULE;
-- 7. Drop user
DROP USER IF EXISTS HIRC_DUCKDB_DEMO_RUNNER;
-- 8. Drop role (optional)
-- DROP ROLE IF EXISTS HIRC_DUCKDB_DEMO_ACCESS;
```

### One-liner

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py remove --user <SA_USER> --db <SNOW_UTILS_DB>
```

```

**Display success summary to user:**

```

PAT Setup Complete!

Resources Created:
  User:           HIRC_DUCKDB_DEMO_RUNNER
  Role:           HIRC_DUCKDB_DEMO_ACCESS
  Network Rule:   KAMESHS_SNOW_UTILS.NETWORKS.HIRC_DUCKDB_DEMO_RUNNER_NETWORK_RULE
  Network Policy: HIRC_DUCKDB_DEMO_RUNNER_NETWORK_POLICY
  Auth Policy:    KAMESHS_SNOW_UTILS.POLICIES.HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY
  PAT:            ***REDACTED*** (saved to .env as SA_PAT)

Manifest appended to: ./snow-utils-manifest.md

```

## PAT Security

**NEVER display PAT tokens in:**
- Diff output
- Log messages
- Console output (except initial creation confirmation)
- Summary displays

**Always mask as:** `***REDACTED***`

**When showing .env changes:**
```diff
+ SA_PAT=***REDACTED***
```

## Tools

### check_setup.py (from common)

**Description:** Pre-flight check for snow-utils infrastructure. Prompts interactively.

**Usage:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup
```

**DO NOT ADD ANY FLAGS.**

**Options:**

- `--quiet`, `-q`: Exit 0 if ready, 1 if not (scripting only)

### pat.py

**Description:** Creates and manages Snowflake PATs with network and auth policies.

**Commands:**

- `create`: Create service user, policies, and PAT
- `remove`: Remove all PAT-related resources (follows correct cleanup order)
- `rotate`: Rotate existing PAT
- `verify`: Test PAT connection

**Create Options:**

- `--user`: Service user name (required)
- `--role`: PAT role restriction (required)
- `--admin-role`: Role for creating policies (default: from SA_ADMIN_ROLE env)
- `--db`: Database for policy objects (required)
- `--dry-run`: Preview without creating
- `--output json`: Machine-readable output
- `--local-ip`: Override auto-detected IP
- `--default-expiry-days`: Token expiry (default: 30)

## Stopping Points

- Step 1: If connection checks fail
- Step 2: If infra check needed (prompts user)
- Step 3: After gathering requirements
- Step 3.5: If PAT exists (ask rotate/recreate/cancel)
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

**Cannot drop database (policy attached):** Use `snow-utils-manifest.md` cleanup commands in order, or run `pat.py remove`.

## Security Notes

- PAT tokens stored in .env with proper escaping
- PAT tokens NEVER displayed in diffs or logs (masked as ***REDACTED***)
- Network policy restricts access to specified IPs only
- Auth policy enforces PAT-only authentication
- Tokens have configurable expiry (default 30 days)
