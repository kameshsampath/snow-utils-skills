---
name: snow-utils-networks
description: "Create Snowflake network rules and policies for IP allowlisting. Use when: setting up network security, creating ingress/egress rules, allowlisting GitHub Actions, Google IPs, or custom CIDRs. Triggers: network rule, network policy, IP allowlist, CIDR, ingress, egress, GitHub Actions IPs, firewall, replay network, replay network manifest, recreate network, replay all manifests, replay all snow-utils."
---

# Snowflake Network Rules & Policies

Creates and manages network rules and policies for IP-based access control in Snowflake.

## Workflow

**📋 PREREQUISITE:** None. This skill can be used standalone or alongside other snow-utils skills.

**📍 MANIFEST FILE:** `.snow-utils/snow-utils-manifest.md` (ALWAYS this exact path and filename - never search for other patterns like *.yaml or *.*)

**⚠️ CONNECTION USAGE:** This skill uses the **user's Snowflake connection** (SNOWFLAKE_DEFAULT_CONNECTION_NAME) for all object creation. Uses admin_role from manifest (defaults to ACCOUNTADMIN) for privileged operations.

**🔄 IDEMPOTENCY NOTE:** Network rules use `CREATE OR REPLACE` (Snowflake does not support `IF NOT EXISTS` for network rules). Network policies use `CREATE IF NOT EXISTS` to preserve existing policies. Re-running create operations is safe for automation.

**🚫 FORBIDDEN ACTIONS - NEVER DO THESE:**

- NEVER run SQL queries to discover/find/check values (no SHOW ROLES, SHOW DATABASES, SHOW NETWORK RULES)
- NEVER auto-populate empty .env values by querying Snowflake
- NEVER use flags that bypass user interaction: `--yes`, `-y`, `--auto-setup`, `--auto-approve`, `--quiet`, `--force`, `--non-interactive`
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER skip SQL in dry-run output - always show BOTH summary AND full SQL
- **NEVER run raw SQL for cleanup** - ALWAYS use CLI commands (handles dependency order and detach/reattach)
- If .env values are empty, prompt user or run check_setup.py

**✅ INTERACTIVE PRINCIPLE:** This skill is designed to be interactive. At every decision point, ASK the user and WAIT for their response before proceeding.

**⚠️ ENVIRONMENT REQUIREMENT:** Once SNOWFLAKE_DEFAULT_CONNECTION_NAME is set in .env, ALL commands must use it. Always `source .env` before running any script commands.

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

**⚠️ STOP**: Do not proceed until all prerequisites are installed.

**After tools verified, write to manifest:**

```bash
mkdir -p .snow-utils && chmod 700 .snow-utils
# Create manifest with header if it doesn't exist
if [ ! -f .snow-utils/snow-utils-manifest.md ]; then
cat > .snow-utils/snow-utils-manifest.md << 'EOF'
# Snow-Utils Manifest

This manifest tracks Snowflake resources created by snow-utils skills.

---

## prereqs
tools_verified: <TODAY_DATE>
skills:
EOF
fi
# Add this skill's source URL if not already present
grep -q "networks:" .snow-utils/snow-utils-manifest.md || \
  echo "  networks: https://github.com/kameshsampath/snow-utils-skills/snow-utils-networks" >> .snow-utils/snow-utils-manifest.md
chmod 600 .snow-utils/snow-utils-manifest.md
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
   - Keys to check: SNOWFLAKE_DEFAULT_CONNECTION_NAME, SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT_URL, SNOW_UTILS_DB, NW_RULE_NAME, NW_RULE_DB, NW_RULE_SCHEMA, LOCAL_IP

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
- Skip infra check, go to Step 2a

**Otherwise, read from .env:**

```bash
grep -E "^SNOW_UTILS_DB=" .env
```

**If SNOW_UTILS_DB is empty**, run check_setup.py first:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup --suggest
```

If not ready, prompt user and run with `--run-setup`.

**If SNOW_UTILS_DB is present:**

**Update memory:**

```
Update /memories/snow-utils-prereqs.md:
tools_checked: true
infra_ready: true
snow_utils_db: <SNOW_UTILS_DB>
```

Continue to Step 2a.

### Step 2a: Admin Role from Manifest

**Purpose:** Networks skill requires elevated privileges for account-level objects. Get admin_role from manifest.

