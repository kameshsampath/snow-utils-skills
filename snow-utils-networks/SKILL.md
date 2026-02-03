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
-- Uses SA_ADMIN_ROLE from .env (defaults to ACCOUNTADMIN)
USE ROLE <SA_ADMIN_ROLE>;
CREATE NETWORK RULE MY_DB.NETWORKS.MYAPP_RUNNER_NETWORK_RULE
    MODE = INGRESS
    TYPE = IPV4
    VALUE_LIST = ('192.168.1.1/32', '10.0.0.0/8', '172.16.0.0/12')
    COMMENT = 'MYAPP network rule - managed by snow-utils-networks';

CREATE NETWORK POLICY MYAPP_RUNNER_NETWORK_POLICY
    ALLOWED_NETWORK_RULE_LIST = ('MY_DB.NETWORKS.MYAPP_RUNNER_NETWORK_RULE')
    COMMENT = 'MYAPP network policy - managed by snow-utils-networks';
```

**COMMENT Pattern:** `{CONTEXT} {resource_type} - managed by snow-utils-networks`

**Context Inference:**

- Derived from NW_RULE_NAME by stripping suffixes: `_NETWORK_RULE`, `_RULE`, `_RUNNER`
- Example: `MYAPP_RUNNER_NETWORK_RULE` → `MYAPP`
- Can be overridden via root CLI option: `network.py --comment "MY_PROJECT" rule create ...`

This enables:

- Easy identification of resources by project context
- Filtering resources by skill: `SHOW NETWORK RULES WHERE COMMENT LIKE '%snow-utils-networks%'`
- Cleanup discovery across multiple projects

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

**Manifest Location:** `.snow-utils/snow-utils-manifest.md`

**Create directory if needed:**

```bash
mkdir -p .snow-utils
```

**If manifest doesn't exist, create with header:**

```markdown
# Snow-Utils Manifest

This manifest tracks Snowflake resources created by snow-utils skills.
Each skill section is bounded by START/END markers for easy identification.
CoCo can use this manifest to replay creation or cleanup resources.

---
```

#### Progressive Manifest Writing

**Update manifest AFTER EACH resource is successfully created (not at the end).**

**After network rule created:**

```markdown
<!-- START -- snow-utils-networks -->
## Network Resources: {COMMENT_PREFIX}

**Created:** {TIMESTAMP}
**Rule Name:** {NW_RULE_NAME}
**Database:** {NW_RULE_DB}
**Status:** IN_PROGRESS

### Resources (creation order)

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Network Rule | {NW_RULE_NAME} | {NW_RULE_DB}.{NW_RULE_SCHEMA} | ✓ |
| 2 | Network Policy | {NW_RULE_NAME}_POLICY | Account | pending |

### IP Sources

| Source | Included |
|--------|----------|
| Local IP | {LOCAL_IP} |
| GitHub Actions | {yes/no} |
| Google Cloud | {yes/no} |
| Custom CIDRs | {list or none} |
<!-- END -- snow-utils-networks -->
```

**After all resources created, update Status to COMPLETE and add cleanup:**

```markdown
<!-- START -- snow-utils-networks -->
## Network Resources: {COMMENT_PREFIX}

**Created:** {TIMESTAMP}
**Rule Name:** {NW_RULE_NAME}
**Database:** {NW_RULE_DB}
**Status:** COMPLETE

### Resources (creation order)

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Network Rule | {NW_RULE_NAME} | {NW_RULE_DB}.{NW_RULE_SCHEMA} | ✓ |
| 2 | Network Policy | {NW_RULE_NAME}_POLICY | Account | ✓ |

### IP Sources

| Source | Included |
|--------|----------|
| Local IP | {LOCAL_IP} |
| GitHub Actions | {yes/no} |
| Google Cloud | {yes/no} |
| Custom CIDRs | {list or none} |

### Cleanup Instructions (dependency order)

```sql
USE ROLE {SA_ADMIN_ROLE};
-- 1. Drop network policy first (depends on rule)
DROP NETWORK POLICY IF EXISTS {NW_RULE_NAME}_POLICY;
-- 2. Drop network rule
DROP NETWORK RULE IF EXISTS {NW_RULE_DB}.{NW_RULE_SCHEMA}.{NW_RULE_NAME};
```

### CLI Cleanup

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py rule delete --name {NW_RULE_NAME} --db {NW_RULE_DB}
```
<!-- END -- snow-utils-networks -->
```

#### Remove Flow (Reads Manifest First)

**On `rule delete` command:**

1. **Check manifest exists:** `.snow-utils/snow-utils-manifest.md`
2. **If exists:** Read `<!-- START -- snow-utils-networks -->` section for exact resource names
3. **Use manifest values** for cleanup instead of inferring from naming convention
4. **After cleanup success:** Remove the `<!-- START -- snow-utils-networks -->` to `<!-- END -- snow-utils-networks -->` section
5. **If manifest becomes empty** (only header): Optionally delete the file

