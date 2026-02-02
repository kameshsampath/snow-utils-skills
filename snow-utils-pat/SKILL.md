---
name: snow-utils-pat
description: "Create Snowflake Programmatic Access Tokens (PATs) for service accounts. Use when: setting up service user, creating PAT, configuring authentication policy, network policy for PAT. Triggers: programmatic access token, PAT, service account, snowflake authentication."
---

# Snowflake PAT Setup

Creates service users, network policies, authentication policies, and Programmatic Access Tokens for automation.

## Workflow

**🚫 FORBIDDEN ACTIONS - NEVER DO THESE:**

- NEVER run SQL queries to discover/find/check values (no SHOW ROLES, SHOW DATABASES, SHOW USERS)
- NEVER auto-populate empty .env values by querying Snowflake
- NEVER use flags that bypass user interaction: `--yes`, `-y`, `--auto-setup`, `--auto-approve`, `--quiet`, `--force`, `--non-interactive`
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER skip SQL in dry-run output - always show BOTH summary AND full SQL
- If .env values are empty, prompt user or run check_setup.py

**✅ INTERACTIVE PRINCIPLE:** This skill is designed to be interactive. At every decision point, ASK the user and WAIT for their response before proceeding.

**⚠️ ENVIRONMENT REQUIREMENT:** Once SNOWFLAKE_DEFAULT_CONNECTION_NAME is set in .env, ALL commands must use it. Always `source .env` before running any script commands.

### Step 0: Check Prerequisites

**Check required tools are installed:**

```bash
command -v uv >/dev/null 2>&1 && echo "uv: OK" || echo "uv: MISSING"
command -v snow >/dev/null 2>&1 && echo "snow: OK" || echo "snow: MISSING"
```

**If any tool is MISSING, stop and provide installation instructions:**

| Tool | Install Command |
|------|-----------------|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `snow` | `pip install snowflake-cli` or `uv tool install snowflake-cli` |

**⚠️ STOP**: Do not proceed until all prerequisites are installed.

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

Read SA_ROLE and SNOW_UTILS_DB from .env:

```bash
grep -E "^(SA_ROLE|SNOW_UTILS_DB)=" .env
```

**If BOTH have values:** Skip to Step 3.

**If either is empty**, run check_setup.py:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/check_setup.py
```

The script will:

1. Read SNOWFLAKE_USER from environment for context
2. Prompt for SA Role name (suggests {USER}_SNOW_UTILS_SA)
3. Prompt for Database name (suggests {USER}_SNOW_UTILS)
4. Check if they exist, offer to create if missing

**After script completes, update .env:**

- `SA_ROLE=<value user confirmed>`
- `SNOW_UTILS_DB=<value user confirmed>`

### Step 3: Gather Requirements (with Semantic Prompts)

Read existing values from .env for semantic suggestions:

```bash
grep -E "^(SNOWFLAKE_USER|SA_ROLE|SNOW_UTILS_DB)=" .env
```

**Prompt for skill-specific values with semantic defaults:**

| Variable | Semantic Match | Prompt |
|----------|---------------|--------|
| SA_USER | SNOWFLAKE_USER | "Service user name [default: {SNOWFLAKE_USER}_service]:" |
| SA_ADMIN_ROLE | SA_ROLE | "Admin role for policies [default: use {SA_ROLE}?]:" |

**Full prompt:**

```
PAT Configuration:

1. Service user name [default: <SNOWFLAKE_USER>_service]:
2. PAT role (role the service account can use):
3. Admin role for creating policies:
   → Found SA_ROLE=<value> - use same? [Y/n]:
4. Database for policy objects:
   → Found SNOW_UTILS_DB=<value> - use same? [Y/n]:
5. PAT expiry days [default: 30]:
```

**⚠️ STOP**: Wait for user input.

**After user provides input, update .env:**

- `SA_USER=<confirmed_value>`
- `SA_ADMIN_ROLE=<confirmed_value>` (may equal SA_ROLE)

### Step 4: Preview (Dry Run)

**Execute:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <SA_USER> --role <PAT_ROLE> --db <SNOW_UTILS_DB> --dry-run
```

**🔴 CRITICAL: SHOW BOTH SUMMARY AND FULL SQL**

After running dry-run, display output in TWO parts:

**Part 1 - Resource Summary (brief):**