> **📍 MANIFEST FILE:** `.snow-utils/snow-utils-manifest.md` - always use this exact path, never search for other patterns

**Required privileges for Networks skill:**

| Privilege | Scope | Required For | Default Role |
|-----------|-------|--------------|--------------|
| USAGE | Database | Accessing SNOW_UTILS_DB | DB owner, ACCOUNTADMIN |
| CREATE NETWORK RULE | Schema | Creating network rules | Schema owner, ACCOUNTADMIN |
| CREATE NETWORK POLICY | Account | Creating network policies | SECURITYADMIN+ |

> **Note:** Only ACCOUNTADMIN has all these privileges by default. SECURITYADMIN lacks USAGE on databases.

**Ensure secured .snow-utils directory:**

```bash
mkdir -p .snow-utils && chmod 700 .snow-utils
```

**Check manifest for existing admin_role:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -A1 "## admin_role" | grep "networks:"
```

**If admin_role exists for networks:** Use it, continue to Step 2b (privilege verification).

**If admin_role NOT set for networks, check other skills:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -E "^(volumes|pat):" | head -1
```

**If another skill has admin_role set**, use `ask_user_question`:

```
Detected admin_role={value} from {skill} skill.

Use the same role for network operations?
- Yes, use {value}
- No, specify different role
```

- **If Yes:** Use detected role for networks
- **If No:** Prompt for role (see below)

**If no admin_role set for any skill**, prompt user with `ask_user_question` (type: "text", defaultValue: "ACCOUNTADMIN"):

```
Admin role for network operations:
[ACCOUNTADMIN]
```

**IMMEDIATELY write to manifest (before ANY resource creation):**

```bash
chmod 700 .snow-utils
cat >> .snow-utils/snow-utils-manifest.md << 'EOF'
## admin_role
networks: <USER_ROLE>
EOF
chmod 600 .snow-utils/snow-utils-manifest.md
```

Continue to Step 2b.

### Step 2b: Verify Admin Role Privileges

**If admin_role is NOT ACCOUNTADMIN**, verify it has required privileges:

```bash
set -a && source .env && set +a && snow sql -q "
SHOW GRANTS TO ROLE <ADMIN_ROLE>;
" --format json
```

**Check for these grants in the output:**

| Look For | Privilege | On |
|----------|-----------|-----|
| CREATE NETWORK RULE | `CREATE NETWORK RULE` | SCHEMA (SNOW_UTILS_DB.NETWORKS) |
| CREATE NETWORK POLICY | `CREATE NETWORK POLICY` | ACCOUNT |

**If any privilege is missing**, use `ask_user_question` with options:

| Option | Action |
|--------|--------|
| Grant missing privileges | Show GRANT statements for user to execute with elevated role |
| Use a different role | Prompt for role name with required privileges (default: SECURITYADMIN) |
| Cancel | Stop workflow |

**If user chooses "Grant missing privileges":**

Show SQL for each missing privilege:

```sql
-- Run as ACCOUNTADMIN or SECURITYADMIN
GRANT CREATE NETWORK RULE ON SCHEMA <SNOW_UTILS_DB>.NETWORKS TO ROLE <ADMIN_ROLE>;
GRANT CREATE NETWORK POLICY ON ACCOUNT TO ROLE <ADMIN_ROLE>;
```

**STOP**: Wait for user to confirm privileges have been granted, then re-check.

**If user chooses "Use a different role":**

Go back to Step 2a (prompt for role).

Continue to Step 3.

**If admin_role=SECURITYADMIN or ACCOUNTADMIN (default):** All privileges are available, continue to Step 3.

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

**Part 1b - Rule Mode Selection:**

> **Note:** ask_user_question supports max 4 options. POSTGRES modes are grouped.

Use `ask_user_question` with options (INGRESS pre-selected as default):

```
Network rule mode:

○ INGRESS (default)
  Control who can connect TO Snowflake

○ EGRESS
  Control what Snowflake can connect TO (external access)

○ INTERNAL_STAGE
  Internal stage access rules

○ POSTGRES
  PostgreSQL interface (Iceberg, external tables)
```

**If user selects POSTGRES:** Follow-up with direction question:

```
PostgreSQL interface direction:

○ POSTGRES_INGRESS (default)
  Incoming connections to PostgreSQL interface

○ POSTGRES_EGRESS
  Outbound connections from PostgreSQL interface
```

