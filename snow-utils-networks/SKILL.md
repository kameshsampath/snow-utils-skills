---
name: snow-utils-networks
description: "Create Snowflake network rules and policies for IP allowlisting. Use when: setting up network security, creating ingress/egress rules, allowlisting GitHub Actions, Google IPs, or custom CIDRs. Triggers: network rule, network policy, IP allowlist, CIDR, ingress, egress, GitHub Actions IPs, firewall."
---

# Snowflake Network Rules & Policies

Creates and manages network rules and policies for IP-based access control in Snowflake.

## Workflow

**📋 PREREQUISITE:** This skill requires `snow-utils-pat` to be run first. If SA_PAT is not set in .env, stop and direct user to run snow-utils-pat.

**⚠️ CONNECTION USAGE:** This skill uses the **user's Snowflake connection** (SNOWFLAKE_DEFAULT_CONNECTION_NAME) for all object creation. SA_ROLE is a consumer-only role with no CREATE privileges. Uses SA_ADMIN_ROLE (defaults to ACCOUNTADMIN) for privileged operations. After creation, USAGE grants are given to SA_ROLE so apps/demos can use the resources via SA_PAT.

**🚫 FORBIDDEN ACTIONS - NEVER DO THESE:**

- NEVER run SQL queries to discover/find/check values (no SHOW ROLES, SHOW DATABASES, SHOW NETWORK RULES)
- NEVER auto-populate empty .env values by querying Snowflake
- NEVER use flags that bypass user interaction: `--yes`, `-y`, `--auto-setup`, `--auto-approve`, `--quiet`, `--force`, `--non-interactive`
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER skip SQL in dry-run output - always show BOTH summary AND full SQL
- If .env values are empty, prompt user or run check_setup.py

**✅ INTERACTIVE PRINCIPLE:** This skill is designed to be interactive. At every decision point, ASK the user and WAIT for their response before proceeding.

**⚠️ ENVIRONMENT REQUIREMENT:** Once SNOWFLAKE_DEFAULT_CONNECTION_NAME is set in .env, ALL commands must use it. Always `source .env` before running any script commands.

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

**⚠️ STOP**: Do not proceed until all prerequisites are installed.

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
   - Keys to check: SNOWFLAKE_DEFAULT_CONNECTION_NAME, SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT_URL, SA_ROLE, SA_USER, SNOW_UTILS_DB, SA_PAT, NW_RULE_NAME, NW_RULE_DB, NW_RULE_SCHEMA, LOCAL_IP

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
grep -E "^(SA_ROLE|SA_USER|SNOW_UTILS_DB|SA_PAT)=" .env
```

**If SA_ROLE or SNOW_UTILS_DB is empty**, run check_setup.py first:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup
```

**If SA_PAT is empty:**

⚠️ **STOP** - Service account PAT is required before creating network rules.

Tell the user:

```
SA_PAT is not set. You need to create a PAT for the service account first.

Run the snow-utils-pat skill to create the PAT:
  "Create a PAT for service account"

This ensures the network rules are created using the service account credentials.
```

**Do NOT proceed** until SA_PAT is populated in .env.

**If ALL values present (SA_ROLE, SA_USER, SNOW_UTILS_DB, SA_PAT):**

**Update memory:**

```
Update /memories/snow-utils-prereqs.md:
tools_checked: true
infra_ready: true
sa_role: <SA_ROLE>
snow_utils_db: <SNOW_UTILS_DB>
sa_admin_role: <SA_ADMIN_ROLE>
```

Continue to Step 3.

### Step 3: Gather Requirements (with Semantic Prompts)

Read existing values from .env for semantic suggestions:

```bash
grep -E "^(SNOWFLAKE_USER|SNOW_UTILS_DB)=" .env
```

**Prompt for skill-specific values with semantic defaults:**

| Variable | Semantic Match | Prompt |
|----------|---------------|--------|
| NW_RULE_DB | SNOW_UTILS_DB | "Database for network objects [use {SNOW_UTILS_DB}?]:" |
| NW_RULE_NAME | SNOWFLAKE_USER | "Rule name [default: {USER}_LOCAL_ACCESS]:" |

