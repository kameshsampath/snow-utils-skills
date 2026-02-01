---
name: snow-utils-pat
description: "Create Snowflake Programmatic Access Tokens (PATs) for service accounts. Use when: setting up service user, creating PAT, configuring authentication policy, network policy for PAT. Triggers: programmatic access token, PAT, service account, snowflake authentication."
---

# Snowflake PAT Setup

Creates service users, network policies, authentication policies, and Programmatic Access Tokens for automation.

## Workflow

**🚫 FORBIDDEN ACTIONS - NEVER DO THESE:**
- NEVER run SQL queries to discover/find/check SA_ROLE, SNOW_UTILS_DB, or any infrastructure
- NEVER run `SHOW ROLES`, `SHOW DATABASES`, or similar to populate empty .env values
- NEVER auto-populate empty values by querying Snowflake
- If .env values are empty, they stay empty until the user provides them via interactive prompt

### Step 1: Check Environment

**Actions:**

1. **Verify** project has required files:
   ```bash
   ls -la .env 2>/dev/null || echo "missing"
   ```

2. **If .env missing**, copy EXACTLY from `.env.example`:
   ```bash
   cp <SKILL_DIR>/.env.example .env
   ```
   
   **If .env exists**, MERGE new settings - do NOT overwrite:
   - Read existing .env
   - Add only missing keys from `.env.example`
   - Preserve user's existing values

3. **Verify** Snowflake connection:
   ```bash
   snow connection list
   ```
   - If user needs to choose a connection, ask them to select one
   - Set ONLY `SNOWFLAKE_DEFAULT_CONNECTION_NAME=<selected_connection>` in .env

**⚠️ CRITICAL RULES FOR STEP 1:**
- Do NOT run any SQL queries (no SHOW ROLES, SHOW DATABASES, etc.)
- Do NOT try to discover or infer SA_ROLE or SNOW_UTILS_DB values
- Do NOT set these values - leave them empty in .env
- The ONLY value to set is SNOWFLAKE_DEFAULT_CONNECTION_NAME
- Proceed to Step 2 - the script will prompt user for values

**⚠️ STOP**: After setting connection, proceed DIRECTLY to Step 2. Do not run any additional commands.

### Step 2: Check Infrastructure (REQUIRED)

**Run pre-flight check with NO FLAGS** (script will prompt interactively):
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/check_setup.py
```

**⚠️ CRITICAL: Run the command EXACTLY as shown above.**
- Do NOT add any flags
- Do NOT source .env before running
- Let the script prompt the user interactively

The script will:
1. Prompt for SA Role name (default: SNOW_UTILS_SA)
2. Prompt for Database name (default: SNOW_UTILS)
3. Check if infrastructure exists
4. Offer to create it if missing (requires ACCOUNTADMIN)

**After setup completes, update `.env`** with the values user provided:
- `SA_ROLE=<user_role>`
- `SNOW_UTILS_DB=<user_db>`

**If user declines setup**, explain they need to run setup first:
- `snow sql -f snow-utils-setup.sql --templating all --role ACCOUNTADMIN`

**If exit code is 0**: Continue to Step 3.

### Step 3: Gather Requirements

**Ask user:**
```
To create the PAT:
1. Service user name:
2. PAT role (the role this service account can use):
3. Admin role (default: ${SA_ROLE} - the role with privileges to create policies):
4. Database for policy objects (default: ${SNOW_UTILS_DB}):
5. PAT expiry days (default: 30):
```

**⚠️ STOP**: Wait for user input.

**After user provides input, update `.env` with their values:**

Update these variables in `.env`:
- `SA_USER=<user_service_user_name>`
- `SA_ROLE=<user_admin_role>` (if different from default)
- `SNOW_UTILS_DB=<user_database>` (if different from default)

This ensures values are saved for future runs (e.g., rotate, remove commands).

### Step 4: Preview (Dry Run)

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  -c "${SNOWFLAKE_DEFAULT_CONNECTION_NAME}" \
  create --user <USER> --role <PAT_ROLE> --db <DB> --dry-run
```

**CRITICAL: You MUST show ALL SQL from the dry-run output. Do NOT skip or summarize.**

**Section 1: Resources Summary**
List what would be created with actual names from output.

**Section 2: ALL SQL Statements (REQUIRED - DO NOT SKIP)**
Copy the COMPLETE SQL from output under "SQL that would be executed:" and display as:

