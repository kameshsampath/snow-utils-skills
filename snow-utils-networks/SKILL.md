---
name: snow-utils-networks
description: "Create Snowflake network rules and policies for IP allowlisting. Use when: setting up network security, creating ingress/egress rules, allowlisting GitHub Actions, Google IPs, or custom CIDRs. Triggers: network rule, network policy, IP allowlist, CIDR, ingress, egress, GitHub Actions IPs, firewall, replay network, replay network manifest, recreate network, replay all manifests, replay all snow-utils, export manifest for sharing, setup from shared manifest, replay from shared manifest."
---

# Snowflake Network Rules & Policies

Creates and manages network rules and policies for IP-based access control in Snowflake.

## Workflow

**📋 PREREQUISITE:** None. This skill can be used standalone or alongside other snow-utils skills.

**📍 MANIFEST FILE:** `.snow-utils/snow-utils-manifest.md` (ALWAYS this exact path and filename - never search for other patterns like *.yaml or *.*)

> **⛔ DO NOT hand-edit manifests.** Manifests are machine-managed by Cortex Code. Manual edits can corrupt the format and break replay, cleanup, and export flows. Use skill commands to modify resources instead.

**⚠️ CONNECTION USAGE:** This skill uses the **user's Snowflake connection** (SNOWFLAKE_DEFAULT_CONNECTION_NAME) for all object creation. Uses admin_role from manifest (defaults to ACCOUNTADMIN) for privileged operations.

**🔄 IDEMPOTENCY NOTE:** Network rules use `CREATE OR REPLACE` (Snowflake does not support `IF NOT EXISTS` for network rules). Network policies use `CREATE IF NOT EXISTS` to preserve existing policies. Re-running create operations is safe for automation.

**🚫 FORBIDDEN ACTIONS - NEVER DO THESE:**

- NEVER run SQL queries to discover/find/check values (no SHOW ROLES, SHOW DATABASES, SHOW NETWORK RULES)
- NEVER auto-populate empty .env values by querying Snowflake
- NEVER use flags that bypass user interaction: `--yes`, `-y`, `--auto-setup`, `--auto-approve`, `--quiet`, `--force`, `--non-interactive`
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER skip SQL in dry-run output - always show BOTH summary AND full SQL
- **NEVER run raw SQL for cleanup** - ALWAYS use CLI commands (handles dependency order and detach/reattach)
- **NEVER offer to drop SNOW_UTILS_DB** - it is shared infrastructure; cleanup only drops resources *inside* it (network rules, schemas), never the database itself
- If .env values are empty, prompt user or run `check-setup` CLI

**✅ INTERACTIVE PRINCIPLE:** This skill is designed to be interactive. At every decision point, ASK the user and WAIT for their response before proceeding.

**⚠️ ENVIRONMENT REQUIREMENT:** Once SNOWFLAKE_DEFAULT_CONNECTION_NAME is set in .env, ALL commands must use it. CLI tools (snow-utils-networks) auto-load `.env` via `load_dotenv()`. For `snow sql` or other shell commands, use `set -a && source .env && set +a` before running.

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

## project_recipe
project_name: <PROJECT_NAME>

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

**If SNOW_UTILS_DB is empty**, run `check-setup` first:

```bash
uv run --project <SKILL_DIR> check-setup --suggest
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
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -A1 "## admin_role" | grep "snow-utils-networks:"
```

**If admin_role exists for snow-utils-networks:** Use it, continue to Step 2b (privilege verification).

**If admin_role NOT set for snow-utils-networks, check other skills:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -E "^snow-utils-(volumes|pat):" | head -1
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
snow-utils-networks: <USER_ROLE>
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

**Cortex Code Conversion:** Selected mode → `--mode <value>`

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

**Cortex Code Conversion:** Selected type → `--type <value>`

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

**Cortex Code Conversion Table (IPV4 only):**

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

**Cortex Code Conversion:** → `--values "<comma-separated-hosts>"`

**If type is AWSVPCEID:** Prompt for VPC endpoint IDs

```
Enter AWS VPC Endpoint IDs (comma-separated):
Example: vpce-1234567890abcdef0
```