**CoCo Conversion:** Selected mode → `--mode <value>`

**Part 1c - Rule Type Selection (mode-dependent):**

> **⚠️ CRITICAL:** Mode and Type have constraints. Use wrong combination = Snowflake error!

**Mode-Type Compatibility Matrix:**

| Mode | Valid Types | Default | Notes |
|------|-------------|---------|-------|
| INGRESS | IPV4, AWSVPCEID | IPV4 | IP allowlisting |
| INTERNAL_STAGE | IPV4, AWSVPCEID | IPV4 | Stage access |
| EGRESS | HOST_PORT, IPV4 | HOST_PORT | Use HOST_PORT for hostname:port targets |
| POSTGRES_INGRESS | IPV4, AWSVPCEID | IPV4 | PostgreSQL incoming |
| POSTGRES_EGRESS | HOST_PORT, IPV4 | HOST_PORT | Use HOST_PORT for hostname:port targets |

**If mode is INGRESS, INTERNAL_STAGE, or POSTGRES_INGRESS:**

Use `ask_user_question` with IPV4 pre-selected:

```
Rule type:

○ IPV4 (default)
  IP addresses/CIDR ranges (e.g., 192.168.1.0/24)

○ AWSVPCEID
  AWS VPC Endpoint IDs
```

**If mode is EGRESS or POSTGRES_EGRESS:**

Use `ask_user_question` with HOST_PORT pre-selected:

```
Rule type:

○ HOST_PORT (recommended)
  Hostname:port targets (e.g., api.github.com:443)

○ IPV4
  Specific external IP addresses to connect to
```

**CoCo Conversion:** Selected type → `--type <value>`

**Part 2 - Value Input (type-dependent):**

> **⚠️ IMPORTANT:** IP source presets (--allow-local, --allow-gh, --allow-google) only work with IPV4 type!

**If type is IPV4:** Show IP Sources Selection (multi-select)

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

**CoCo Conversion Table (IPV4 only):**

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

**If type is HOST_PORT:** Prompt for hostnames directly

```
Enter hostname:port targets (comma-separated):
Example: api.github.com:443, storage.googleapis.com:443
```

**CoCo Conversion:** → `--values "<comma-separated-hosts>"`

**If type is AWSVPCEID:** Prompt for VPC endpoint IDs

```
Enter AWS VPC Endpoint IDs (comma-separated):
Example: vpce-1234567890abcdef0
```

**CoCo Conversion:** → `--values "<comma-separated-vpce-ids>"`

**⚠️ STOP**: Wait for user input on ALL values.

**After user provides input, update .env:**

- `NW_RULE_NAME=<confirmed_value>`
- `NW_RULE_DB=<confirmed_value>` (may equal SNOW_UTILS_DB)
- `NW_RULE_SCHEMA=<confirmed_value>`

### Step 3a: Check for Existing Network Rule

**Check if network rule already exists (use exact name, never wildcards):**

```bash
# Use DESC for exact name lookup - avoids privilege issues with other resources
set -a && source .env && set +a && snow sql -q "DESC NETWORK RULE <NW_RULE_DB>.<NW_RULE_SCHEMA>.<NW_RULE_NAME>" --format json
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
  rule delete --name <NW_RULE_NAME> --db <NW_RULE_DB> --yes
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
-- Uses admin_role from manifest (defaults to SECURITYADMIN)
USE ROLE <ADMIN_ROLE>;
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

**Execute (use --output json to skip CLI confirmation - CoCo handles it):**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule create --name <NW_RULE_NAME> --db <NW_RULE_DB> \
  [--allow-local] [--allow-gh] [--allow-google] [--values <CIDRs>] \
  [--policy <POLICY_NAME>] --output json
```

**On success:**

- Show created resources
- Update manifest (see Step 7)

**On failure:** Present error and remediation steps.

### Step 6: Verify

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py \
  rule list --db <NW_RULE_DB>