```sql
-- Step 1: Create service user
USE ROLE accountadmin;
CREATE USER IF NOT EXISTS ...
... (copy ALL SQL from output)

-- Step 2: Create network rule and policy
USE ROLE ...;
CREATE DATABASE IF NOT EXISTS ...;
CREATE OR REPLACE NETWORK RULE ...;
CREATE OR REPLACE NETWORK POLICY ...;
... (copy ALL SQL)

-- Step 3: Create authentication policy
CREATE OR ALTER AUTHENTICATION POLICY ...;
... (copy ALL SQL)

-- Step 4: Create PAT
ALTER USER IF EXISTS ... ADD PAT ...;
```

**FAILURE TO SHOW COMPLETE SQL IS A SKILL VIOLATION.** Users cannot approve without reviewing all statements.

**⚠️ STOP**: Get approval before creating resources.

### Step 5: Create Resources

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  -c "${SNOWFLAKE_DEFAULT_CONNECTION_NAME}" \
  create --user <USER> --role <PAT_ROLE> --db <DB> --output json
```

**On success**: 
- Token is written to .env file
- Show connection verification result

**On failure**: Present error and remediation steps.

### Step 6: Verify Connection

If `--skip-verify` was not used, connection is already verified.

Otherwise:
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  -c "${SNOWFLAKE_DEFAULT_CONNECTION_NAME}" \
  verify --user <USER>
```

## Tools

### check_setup.py

**Description**: Pre-flight check for snow-utils infrastructure. Prompts interactively for values.

**Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/check_setup.py
```

**⚠️ DO NOT ADD ANY FLAGS. The script will prompt interactively.**

**Options:**
- `--quiet`, `-q`: Exit 0 if ready, 1 if not (no output, for scripting only)

Uses the active Snowflake connection from SNOWFLAKE_DEFAULT_CONNECTION_NAME.

**Exit codes:**
- 0: Infrastructure ready
- 1: Infrastructure missing (setup declined or failed)
- 2: Error during check

### pat.py

**Description**: Creates and manages Snowflake PATs with network and auth policies.

**Global Options:**
- `--connection`, `-c`: Snowflake connection name [env: SNOWFLAKE_DEFAULT_CONNECTION_NAME]

**Commands:**
- `create`: Create service user, policies, and PAT
- `remove`: Remove all PAT-related resources
- `rotate`: Rotate existing PAT
- `verify`: Test PAT connection

**Create Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  [-c CONNECTION] create --user USER --role ROLE --db DATABASE \
  [--admin-role ADMIN_ROLE] [--dry-run] [--output json]
```

**Key Options:**
- `--user`: Service user name (required)
- `--role`: PAT role restriction (required)
- `--admin-role`: Role for creating policies (default: same as --role)
- `--db`: Database for policy objects (required)
- `--pat-name`: Custom PAT name (default: {USER}_PAT)
- `--rotate`: Replace existing PAT
- `--dry-run`: Preview without creating
- `--output json`: Machine-readable output
- `--local-ip`: Override auto-detected IP
- `--default-expiry-days`: Token expiry (default: 30)
- `--skip-verify`: Skip connection verification

**Remove Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  [-c CONNECTION] remove --user USER --db DATABASE
```

## Stopping Points

- ✋ Step 1: If environment checks fail
- ✋ Step 2: Interactive prompts for SA_ROLE/SNOW_UTILS_DB, then setup if needed
- ✋ Step 3: After gathering requirements  
- ✋ Step 4: After dry-run preview (get approval)
- ✋ Step 5: If creation fails

## Output

- Service user (TYPE = SERVICE)
- Network rule with local IP
- Network policy (ENFORCED_REQUIRED)
- Authentication policy (PROGRAMMATIC_ACCESS_TOKEN only)
- PAT token (saved to .env)
- Verified connection

## Troubleshooting

**Infrastructure not set up**: Run `check_setup.py` interactively or with `--auto-setup`.

**Network policy blocking**: Ensure your IP is in the network rule. Run with `--local-ip` to specify.

**Permission denied**: SA_ROLE needs CREATE NETWORK RULE, CREATE NETWORK POLICY, CREATE AUTHENTICATION POLICY privileges.

**PAT already exists**: Use `--rotate` to replace existing PAT.

**Connection verification failed**: Check network policy allows your IP and auth policy is correctly assigned.

## Security Notes

- PAT tokens are stored in .env with proper escaping
- Network policy restricts access to specified IPs only
- Auth policy enforces PAT-only authentication (no password)
- Tokens have configurable expiry (default 30 days, max 365)
- SA_ROLE has scoped privileges with no grant delegation