**Cortex Code Conversion:** → `--values "<comma-separated-vpce-ids>"`

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
| Update existing | Use `snow-utils-networks rule update` - modifies IPs, keeps policy intact |
| Remove and recreate | Use `snow-utils-networks rule delete` then `rule create` - fresh start |
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
uv run --project <SKILL_DIR> snow-utils-networks \
  rule update --name <NW_RULE_NAME> --db <NW_RULE_DB> \
  [--allow-local] [--allow-gh] [--allow-google] [--values <CIDRs>]
```

Then skip to Step 6 (Verify).

**If user chooses "Remove and recreate":**

```bash
uv run --project <SKILL_DIR> snow-utils-networks \
  rule delete --name <NW_RULE_NAME> --db <NW_RULE_DB> --yes
```

Then continue to Step 4.

**If no rule exists:** Continue to Step 4.

**Execute:**

```bash
uv run --project <SKILL_DIR> snow-utils-networks \
  rule create --name <NW_RULE_NAME> --db <NW_RULE_DB> \
  [--allow-local] [--allow-gh] [--allow-google] [--values <CIDRs>] \
  [--policy <POLICY_NAME>] --dry-run
```

**🔴 CRITICAL: Run the CLI dry-run, capture its output, and present it IN YOUR RESPONSE as formatted text.**

> Terminal output gets collapsed/truncated by the UI. The user cannot see it.
> You MUST copy the dry-run output into your chat response so the user can read it.

**After the command completes, you MUST:**

1. Read the full terminal output from the command
2. Copy-paste the ENTIRE output into your response using **language-tagged** markdown code blocks
3. The output includes both a resource summary AND full SQL (CREATE NETWORK RULE, CREATE NETWORK POLICY)

**Formatting rules:**

- Use ` ```text ` for the resource summary section
- Use ` ```sql ` for the SQL statements section
- Split the output into labeled sections for readability

**❌ WRONG:** Just running the command and letting the terminal output speak for itself (it gets truncated).
**❌ WRONG:** Constructing your own summary box or table instead of showing CLI output.
**❌ WRONG:** Saying "see the output above" -- the user CANNOT see collapsed terminal output.
**❌ WRONG:** Pasting everything into one bare ` ``` ` block without language tags.
**✅ RIGHT:** Pasting the CLI output with proper formatting like this:

````
Here is the dry-run preview:

**Resource Summary:**

```text
==================================================
Snowflake Network Manager
  [DRY RUN]
==================================================
Rule Name: BOBS_HIRC_DUCKDB_DEMO_RUNNER_NETWORK_RULE
Database:  BOBS_SNOW_UTILS
Mode:      INGRESS
Type:      IPV4
CIDRs:     106.222.203.139/32, 0.0.0.0/0 (GitHub Actions)
...
```

**SQL that would be executed:**

```sql
-- Step 1: Create network rule
USE ROLE ACCOUNTADMIN;
CREATE OR REPLACE NETWORK RULE BOBS_SNOW_UTILS.PUBLIC.BOBS_..._NETWORK_RULE
  MODE = INGRESS TYPE = IPV4
  VALUE_LIST = ('106.222.203.139/32', '0.0.0.0/0');

-- Step 2: Create network policy
CREATE NETWORK POLICY IF NOT EXISTS BOBS_..._NETWORK_POLICY
  ALLOWED_NETWORK_RULE_LIST = ('BOBS_SNOW_UTILS.PUBLIC.BOBS_..._NETWORK_RULE');
```

Proceed with creating these resources? [yes/no]
````

**COMMENT Pattern:** `{CONTEXT} {resource_type} - managed by snow-utils-networks`

**Context Inference:**

- Derived from NW_RULE_NAME by stripping suffixes: `_NETWORK_RULE`, `_RULE`, `_RUNNER`
- Example: `MYAPP_RUNNER_NETWORK_RULE` → `MYAPP`
- Can be overridden via root CLI option: `snow-utils-networks --comment "MY_PROJECT" rule create ...`

> 🔄 **On pause/resume:** Re-run `--dry-run` and paste the complete output again before asking for confirmation.

**⚠️ STOP**: Wait for explicit user approval ("yes", "ok", "proceed") before creating resources.