```

### Step 7: Write Success Summary and Manifest

> **Purpose:** The manifest enables replay, audit, and cleanup operations.

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
<!-- START -- snow-utils-networks:{NW_RULE_NAME} -->
## Network Resources: {COMMENT_PREFIX}

**Created:** {TIMESTAMP}
**Rule Name:** {NW_RULE_NAME}
**Database:** {NW_RULE_DB}
**Status:** IN_PROGRESS

### Resources (creation order)

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Network Rule | {NW_RULE_NAME} | {NW_RULE_DB}.{NW_RULE_SCHEMA} | DONE |
| 2 | Network Policy | {NW_RULE_NAME}_POLICY | Account | PENDING |

### IP Sources

| Source | Included |
|--------|----------|
| Local IP | {LOCAL_IP} |
| GitHub Actions | {yes/no} |
| Google Cloud | {yes/no} |
| Custom CIDRs | {list or none} |
<!-- END -- snow-utils-networks:{NW_RULE_NAME} -->
```

**After all resources created, update Status to COMPLETE and add cleanup:**

```markdown
<!-- START -- snow-utils-networks:{NW_RULE_NAME} -->
## Network Resources: {COMMENT_PREFIX}

**Created:** {TIMESTAMP}
**Rule Name:** {NW_RULE_NAME}
**Database:** {NW_RULE_DB}
**Status:** COMPLETE

### Resources (creation order)

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Network Rule | {NW_RULE_NAME} | {NW_RULE_DB}.{NW_RULE_SCHEMA} | DONE |
| 2 | Network Policy | {NW_RULE_NAME}_POLICY | Account | DONE |

### IP Sources

| Source | Included |
|--------|----------|
| Local IP | {LOCAL_IP} |
| GitHub Actions | {yes/no} |
| Google Cloud | {yes/no} |
| Custom CIDRs | {list or none} |

### Cleanup Instructions

> **🚨 CRITICAL: ALWAYS USE CLI COMMAND FOR CLEANUP**
>
> The CLI command handles dependency order and detach/reattach for rules attached to policies.
> **NEVER run raw SQL for cleanup** - use the script command below.

#### CLI Cleanup (REQUIRED)

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network.py rule delete --name {NW_RULE_NAME} --db {NW_RULE_DB} --yes
```

#### SQL Reference (FALLBACK ONLY - if CLI unavailable)

<details>
<summary>Manual SQL cleanup (dependency order)</summary>

```sql
USE ROLE {ADMIN_ROLE};
-- 1. Drop network policy first (depends on rule)
DROP NETWORK POLICY IF EXISTS {NW_RULE_NAME}_POLICY;
-- 2. Drop network rule
DROP NETWORK RULE IF EXISTS {NW_RULE_DB}.{NW_RULE_SCHEMA}.{NW_RULE_NAME};
```

</details>
<!-- END -- snow-utils-networks:{NW_RULE_NAME} -->
```

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
   - If yes, ask for NW_RULE_NAME and NW_RULE_DB values

3. **If manifest EXISTS:**
   - Read the `<!-- START -- snow-utils-networks:{NW_RULE_NAME} -->` section
   - Find the **"CLI Cleanup (REQUIRED)"** section in manifest
   - **Execute the command exactly as written in the manifest**

4. **Before executing, show user:**

   ```
   🗑️  Cleanup from manifest:
   
   Will remove resources:
     Network Rule:   {NW_RULE_NAME}
     Network Policy: {NW_RULE_NAME}_POLICY
   
   Using command from manifest:
   
   <CLI command from manifest>
   
   Proceed? [yes/no]
   ```

5. **On confirmation:** Execute the CLI command from manifest

6. **After cleanup success, update manifest status to REMOVED:**

   Change `**Status:** COMPLETE` to `**Status:** REMOVED` in the section.

   **DO NOT delete the section** - it's needed for replay flow.

> **Why manifest-driven?** The manifest captures exact resource names created during setup.
> Using CLI ensures proper dependency order, syntax, and error handling.

#### Replay Flow (Single Confirmation)

**Trigger phrases:** "replay network", "replay network manifest", "recreate network", "replay from manifest"

> **📍 Manifest Location:** `.snow-utils/snow-utils-manifest.md` (in current working directory)

**IMPORTANT:** This is the **snow-utils-networks** skill. Only replay sections marked `<!-- START -- snow-utils-networks -->`. If manifest contains other skills (Volumes, PAT), ignore them - use the appropriate skill for those.

**If user asks to replay/recreate from manifest:**

1. **Read manifest from current project directory:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md
   ```