**Part 1 - Basic Configuration:**

```
Network Rule Configuration:

1. Rule name [default: <SNOWFLAKE_USER>_LOCAL_ACCESS]:
2. Database for network objects:
   → Found SNOW_UTILS_DB=<value> - use same? [Y/n]:
3. Schema [default: NETWORKS]:
4. Create network policy? (name if yes):
```

**Part 2 - IP Sources Selection (multi-select):**

Use `ask_user_question` with `multiSelect: true`:

```
Which IP sources should be allowed access?
(Select all that apply)

☐ My current IP
  Auto-detected local IP for development

☐ GitHub Actions
  Allow CI/CD workflows from GitHub (IPv4 only)

☐ Google Cloud
  Allow Cloud Run, GKE, Compute Engine

☐ Custom CIDRs
  I'll specify IP ranges
```

**CoCo Conversion Table:**

| User Selection | CLI Flag |
|----------------|----------|
| My current IP | `--allow-local` |
| GitHub Actions | `--allow-gh` |
| Google Cloud | `--allow-google` |
| Custom CIDRs | → Follow-up prompt → `--values "..."` |

**If "Custom CIDRs" selected, prompt:**

```
Enter custom CIDRs (comma-separated):
Example: 10.0.0.0/8, 192.168.1.0/24
```

**⚠️ STOP**: Wait for user input on ALL values.

**After user provides input, update .env:**

- `NW_RULE_NAME=<confirmed_value>`
- `NW_RULE_DB=<confirmed_value>` (may equal SNOW_UTILS_DB)
- `NW_RULE_SCHEMA=<confirmed_value>`

### Step 3.5: Check for Existing Network Rule

**Check if network rule already exists:**

```bash
set -a && source .env && set +a && snow sql -q "SHOW NETWORK RULES LIKE '<NW_RULE_NAME>' IN SCHEMA <NW_RULE_DB>.<NW_RULE_SCHEMA>" --format json
```

**If rule exists**, use `ask_user_question` to ask:

| Option | Action |
|--------|--------|
| Update existing | Use `network.py rule update` - modifies IPs, keeps policy intact |
| Remove and recreate | Use `network.py rule delete` then `rule create` - fresh start |
| Cancel | Stop workflow |

**If user chooses "Update existing":**

Show same IP sources multi-select as Step 3:

```
Which IP sources should be allowed access?
(Select all that apply)

☐ My current IP
  Auto-detected local IP for development

☐ GitHub Actions
  Allow CI/CD workflows from GitHub (IPv4 only)

☐ Google Cloud
  Allow Cloud Run, GKE, Compute Engine

☐ Custom CIDRs
  I'll specify IP ranges
```

Then execute with converted flags:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule update --name <NW_RULE_NAME> --db <NW_RULE_DB> \
  [--allow-local] [--allow-gh] [--allow-google] [--values <CIDRs>]
```

Then skip to Step 6 (Verify).

**If user chooses "Remove and recreate":**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule delete --name <NW_RULE_NAME> --db <NW_RULE_DB>
```

Then continue to Step 4.

**If no rule exists:** Continue to Step 4.

**Execute:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule create --name <NW_RULE_NAME> --db <NW_RULE_DB> \
  [--allow-local] [--allow-gh] [--allow-google] [--values <CIDRs>] \
  [--policy <POLICY_NAME>] --dry-run
```

**🔴 CRITICAL: SHOW BOTH SUMMARY AND FULL SQL**

After running dry-run, display output in TWO parts:

**Part 1 - Resource Summary (brief):**

```
Rule Name: MY_DB.NETWORKS.MY_RULE
Mode:      INGRESS
Type:      IPV4
Values:    3 CIDRs
```

**Part 2 - Full SQL (MANDATORY - do not skip on first display):**

```sql
CREATE NETWORK RULE MY_DB.NETWORKS.MY_RULE
    MODE = INGRESS
    TYPE = IPV4
    VALUE_LIST = ('192.168.1.1/32', '10.0.0.0/8', '172.16.0.0/12')
    COMMENT = 'Created by snow-utils';