### Step 5: Create Resources

**Execute (use --output json to skip CLI confirmation - Cortex Code handles it):**

```bash
uv run --project <SKILL_DIR> snow-utils-networks \
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
uv run --project <SKILL_DIR> snow-utils-networks \
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
Cortex Code can use this manifest to replay creation or cleanup resources.

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
uv run --project <SKILL_DIR> snow-utils-networks rule delete --name {NW_RULE_NAME} --db {NW_RULE_DB} --yes
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

**Setup from shared manifest:** See hirc-duckdb-demo SKILL.md for the full "setup from shared manifest" flow.

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
> **🔴 CRITICAL:** Even in replay flow, user MUST see the full SQL preview before confirmation. NEVER skip dry-run output.

**IMPORTANT:** This is the **snow-utils-networks** skill. Only replay sections marked `<!-- START -- snow-utils-networks -->`. If manifest contains other skills (Volumes, PAT), ignore them - use the appropriate skill for those.

**If user asks to replay/recreate from manifest:**

1. **Detect manifest(s) in current directory:**

   ```bash
   WORKING_MANIFEST=""
   SHARED_MANIFEST=""
   SHARED_MANIFEST_FILE=""

   [ -f .snow-utils/snow-utils-manifest.md ] && WORKING_MANIFEST="EXISTS" && \
     WORKING_STATUS=$(grep "^Status:" .snow-utils/snow-utils-manifest.md | head -1 | awk '{print $2}') && \
     echo "Working manifest: Status=${WORKING_STATUS}"

   for f in *-manifest.md; do
     [ -f "$f" ] && grep -q "## shared_info\|COCO_INSTRUCTION" "$f" 2>/dev/null && \
       SHARED_MANIFEST="EXISTS" && SHARED_MANIFEST_FILE="$f" && echo "Shared manifest: $f"
   done
   ```

   **If BOTH exist, ask user:**

   ```
   ⚠️ Found two manifests:
     1. Working manifest: .snow-utils/snow-utils-manifest.md (Status: <WORKING_STATUS>)
     2. Shared manifest: <SHARED_MANIFEST_FILE>

   Which should we use for networks replay?
     A. Resume working manifest
     B. Start fresh from shared manifest (adapt values for your account)
     C. Cancel
   ```

   **⚠️ STOP**: Wait for user choice.

   | Choice | Action |
   |--------|--------|
   | **A** | Use working manifest → step 2 |
   | **B** | Backup working to `.bak`, copy shared to `.snow-utils/snow-utils-manifest.md` → step 1b |
   | **C** | Stop. |

   **If ONLY shared manifest:** Copy to `.snow-utils/snow-utils-manifest.md` → step 1b.
   **If ONLY working manifest:** Go to step 2.

1b. **Shared manifest adapt-check (ALWAYS run for shared manifests):**

   ```bash
   IS_SHARED=$(grep -c "## shared_info\|COCO_INSTRUCTION" .snow-utils/snow-utils-manifest.md 2>/dev/null)
   if [ "$IS_SHARED" -gt 0 ]; then
     ADAPT_COUNT=$(grep -c "# ADAPT:" .snow-utils/snow-utils-manifest.md 2>/dev/null)
     echo "Shared manifest detected. ADAPT markers: ${ADAPT_COUNT}"
   fi
   ```

   **If `ADAPT_COUNT` > 0:** Extract `shared_by` from `## shared_info`, get current user's `SNOWFLAKE_USER`, show adaptation screen for network values (NW_RULE_NAME, NW_RULE_DB). Three options: Accept adapted / Edit specific / Keep originals. Apply to manifest.

   **If `ADAPT_COUNT` = 0:** No markers, proceed with values as-is.