2. **Find section** `<!-- START -- snow-utils-networks:{NW_RULE_NAME} -->`
   - If section NOT found: "No network resources in manifest. Nothing to replay for networks."
   - If section found: Continue to step 3

3. **Check Status:**

| Status | Action |
|--------|--------|
| `REMOVED` | Proceed with creation (resources don't exist) |
| `COMPLETE` | Warn: "Resources already exist. Run 'remove' first or choose 'recreate'" |
| `IN_PROGRESS` | Use Resume Flow instead (partial creation) |

1. **Display info summary with single confirmation:**

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

1. **On "yes":** Execute all creation steps without individual confirmations
2. **Update manifest** status back to COMPLETE as each resource is created

#### Resume Flow (Partial Creation Recovery)

**If manifest shows Status: IN_PROGRESS:**

1. **Read which resources have status `DONE`** (already created)
2. **Display resume info:**

```

ℹ️  Resuming from partial creation:

  ✓ Network Rule:   CREATED

- Network Policy: PENDING

Continue from Network Policy creation? [yes/no]

```

1. **On "yes":** Continue from first `PENDING` resource
2. **Update manifest** as each remaining resource is created

**Display success summary to user:**

```

Network Setup Complete!

Resources Created:
  Network Rule:   {NW_RULE_DB}.{NW_RULE_SCHEMA}.{NW_RULE_NAME}
  Network Policy: {NW_RULE_NAME}_POLICY
  CIDRs:          {count} IP ranges

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
- `--mode, -m`: Rule mode (default: INGRESS)
  - `INGRESS` - Control who can connect TO Snowflake
  - `EGRESS` - Control what Snowflake can connect TO
  - `INTERNAL_STAGE` - Internal stage access rules
  - `POSTGRES_INGRESS` - PostgreSQL interface incoming
  - `POSTGRES_EGRESS` - PostgreSQL interface outbound
- `--type, -t`: Rule type (default depends on mode)
  - `IPV4` - IP addresses/CIDRs (default for INGRESS modes)
  - `HOST_PORT` - hostname:port targets (default for EGRESS modes)
  - `AWSVPCEID` - AWS VPC Endpoint IDs
- `--values`: Comma-separated values (CIDRs, hosts, or VPC IDs depending on type)
- `--allow-local`: Include auto-detected local IP **(IPV4 type only)**
- `--allow-gh, -G`: Include GitHub Actions IPs **(IPV4 type only)**
- `--allow-google, -g`: Include Google IPs **(IPV4 type only)**
- `--policy, -p`: Also create network policy
- `--dry-run`: Preview SQL without executing

**⚠️ Mode-Type Constraints:**

| Mode | Valid Types |
|------|-------------|
| INGRESS, INTERNAL_STAGE, POSTGRES_INGRESS | IPV4, AWSVPCEID |
| EGRESS, POSTGRES_EGRESS | HOST_PORT, IPV4 |

> IP source flags (`--allow-local`, `--allow-gh`, `--allow-google`) only work with `--type IPV4`

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

**Permission denied:** Ensure admin_role (from manifest, defaults to SECURITYADMIN) has CREATE NETWORK RULE and CREATE NETWORK POLICY privileges.

**Rule already exists:** Use Step 3.5 flow - choose "Update existing" to modify IPs or "Remove and recreate" for fresh start.

**Invalid CIDR:** Ensure CIDRs are in x.x.x.x/mask format (e.g., `192.168.1.0/24`, `10.0.0.0/8`).

**GitHub Actions IPs not working:** Only IPv4 ranges are included. GitHub provides IPv6 ranges too, but Snowflake `TYPE = IPV4` rules don't support them.

**Cannot find resources for cleanup:** Check `.snow-utils/snow-utils-manifest.md` for exact resource names. Use manifest-based cleanup instead of guessing names.

**Partial creation failed:** If manifest shows `Status: IN_PROGRESS`, use Resume flow to continue from where it stopped, or manually clean up created resources using manifest cleanup instructions.

**Policy depends on rule:** When cleaning up, drop network policy BEFORE dropping network rule (policy references the rule).

## Security Notes

- Network rules control IP-based access to Snowflake
- INGRESS rules restrict incoming connections
- Use specific CIDRs, not 0.0.0.0/0
- Review IP sources periodically - GitHub/Google ranges change over time
- Use `--allow-local` for development, restrict to known CIDRs for production