```

**FORBIDDEN:** Showing only summary without SQL. User MUST see BOTH parts on first display.

**⚠️ STOP**: Wait for explicit user approval ("yes", "ok", "proceed") before creating resources.

### Step 5: Create Resources

**Execute:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule create --name <NW_RULE_NAME> --db <NW_RULE_DB> \
  [--allow-local] [--allow-gh] [--allow-google] [--values <CIDRs>] \
  [--policy <POLICY_NAME>]
```

**On success:**

- Show created resources
- Write cleanup manifest (see Step 7)

**On failure:** Present error and remediation steps.

### Step 6: Verify

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule list --db <NW_RULE_DB>
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
## snow-utils-networks
Created: <TIMESTAMP>

| Type | Name | Location |
|------|------|----------|
| Network Rule | HIRC_DUCKDB_DEMO_ACCESS_RULE | KAMESHS_SNOW_UTILS.NETWORKS |
| Network Policy | HIRC_DUCKDB_DEMO_ACCESS_POLICY | Account |

### Cleanup

```sql
-- Uses SA_ADMIN_ROLE from .env (defaults to ACCOUNTADMIN)
USE ROLE <SA_ADMIN_ROLE>;
-- 1. Drop network policy (account-level)
DROP NETWORK POLICY IF EXISTS HIRC_DUCKDB_DEMO_ACCESS_POLICY;
-- 2. Drop network rule (schema-level)
DROP NETWORK RULE IF EXISTS KAMESHS_SNOW_UTILS.NETWORKS.HIRC_DUCKDB_DEMO_ACCESS_RULE;
```

```

**Display success summary to user:**

```

Network Setup Complete!

Resources Created:
  Network Rule:   KAMESHS_SNOW_UTILS.NETWORKS.HIRC_DUCKDB_DEMO_ACCESS_RULE
  Network Policy: HIRC_DUCKDB_DEMO_ACCESS_POLICY
  CIDRs:          192.168.1.1/32, 10.0.0.0/8

Manifest appended to: ./snow-utils-manifest.md

```

## Tools

### check_setup.py (from common)

**Description:** Pre-flight check for snow-utils infrastructure. Prompts interactively.

**Usage:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup
```

**⚠️ DO NOT ADD ANY FLAGS.**

**Options:**

- `--quiet`, `-q`: Exit 0 if ready, 1 if not (scripting only)

### network.py

**Description:** Creates and manages Snowflake network rules and policies.

**Command Groups:**

- `rule` - Manage network rules (create, list, delete)
- `policy` - Manage network policies (create, alter, list, delete)

**Rule Create Options:**

- `--name, -n`: Network rule name (required)
- `--db`: Database for rule (required)
- `--schema, -s`: Schema (default: NETWORKS)
- `--mode, -m`: INGRESS or EGRESS (default: INGRESS)
- `--values`: Comma-separated CIDRs
- `--allow-local`: Include auto-detected local IP
- `--allow-gh, -G`: Include GitHub Actions IPs
- `--allow-google, -g`: Include Google IPs
- `--policy, -p`: Also create network policy
- `--dry-run`: Preview SQL without executing

## Stopping Points

- ✋ Step 1: If connection checks fail
- ✋ Step 2: If infra check needed (prompts user)
- ✋ Step 3: After gathering requirements
- ✋ Step 4: After dry-run preview (get approval)

## Output

- Network rule (IPV4, HOST_PORT, or AWSVPCEID)
- Network policy (optional, linked to rule)
- Updated .env with all values

## Troubleshooting

**Infrastructure not set up:** Run `python -m snow_utils_common.check_setup` from common - it will prompt and offer to create.

**Permission denied:** SA_ROLE needs CREATE NETWORK RULE and CREATE NETWORK POLICY privileges.

**Rule already exists:** Use --force to replace existing rule.

**Invalid CIDR:** Ensure CIDRs are in x.x.x.x/mask format.

## Security Notes

- Network rules control IP-based access to Snowflake
- INGRESS rules restrict incoming connections
- Use specific CIDRs, not 0.0.0.0/0