2. **Read manifest and find section** `<!-- START -- snow-utils-networks:{NW_RULE_NAME} -->`
   - If section NOT found: "No network resources in manifest. Nothing to replay for networks."
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

   d. **Infer from manifest `snow-utils-networks` section:**

      ```bash
      NW_RULE_NAME=$(grep -A30 "<!-- START -- snow-utils-networks" .snow-utils/snow-utils-manifest.md | grep "^\*\*Rule Name:\*\*" | head -1 | sed 's/\*\*Rule Name:\*\* //')
      NW_RULE_DB=$(grep -A30 "<!-- START -- snow-utils-networks" .snow-utils/snow-utils-manifest.md | grep "^\*\*Database:\*\*" | head -1 | sed 's/\*\*Database:\*\* //')
      ```

   e. Also check for SNOW_UTILS_DB from other sections (may be needed):

      ```bash
      SNOW_UTILS_DB=$(grep -A30 "<!-- START -- snow-utils-pat" .snow-utils/snow-utils-manifest.md | grep "^\*\*Database:\*\*" | head -1 | sed 's/\*\*Database:\*\* //')
      ```

   f. **Validate extracted values** (grep validation):

      ```bash
      for var in NW_RULE_NAME NW_RULE_DB; do
        val=$(eval echo \$$var)
        [ -z "$val" ] && echo "WARNING: Could not extract ${var} from manifest"
      done
      ```

      If any value is empty, ask user to enter manually or abort.

   g. **Shared manifest adapt-check (ALWAYS run for shared manifests):**

      If adaptation was already done in step 1b, skip this step.

      ```bash
      IS_SHARED=$(grep -c "## shared_info\|COCO_INSTRUCTION" .snow-utils/snow-utils-manifest.md 2>/dev/null)
      [ "$IS_SHARED" -gt 0 ] && ADAPT_COUNT=$(grep -c "# ADAPT:" .snow-utils/snow-utils-manifest.md 2>/dev/null)
      ```

      If shared AND `ADAPT_COUNT` > 0: show adaptation screen for NW_RULE_NAME, NW_RULE_DB (see step 1b).
      If shared AND no markers: proceed with values as-is.
      If not shared: skip.

   h. Write values (adapted or original) to `.env` (only if not already set):

      ```bash
      for var in NW_RULE_NAME NW_RULE_DB SNOW_UTILS_DB; do
        val=$(eval echo \$$var)
        [ -n "$val" ] && (grep -q "^${var}=" .env && \
          sed -i '' "s/^${var}=.*/${var}=${val}/" .env || \
          echo "${var}=${val}" >> .env)
      done
      ```

   **If .env exists and has all values:** Skip to step 4.

4. **Check Status:**