```
User:     MY_SERVICE_USER
Role:     MY_ROLE
Database: MY_DB
PAT Name: MY_SERVICE_USER_PAT
```

**Part 2 - Full SQL (MANDATORY - do not skip on first display):**

```sql
-- Step 1: Create service user
USE ROLE accountadmin;
CREATE USER IF NOT EXISTS MY_SERVICE_USER
    TYPE = SERVICE
    COMMENT = 'Service user for PAT access';
GRANT ROLE MY_ROLE TO USER MY_SERVICE_USER;

-- Step 2: Create network rule and policy
CREATE NETWORK RULE MY_DB.NETWORKS.MY_SERVICE_USER_NETWORK_RULE
    MODE = INGRESS
    TYPE = IPV4
    VALUE_LIST = ('192.168.1.1/32')
    COMMENT = 'Created by snow-utils';

-- Step 3: Create authentication policy
CREATE SCHEMA IF NOT EXISTS MY_DB.POLICIES;
CREATE OR ALTER AUTHENTICATION POLICY MY_DB.POLICIES.MY_SERVICE_USER_AUTH_POLICY
    AUTHENTICATION_METHODS = ('PROGRAMMATIC_ACCESS_TOKEN')
    PAT_POLICY = (
        default_expiry_in_days = 45,
        max_expiry_in_days = 90,
        network_policy_evaluation = ENFORCED_REQUIRED
    );

ALTER USER MY_SERVICE_USER SET AUTHENTICATION POLICY MY_DB.POLICIES.MY_SERVICE_USER_AUTH_POLICY;

-- Step 4: Create PAT
ALTER USER IF EXISTS MY_SERVICE_USER ADD PAT MY_SERVICE_USER_PAT ROLE_RESTRICTION = MY_ROLE;
```

**FORBIDDEN:** Showing only summary without SQL. User MUST see BOTH parts on first display.

**⚠️ STOP**: Wait for explicit user approval ("yes", "ok", "proceed") before creating resources.

### Step 5: Create Resources

**Execute:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <SA_USER> --role <PAT_ROLE> --db <SNOW_UTILS_DB> --output json
```

**On success:**

- Token is written to .env as SA_PAT
- Show connection verification result

**On failure:** Present error and remediation steps.

### Step 6: Verify Connection

If `--skip-verify` was not used, connection is already verified.

Otherwise:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  verify --user <SA_USER>
```

## Tools

### check_setup.py

**Description:** Pre-flight check for snow-utils infrastructure. Prompts interactively.

**Usage:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/check_setup.py
```

**⚠️ DO NOT ADD ANY FLAGS.**

**Options:**

- `--quiet`, `-q`: Exit 0 if ready, 1 if not (scripting only)

### pat.py

**Description:** Creates and manages Snowflake PATs with network and auth policies.

**Commands:**

- `create`: Create service user, policies, and PAT
- `remove`: Remove all PAT-related resources
- `rotate`: Rotate existing PAT
- `verify`: Test PAT connection

**Create Options:**

- `--user`: Service user name (required)
- `--role`: PAT role restriction (required)
- `--admin-role`: Role for creating policies (default: same as --role)
- `--db`: Database for policy objects (required)
- `--dry-run`: Preview without creating
- `--output json`: Machine-readable output
- `--local-ip`: Override auto-detected IP
- `--default-expiry-days`: Token expiry (default: 30)

## Stopping Points

- ✋ Step 1: If connection checks fail
- ✋ Step 2: If infra check needed (prompts user)
- ✋ Step 3: After gathering requirements
- ✋ Step 4: After dry-run preview (get approval)

## Output

- Service user (TYPE = SERVICE)
- Network rule with local IP
- Network policy (ENFORCED_REQUIRED)
- Authentication policy (PROGRAMMATIC_ACCESS_TOKEN only)
- PAT token (saved to .env as SA_PAT)
- Updated .env with all values

## Troubleshooting

**Infrastructure not set up:** Run check_setup.py - it will prompt and offer to create.

**Network policy blocking:** Ensure your IP is in the network rule. Use --local-ip to specify.

**PAT already exists:** Use --rotate to replace existing PAT.

**Connection verification failed:** Check network policy allows your IP.

## Security Notes

- PAT tokens stored in .env with proper escaping
- Network policy restricts access to specified IPs only
- Auth policy enforces PAT-only authentication
- Tokens have configurable expiry (default 30 days)
