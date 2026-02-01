---
name: snow-utils-networks
description: "Create Snowflake network rules and policies for IP allowlisting. Use when: setting up network security, creating ingress/egress rules, allowlisting GitHub Actions, Google IPs, or custom CIDRs. Triggers: network rule, network policy, IP allowlist, CIDR, ingress, egress, GitHub Actions IPs, firewall."
---

# Snowflake Network Rules & Policies

Creates and manages network rules and policies for IP-based access control in Snowflake.

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

### Step 2: Check Infrastructure (REQUIRED)

**Run pre-flight check with user's connection:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/check_setup.py \
  -c "${SNOWFLAKE_DEFAULT_CONNECTION_NAME}" \
  --role "${SA_ROLE:-SA_ROLE}" --db "${SNOW_UTILS_DB:-SNOW_UTILS}" --quiet
```

**If exit code is non-zero (infrastructure missing):**

1. **Ask user**: "The snow-utils infrastructure (SA_ROLE and SNOW_UTILS_DB) is not set up. Would you like to create it now? This requires ACCOUNTADMIN role."

2. **If user agrees**, run setup:
   ```bash
   uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/check_setup.py \
     -c "${SNOWFLAKE_DEFAULT_CONNECTION_NAME}" \
     --role "${SA_ROLE:-SA_ROLE}" --db "${SNOW_UTILS_DB:-SNOW_UTILS}" --auto-setup
   ```

3. **If user declines**, explain they need to run setup first:
   - `snow sql -f snow-utils-setup.sql --templating=all --role ACCOUNTADMIN`
   - Or use the snow-bin-utils project: `task snow-utils:setup`

**If exit code is 0**: Continue to Step 3.

### Step 3: Gather Requirements

**Use connection test results as prompt defaults** (from Step 1):
- Database: use SNOW_UTILS_DB from .env (default: SNOW_UTILS)
- Role: use SA_ROLE from .env (default: SA_ROLE)
- Schema: default to NETWORKS

**Ask user:**
```
To create the network rule:
1. Rule name:
2. Database for network objects (default: SNOW_UTILS):
3. Schema (default: NETWORKS):
4. IP sources to include:
   - Local IP (auto-detected, default: ON)
   - GitHub Actions IPs
   - Google IPs
   - Custom CIDRs
5. Create network policy? (name if yes)
```

**Note:** Mode defaults to INGRESS. Only ask about mode if user mentions egress/outbound.

**⚠️ STOP**: Wait for user input.

**After user provides input, update `.env` with their values:**

Update these variables in `.env`:
- `NW_RULE_NAME=<user_rule_name>`
- `NW_RULE_DB=<user_database>` (if different from SNOW_UTILS_DB)
- `NW_RULE_SCHEMA=<user_schema>`

### Step 4: Preview (Dry Run)

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule create --name <NAME> --db <DB> \
  [--allow-local] [--allow-gh] [--allow-google] [--values <CIDRs>] \
  [--policy <POLICY_NAME>] --dry-run
```

**CRITICAL: You MUST show ALL SQL from the dry-run output. Do NOT skip or summarize.**

**Section 1: Resources Summary**
List what would be created with actual names from output.

**Section 2: ALL SQL Statements (REQUIRED - DO NOT SKIP)**
Copy the COMPLETE SQL from output and display as:

```sql
-- Create database and schema
CREATE DATABASE IF NOT EXISTS ...;
CREATE SCHEMA IF NOT EXISTS ...;

-- Create network rule
CREATE IF NOT EXISTS NETWORK RULE ...
  MODE = INGRESS
  TYPE = IPV4
  VALUE_LIST = (...)
  COMMENT = '...';

-- Create network policy (if requested)
CREATE IF NOT EXISTS NETWORK POLICY ...
  ALLOWED_NETWORK_RULE_LIST = (...)
  BLOCKED_NETWORK_RULE_LIST = ()
  COMMENT = '...';
```

**FAILURE TO SHOW COMPLETE SQL IS A SKILL VIOLATION.**

**⚠️ STOP**: Get approval before creating resources.