#### Replay Flow (Single Confirmation)

**If user asks to replay/recreate from manifest:**

1. **Read manifest** `.snow-utils/snow-utils-manifest.md`
2. **Find section** `<!-- START -- snow-utils-networks -->`
3. **Display info summary with single confirmation:**

```

ℹ️  Replay from manifest will create:

  1. Network Rule:   {NW_RULE_NAME}
  2. Network Policy: {NW_RULE_NAME}_POLICY

IP Sources from manifest:
  Local IP:       {LOCAL_IP}
  GitHub Actions: {yes/no}
  Google Cloud:   {yes/no}
  Custom CIDRs:   {list}

Proceed with creation? [yes/no]

```

4. **On "yes":** Execute all creation steps without individual confirmations
5. **Update manifest** progressively as each resource is created

#### Resume Flow (Partial Creation Recovery)

**If manifest shows Status: IN_PROGRESS:**

1. **Read which resources have status `✓`** (already created)
2. **Display resume info:**

```

ℹ️  Resuming from partial creation:

  ✓ Network Rule:   CREATED

- Network Policy: PENDING

Continue from Network Policy creation? [yes/no]

```

3. **On "yes":** Continue from first `pending` resource
4. **Update manifest** as each remaining resource is created

**Display success summary to user:**

```

Network Setup Complete!

Resources Created:
  Network Rule:   {NW_RULE_DB}.{NW_RULE_SCHEMA}.{NW_RULE_NAME}
  Network Policy: {NW_RULE_NAME}_POLICY
  CIDRs:          {count} IP ranges

Manifest updated: .snow-utils/snow-utils-manifest.md

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

**CRITICAL RULES FOR COCO:**

| Rule | Description |
|------|-------------|
| **Always confirm** | NEVER execute create, update, or delete without explicit user confirmation |
| **Show what will happen** | Display SQL preview or summary BEFORE asking for confirmation |
| **One operation at a time** | Don't chain multiple destructive operations |
| **Fail fast** | Check prerequisites before running; stop with clear error if not met |

**Pre-Check Rules (Fail Fast):**

| Command | Pre-Check | If Fails |
|---------|-----------|----------|
| `rule create` | Rule doesn't exist | Stop: "Rule {name} already exists. Use `update` to modify or `delete` first." |
| `rule update` | Rule exists | Stop: "Rule {name} not found. Use `create` instead." |
| `rule delete` | Rule exists | Proceed gracefully (idempotent with IF EXISTS) |

**Command Selection Rules:**

| Scenario | Command | When to Use |
|----------|---------|-------------|
| New rule needed | `rule create` | No existing rule, or chose "Remove and recreate" in Step 3.5 |
| Rule exists, modify IPs | `rule update` | User chose "Update existing" in Step 3.5 |
| Full cleanup | `rule delete` | User explicitly requests cleanup |
| List rules | `rule list` | Verify creation or troubleshoot |

**Confirmation Flow:**

1. **create**: Show SQL preview (Step 4) → Ask "Proceed with creation?" → Execute only on "yes"
2. **update**: Show current vs new IPs → Ask "Update rule with these IPs?" → Execute only on "yes"
3. **delete**: Show resources to be deleted → Ask "Confirm deletion?" → Execute only on "yes"

**Post-Operation Rules:**

| Command | After Success |
|---------|---------------|
| `create` | Add section to `.snow-utils/snow-utils-manifest.md` → Update manifest progressively |
| `update` | Update manifest with new IP list |
| `delete` | Remove `snow-utils-networks` section from manifest |

**Command Groups:**

- `rule` - Manage network rules (create, update, list, delete)
- `policy` - Manage network policies (create, alter, list, delete)

**Rule Create Options:**

- `--name, -n`: Network rule name (required)
- `--db`: Database for rule (required)
- `--schema, -s`: Schema (default: NETWORKS)
- `--mode, -m`: INGRESS or EGRESS (default: INGRESS)
- `--values`: Comma-separated CIDRs
- `--allow-local`: Include auto-detected local IP
- `--allow-gh, -G`: Include GitHub Actions IPs (IPv4 only - see note below)
- `--allow-google, -g`: Include Google IPs
- `--policy, -p`: Also create network policy
- `--dry-run`: Preview SQL without executing

**⚠️ IPv4-Only Note for GitHub Actions:**

GitHub provides both IPv4 and IPv6 ranges in their meta API, but Snowflake network rules with `TYPE = IPV4` only support IPv4 addresses. The `--allow-gh` flag automatically filters to IPv4 ranges only.

If you need IPv6 support, you would need to create a separate network rule with `TYPE = IPV6` (not currently supported by this skill).

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
