---
name: snow-utils-pat
description: "Create Snowflake Programmatic Access Tokens (PATs) for service accounts. Use when: setting up service user, creating PAT, configuring authentication policy, network policy for PAT. Triggers: programmatic access token, PAT, service account, snowflake authentication."
---

# Snowflake PAT Setup

Creates service users, network policies, authentication policies, and Programmatic Access Tokens for automation.

## Workflow

### Step 1: Check Environment

**Actions:**

1. **Verify** project has required files:
   ```bash
   ls -la .env 2>/dev/null || echo "missing"
   ```

2. **If .env missing**, copy from `.env.example`:
   ```bash
   cp <SKILL_DIR>/.env.example .env
   ```
   
   **If .env exists**, MERGE new settings - do NOT overwrite:
   - Read existing .env
   - Add only missing keys from `.env.example`
   - Preserve user's existing values

3. **Verify** Snowflake connection and get defaults:
   ```bash
   snow connection list
   ```
   - If user needs to choose a connection, ask them to select one
   - Test the selected connection to get effective defaults:
   ```bash
   snow connection test -c <selected_connection> --format json
   ```
   - Extract defaults from test output: Role, Database, Warehouse
   - Set `SNOWFLAKE_DEFAULT_CONNECTION_NAME=<selected_connection>` in .env

4. **Check** required privileges:
   - CREATE USER (or use existing user)
   - CREATE NETWORK RULE, NETWORK POLICY
   - CREATE AUTHENTICATION POLICY

**If any check fails**: Stop and help user resolve.

### Step 2: Gather Requirements

**Use connection test results as prompt defaults** (from Step 1):
- Database: use test output's Database (if not "not set")
- Role: use test output's Role

**Ask user:**
```
To create the PAT:
1. Service user name:
2. PAT role (default: <connection_role>):
3. Admin role (default: same as PAT role):
4. Database for policy objects (default: <connection_database>):
5. PAT expiry days (default: 30):
```

**⚠️ STOP**: Wait for user input.

**After user provides input, update `.env` with their values:**

Update these variables in `.env`:
- `SA_USER=<user_service_user_name>`
- `SA_ROLE=<user_pat_role>`
- `SA_ADMIN_ROLE=<user_admin_role>`
- `PAT_OBJECTS_DB=<user_database>`

This ensures values are saved for future runs (e.g., rotate, remove commands).

### Step 3: Preview (Dry Run)

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <USER> --role <ROLE> --db <DB> --dry-run
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

### Step 4: Create Resources

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <USER> --role <ROLE> --db <DB> --output json
```

**On success**: 
- Token is written to .env file
- Show connection verification result

**On failure**: Present error and remediation steps.

### Step 5: Verify Connection

If `--skip-verify` was not used, connection is already verified.

Otherwise:
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  verify --user <USER>
```

## Tools

### pat.py

**Description**: Creates and manages Snowflake PATs with network and auth policies.

**Commands:**
- `create`: Create service user, policies, and PAT
- `remove`: Remove all PAT-related resources
- `rotate`: Rotate existing PAT
- `verify`: Test PAT connection

**Create Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user USER --role ROLE --db DATABASE \
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
  remove --user USER --db DATABASE
```

## Stopping Points

- ✋ Step 1: If environment checks fail
- ✋ Step 2: After gathering requirements  
- ✋ Step 3: After dry-run preview (get approval)
- ✋ Step 4: If creation fails

## Output

- Service user (TYPE = SERVICE)
- Network rule with local IP
- Network policy (ENFORCED_REQUIRED)
- Authentication policy (PROGRAMMATIC_ACCESS_TOKEN only)
- PAT token (saved to .env)
- Verified connection

## Troubleshooting

**Network policy blocking**: Ensure your IP is in the network rule. Run with `--local-ip` to specify.

**Permission denied**: Admin role needs CREATE NETWORK RULE, CREATE NETWORK POLICY, CREATE AUTHENTICATION POLICY privileges.

**PAT already exists**: Use `--rotate` to replace existing PAT.

**Connection verification failed**: Check network policy allows your IP and auth policy is correctly assigned.

## Security Notes

- PAT tokens are stored in .env with proper escaping
- Network policy restricts access to specified IPs only
- Auth policy enforces PAT-only authentication (no password)
- Tokens have configurable expiry (default 30 days, max 365)