### Step 5: Create Resources

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule create --name <NAME> --db <DB> \
  [--allow-local] [--allow-gh] [--allow-google] [--values <CIDRs>] \
  [--policy <POLICY_NAME>]
```

**On success**: Show created rule FQN and policy name (if created).

**On failure**: Present error and remediation steps.

### Step 6: Verify

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule list --db <DB>
```

## Tools

### check_setup.py

**Description**: Pre-flight check for snow-utils infrastructure.

**Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/check_setup.py \
  [--role SA_ROLE] [--db SNOW_UTILS] [--auto-setup] [--quiet]
```

**Options:**
- `--role`, `-r`: SA role name (default: SA_ROLE, env: SA_ROLE)
- `--db`, `-d`: Database name (default: SNOW_UTILS, env: SNOW_UTILS_DB)
- `--auto-setup`: Automatically run setup if needed (no prompt)
- `--quiet`, `-q`: Exit 0 if ready, 1 if not (no output)

**Exit codes:**
- 0: Infrastructure ready
- 1: Infrastructure missing (setup declined or failed)
- 2: Error during check

### network.py

**Description**: Creates and manages Snowflake network rules and policies.

**Command Groups:**
- `rule` - Manage network rules (create, list, delete)
- `policy` - Manage network policies (create, alter, list, delete)

**Rule Create Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule create --name NAME --db DATABASE \
  [--schema SCHEMA] [--mode ingress|egress] [--type ipv4|host_port|awsvpceid] \
  [--values CIDRs] [--allow-local] [--allow-gh] [--allow-google] \
  [--policy POLICY_NAME] [--force] [--dry-run]
```

**Key Options:**
- `--name, -n`: Network rule name (required)
- `--db`: Database for rule (required)
- `--schema, -s`: Schema (default: NETWORKS)
- `--mode, -m`: INGRESS or EGRESS (default: INGRESS)
- `--type, -t`: IPV4, HOST_PORT, or AWSVPCEID (default: IPV4)
- `--values`: Comma-separated CIDRs or values
- `--allow-local`: Include auto-detected local IP (default: ON)
- `--allow-gh, -G`: Include GitHub Actions IPs
- `--allow-google, -g`: Include Google IPs
- `--policy, -p`: Also create network policy with this name
- `--force, -f`: Use CREATE OR REPLACE instead of CREATE IF NOT EXISTS
- `--dry-run`: Preview SQL without executing

**Rule List/Delete:**
```bash
network.py rule list --db DATABASE [--schema SCHEMA]
network.py rule delete --name NAME --db DATABASE [--schema SCHEMA]
```

**Policy Create/Alter/Delete:**
```bash
network.py policy create --name NAME --rules "db.schema.rule1,db.schema.rule2"
network.py policy alter --name NAME --rules "db.schema.rule3"
network.py policy delete --name NAME [--user USER_TO_UNSET]
network.py policy list
```

## Stopping Points

- ✋ Step 1: If environment checks fail
- ✋ Step 2: If infrastructure missing (ask user to set up)
- ✋ Step 3: After gathering requirements  
- ✋ Step 4: After dry-run preview (get approval)
- ✋ Step 5: If creation fails

## Output

- Network rule (IPV4, HOST_PORT, or AWSVPCEID)
- Network policy (optional, linked to rule)
- Auto-fetched IPs from GitHub Actions API, Google IPs

## Troubleshooting

**Infrastructure not set up**: Run `check_setup.py --auto-setup` or manually run setup with ACCOUNTADMIN.

**Permission denied**: SA_ROLE needs CREATE NETWORK RULE and CREATE NETWORK POLICY privileges. Run `task snow-utils:setup` to create role with proper grants.

**Rule already exists**: Use `--force` to replace existing rule.

**GitHub API rate limit**: GitHub Actions IPs are cached. Wait and retry.

**Invalid CIDR**: Ensure CIDRs are in x.x.x.x/mask format.

## Security Notes

- Network rules control IP-based access to Snowflake
- INGRESS rules restrict incoming connections
- EGRESS rules restrict outgoing connections (for external functions)
- Policies combine multiple rules for flexible access control
- Use specific CIDRs, not 0.0.0.0/0
- SA_ROLE has scoped privileges with no grant delegation