| Status | Action |
|--------|--------|
| `REMOVED` | Proceed to step 5 (resources don't exist) |
| `COMPLETE` | **Collision detected** — show collision strategy prompt |
| `IN_PROGRESS` | Use Resume Flow instead (partial creation) |

   **If Status is `COMPLETE` — Collision Strategy:**

   ```
   ⚠️ Network resources already exist:

     Resource                    Status
     ─────────────────────────────────────
     Network Rule:   {NW_RULE_NAME}            EXISTS
     Network Policy: {NW_RULE_NAME}_POLICY     EXISTS

   Choose a strategy:
   1. Use existing → skip creation, continue to next skill
   2. Replace → run 'remove' then recreate (DESTRUCTIVE)
   3. Rename → prompt for new rule name, create alongside existing
   4. Cancel → stop replay
   ```

   **⚠️ STOP**: Wait for user choice.

   | Choice | Action |
   |--------|--------|
   | **Use existing** | Skip network creation entirely. |
   | **Replace** | Confirm with "Type 'yes, destroy' to confirm". Run Remove Flow, then proceed to step 5. |
   | **Rename** | Ask for new `NW_RULE_NAME`. Derive new policy name. Update `.env` and proceed to step 5. |
   | **Cancel** | Stop replay. |

5. **Run dry-run to show full SQL preview:**

   ```bash
   uv run --project <SKILL_DIR> snow-utils-networks \
     rule create --name {NW_RULE_NAME} --db {NW_RULE_DB} \
     [--allow-local] [--allow-gh] [--allow-google] [--values <CIDRs from manifest>] \
     [--policy {NW_RULE_NAME}_POLICY] --dry-run
   ```

   **🔴 CRITICAL:** Terminal output gets truncated by the UI. After running the command, read the terminal output and paste the ENTIRE result using language-tagged code blocks: ` ```text ` for summary, ` ```sql ` for SQL. See Step 4 formatting example above.

   Then ask:

   ```
   Proceed with creation? [yes/no]
   ```

   **⚠️ STOP**: Wait for user confirmation.

6. **On "yes":** Execute all creation steps without individual confirmations

7. **Verify (MANDATORY -- do NOT skip, even in replay):**

   ```bash
   uv run --project <SKILL_DIR> snow-utils-networks \
     rule list --db {NW_RULE_DB}
   ```

   > Confirm the network rule appears in the list. If verify fails, stop and present error.

8. **Update manifest** status back to COMPLETE as each resource is created

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

### check-setup (from snow-utils-common, via snow-utils dependency)

**Description:** Pre-flight check for snow-utils infrastructure (database + schemas).

**Usage:**

```bash
uv run --project <SKILL_DIR> check-setup
```

**Options:**

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--database` | `-d` | No | from `SNOW_UTILS_DB` env or `{USER}_SNOW_UTILS` | Database name to check/create |
| `--run-setup` | - | No | false | Run setup SQL if infrastructure missing |
| `--suggest` | - | No | false | Output suggested defaults as JSON |

### snow-utils-networks CLI

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

**🔴 COMMAND NAMES (exact -- do NOT substitute):**

- `rule create` -- NOT "rule setup", "rule make", "rule add"
- `rule delete` -- NOT "rule remove", "rule destroy", "rule drop"
- `rule update` -- NOT "rule modify", "rule change", "rule edit"
- `rule list` -- NOT "rule show", "rule get", "rule describe"
- `policy create` -- NOT "policy setup", "policy make"
- `policy delete` -- NOT "policy remove", "policy destroy"
- `policy assign` -- NOT "policy attach", "policy apply", "policy set"

**Global Options (BEFORE subcommand):**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--verbose` | `-v` | false | Enable verbose output |
| `--debug` | `-d` | false | Enable debug output |

### `rule create`

| Option | Short | Env Var | Required | Default | Description |
|--------|-------|---------|----------|---------|-------------|
| `--name` | `-n` | `NW_RULE_NAME` | Yes | - | Network rule name |
| `--db` | - | `NW_RULE_DB` | Yes | - | Database for rule |
| `--schema` | `-s` | `NW_RULE_SCHEMA` | No | `NETWORKS` | Schema for rule |
| `--mode` | `-m` | - | No | `INGRESS` | Rule mode (see constraints below) |
| `--type` | `-t` | - | No | auto | Rule type (see constraints below) |
| `--values` | - | - | No | - | Comma-separated values (CIDRs, hosts, VPC IDs) |
| `--allow-local/--no-local` | - | - | No | true | Include auto-detected local IP (IPV4 only) |
| `--allow-gh` | `-G` | - | No | false | Include GitHub Actions IPs (IPV4 only) |
| `--allow-google` | `-g` | - | No | false | Include Google IPs (IPV4 only) |
| `--dry-run` | - | - | No | false | Preview SQL without executing |
| `--force` | `-f` | - | No | false | Overwrite existing rule (CREATE OR REPLACE) |
| `--policy` | `-p` | - | No | - | Also create/alter a network policy with this name |
| `--policy-mode` | - | - | No | `create` | `create` or `alter` the policy |
| `--output` | `-o` | - | No | `text` | Output format: `text` or `json` |

### `rule update`

| Option | Short | Env Var | Required | Default | Description |
|--------|-------|---------|----------|---------|-------------|
| `--name` | `-n` | `NW_RULE_NAME` | Yes | - | Network rule name |
| `--db` | - | `NW_RULE_DB` | Yes | - | Database name |
| `--schema` | `-s` | `NW_RULE_SCHEMA` | No | `NETWORKS` | Schema name |
| `--values` | - | - | No | - | Comma-separated values to replace existing |
| `--allow-local/--no-local` | - | - | No | true | Include auto-detected local IP (IPV4 only) |
| `--allow-gh` | `-G` | - | No | false | Include GitHub Actions IPs (IPV4 only) |
| `--allow-google` | `-g` | - | No | false | Include Google IPs (IPV4 only) |
| `--dry-run` | - | - | No | false | Preview SQL without executing |

### `rule delete`

| Option | Short | Env Var | Required | Default | Description |
|--------|-------|---------|----------|---------|-------------|
| `--name` | `-n` | `NW_RULE_NAME` | Yes | - | Network rule name |
| `--db` | - | `NW_RULE_DB` | Yes | - | Database name |
| `--schema` | `-s` | `NW_RULE_SCHEMA` | No | `NETWORKS` | Schema name |
| `--yes` | - | - | No | - | Auto-confirm deletion |

### `rule list`

| Option | Short | Env Var | Required | Default | Description |
|--------|-------|---------|----------|---------|-------------|
| `--db` | - | `NW_RULE_DB` | Yes | - | Database name |
| `--schema` | `-s` | `NW_RULE_SCHEMA` | No | `NETWORKS` | Schema name |
| `--admin-role` | `-a` | - | No | `accountadmin` | Role for listing |

### `policy create`

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--name` | `-n` | Yes | - | Network policy name |
| `--rules` | `-r` | Yes | - | Comma-separated FQN of allowed network rules |
| `--dry-run` | - | No | false | Preview SQL without executing |
| `--force` | `-f` | No | false | Overwrite existing policy (CREATE OR REPLACE) |
| `--output` | `-o` | No | `text` | Output format: `text` or `json` |

### `policy alter`

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--name` | `-n` | Yes | - | Network policy name |
| `--rules` | `-r` | Yes | - | Comma-separated FQN of allowed network rules |
| `--dry-run` | - | No | false | Preview SQL without executing |
| `--output` | `-o` | No | `text` | Output format: `text` or `json` |

### `policy delete`

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--name` | `-n` | Yes | - | Network policy name |
| `--user` | `-u` | No | - | Also unset policy from this user first |
| `--admin-role` | `-a` | No | `accountadmin` | Role for deleting |
| `--yes` | - | No | - | Auto-confirm deletion |

### `policy list`

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--admin-role` | `-a` | No | `accountadmin` | Role for listing |

### `policy assign`

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--name` | `-n` | Yes | - | Network policy name |
| `--user` | `-u` | Yes | - | User to assign policy to |
| `--admin-role` | `-a` | No | `accountadmin` | Role for assigning |

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

1. ✋ Step 1: If connection checks fail
2. ✋ Step 2: If infra check needed (prompts user)
3. ✋ Step 3: After gathering requirements
4. ✋ Step 4: After dry-run preview (get approval)

## Output

- Network rule (IPV4, HOST_PORT, or AWSVPCEID)
- Network policy (optional, linked to rule)
- Updated .env with all values

## SQL Reference (Snowflake Documentation)

> These links help Cortex Code infer correct SQL syntax when previewing or troubleshooting.

| Statement | Documentation |
|-----------|---------------|
| `CREATE NETWORK RULE` | https://docs.snowflake.com/en/sql-reference/sql/create-network-rule |
| `ALTER NETWORK RULE` | https://docs.snowflake.com/en/sql-reference/sql/alter-network-rule |
| `DROP NETWORK RULE` | https://docs.snowflake.com/en/sql-reference/sql/drop-network-rule |
| `SHOW NETWORK RULES` | https://docs.snowflake.com/en/sql-reference/sql/show-network-rules |
| `CREATE NETWORK POLICY` | https://docs.snowflake.com/en/sql-reference/sql/create-network-policy |
| `ALTER NETWORK POLICY` | https://docs.snowflake.com/en/sql-reference/sql/alter-network-policy |
| `DROP NETWORK POLICY` | https://docs.snowflake.com/en/sql-reference/sql/drop-network-policy |
| `SHOW NETWORK POLICIES` | https://docs.snowflake.com/en/sql-reference/sql/show-network-policies |
| `ALTER USER ... SET NETWORK POLICY` | https://docs.snowflake.com/en/sql-reference/sql/alter-user |
| `ALTER USER ... UNSET NETWORK_POLICY` | https://docs.snowflake.com/en/sql-reference/sql/alter-user |
| `GRANT ... ON SCHEMA` | https://docs.snowflake.com/en/sql-reference/sql/grant-privilege |

## Troubleshooting

**Infrastructure not set up:** Run `uv run --project <SKILL_DIR> check-setup --run-setup` - it will check and offer to create the database and schemas.

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
