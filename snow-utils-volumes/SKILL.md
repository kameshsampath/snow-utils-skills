---
name: snow-utils-volumes
description: "Create Snowflake external volumes with S3 storage. Use when: setting up external storage, creating external volume, configuring S3 for Snowflake, Iceberg tables, unloading data. Triggers: external volume, s3 snowflake, iceberg storage, data lake storage, replay volumes, replay volume manifest, recreate external volume, replay all manifests, replay all snow-utils, export manifest for sharing, setup from shared manifest, replay from shared manifest."
---

# External Volume Setup (AWS S3)

Creates S3 bucket, IAM role/policy, and Snowflake external volume for cloud storage access.

**Use cases:** Iceberg tables, data lake access, COPY INTO unload, external stages.

## Workflow

**⚠️ CONNECTION USAGE:** This skill uses the **user's Snowflake connection** (SNOWFLAKE_DEFAULT_CONNECTION_NAME) for all operations. External volumes are account-level objects requiring elevated privileges (default: ACCOUNTADMIN).

**📋 NO PREREQUISITE:** This skill does NOT require snow-utils-pat. It operates independently using the user's connection.

> **📋 MANIFEST AS SOURCE OF TRUTH**
>
> **📍 Location:** `.snow-utils/snow-utils-manifest.md` (ALWAYS this exact path - never search for *.yaml or other patterns)
>
> **⛔ DO NOT hand-edit manifests.** Manifests are machine-managed by Cortex Code. Manual edits can corrupt the format and break replay, cleanup, and export flows. Use skill commands to modify resources instead.
>
> **🔒 Security:** Secured like `.ssh` (chmod 700 directory, chmod 600 files)
>
> **Skill-Scoped Admin Roles:**
>
> - Volumes default: `ACCOUNTADMIN` (CREATE EXTERNAL VOLUME privilege)
> - Cross-skill awareness: Can inherit from PAT/Networks if set
> - **Apps should NOT use admin_role** - use SA_ROLE instead

**🚫 FORBIDDEN ACTIONS - NEVER DO THESE:**

- NEVER run SQL queries to discover/find/check values (no SHOW ROLES, SHOW DATABASES, SHOW EXTERNAL VOLUMES)
- NEVER auto-populate empty .env values by querying Snowflake
- NEVER use flags that bypass user interaction (except documented `--yes` for Cortex Code automation)
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER skip SQL/JSON in dry-run output - always show BOTH summary AND full SQL/JSON
- NEVER hardcode admin roles - get admin_role from manifest
- NEVER put admin_role in app .env - apps should use SA_ROLE
- NEVER skip manifest - always update manifest IMMEDIATELY after user input
- NEVER leave .snow-utils unsecured - always chmod 700/600
- NEVER delete .snow-utils directory or manifest file - preserve for audit/cleanup/replay
- **NEVER offer to drop SNOW_UTILS_DB** - it is shared infrastructure; cleanup only drops resources *inside* it, never the database itself
- If .env values are empty, prompt user or run `check-setup` CLI

**✅ INTERACTIVE PRINCIPLE:** This skill is designed to be interactive. At every decision point, ASK the user and WAIT for their response before proceeding.

**⚠️ ENVIRONMENT REQUIREMENT:** Once SNOWFLAKE_DEFAULT_CONNECTION_NAME is set in .env, ALL commands must use it. CLI tools (snow-utils-volumes) auto-load `.env` via `load_dotenv()`. For `snow sql` or other shell commands, use `set -a && source .env && set +a` before running.

### Step 0: Check Prerequisites (Manifest-Cached)

**First, check manifest for cached prereqs:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -A2 "## prereqs"
```

**If `tools_verified:` exists with a date:** Skip tool checks, continue to Step 1.

**Otherwise, check required tools:**

```bash
for t in uv snow aws; do command -v $t &>/dev/null && echo "$t: OK" || echo "$t: MISSING"; done
```

**If any tool is MISSING, stop and provide installation instructions:**

| Tool | Install Command |
|------|-----------------|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `snow` | `pip install snowflake-cli` or `uv tool install snowflake-cli` |
| `aws` | `brew install awscli` or see [AWS CLI Install](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |

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
grep -q "volumes:" .snow-utils/snow-utils-manifest.md || \
  echo "  volumes: https://github.com/kameshsampath/snow-utils-skills/snow-utils-volumes" >> .snow-utils/snow-utils-manifest.md
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
   - Keys to check: SNOWFLAKE_DEFAULT_CONNECTION_NAME, SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT_URL, EXTERNAL_VOLUME_NAME, BUCKET, AWS_REGION, EXTVOLUME_PREFIX

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

1. **Verify AWS credentials:**

   ```bash
   aws sts get-caller-identity
   ```

   Show output to confirm correct AWS account.

**If any check fails:** Stop and help user resolve.

### Step 2: Check Infrastructure (Conditional)

**First, check memory for cached infra status:**

If memory has `infra_ready: true` with `sa_role` and `snow_utils_db` values:

- Use cached values
- Skip infra check, go to Step 3

**Otherwise:**

**IMPORTANT:** Source .env with export to use the configured connection:

```bash
set -a && source .env && set +a
```

Verify the user connection works:

```bash
set -a && source .env && set +a && snow connection test -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} --format json
```

**If connection test succeeds:**

**Update memory:**

```
Update /memories/snow-utils-prereqs.md:
tools_checked: true
connection_verified: true
```

Continue to Step 2a.

### Step 2a: Admin Role from Manifest

**Purpose:** Skills require elevated privileges for account-level objects. Get admin_role from manifest.

**Ensure secured .snow-utils directory:**

```bash
mkdir -p .snow-utils && chmod 700 .snow-utils
```

**Check manifest for existing admin_role:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -A1 "## admin_role" | grep "snow-utils-volumes:"
```

**If admin_role exists for snow-utils-volumes:** Use it.

**If admin_role NOT set for snow-utils-volumes, check other skills:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -E "^snow-utils-(pat|networks):" | head -1
```

**If another skill has admin_role, ask user:**

```
Found admin_role from another skill:
  snow-utils-pat: USERADMIN
  
External volume creation requires ACCOUNTADMIN (CREATE EXTERNAL VOLUME privilege).

Options:
1. Use existing: USERADMIN (may need GRANT CREATE EXTERNAL VOLUME)
2. Use Snowflake default: ACCOUNTADMIN
3. Specify a different role
```

**If NO admin_role exists anywhere, prompt:**

```
External volume creation requires CREATE EXTERNAL VOLUME privilege.

Snowflake recommends: ACCOUNTADMIN (has this privilege by default)

Enter admin role for volumes [ACCOUNTADMIN]: 
```

**⚠️ STOP**: Wait for user input.

**IMMEDIATELY write to manifest (before ANY resource creation):**

```bash
# Secure the directory
chmod 700 .snow-utils

# Create/update manifest
cat >> .snow-utils/snow-utils-manifest.md << 'EOF'

## admin_role
snow-utils-volumes: <USER_ROLE>
EOF

# Secure the file
chmod 600 .snow-utils/snow-utils-manifest.md
```

**Update memory:**

```
Update /memories/snow-utils-prereqs.md:
volumes_admin_role: <USER_ROLE>
```

### Step 3: Check Existing External Volume

Read EXTERNAL_VOLUME_NAME from .env:

```bash
grep "^EXTERNAL_VOLUME_NAME=" .env | cut -d= -f2
```

**If EXTERNAL_VOLUME_NAME has a value**, check if it exists:

```bash
set -a && source .env && set +a && snow sql -q "SHOW EXTERNAL VOLUMES LIKE '${EXTERNAL_VOLUME_NAME}'" --format json
```

**If volume exists:** Ask user:

1. Use existing volume (skip to Step 7)
2. Delete and recreate
3. Create new volume with different name

**If EXTERNAL_VOLUME_NAME is empty or volume doesn't exist:** Continue to Step 4.

### Step 4: Gather Requirements

**Get context for defaults:**

```bash
# Get prefix from SNOWFLAKE_USER (lowercase)
grep "^SNOWFLAKE_USER=" .env | cut -d= -f2 | tr '[:upper:]' '[:lower:]'

# Get project name from current directory for bucket suggestion
basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr '_' '-'
```

**Step 4a: Ask about prefix FIRST:**

```
External Volume Configuration:

Detected prefix (from SNOWFLAKE_USER): <prefix_value>

> **Note:** By default, all AWS resources (S3 bucket, IAM role, IAM policy) are prefixed 
> with your Snowflake username to avoid naming conflicts in shared AWS accounts.

1. Prefix option:
   - Use detected prefix: <prefix_value>
   - Use custom prefix: (specify your own)
   - No prefix: (use raw bucket name)
```

**⚠️ STOP**: Wait for user to select prefix option.

**Step 4b: Ask for bucket name (show WITH prefix applied):**

If user selected prefix (detected or custom), show bucket input WITH preview:

```
Prefix selected: <prefix_value>
Suggested bucket (from project): <project_name>

2. Bucket name (base name) [default: <project_name>]: 

With your prefix, resources will be:
  S3 Bucket:        <prefix>-<project_name>
  IAM Role:         <prefix>-<project_name>-snowflake-role  
  External Volume:  <PREFIX>_<PROJECT_NAME>_EXTERNAL_VOLUME
```

If user selected no prefix:

```
No prefix selected (raw names)
Suggested bucket (from project): <project_name>

2. Bucket name [default: <project_name>]: 

Resources will be:
  S3 Bucket:        <project_name>
  IAM Role:         <project_name>-snowflake-role
  External Volume:  <PROJECT_NAME>_EXTERNAL_VOLUME
```

**⚠️ STOP**: Wait for user input. After bucket entered, update preview with actual bucket name.

**Step 4c: Ask remaining options:**

```
3. AWS region [default: us-west-2]:
4. Allow writes? [default: yes]:
```

**⚠️ STOP**: Wait for user input.

**After user provides all input, update .env:**

- `BUCKET=<user_bucket_name>`
- `AWS_REGION=<user_region>`
- `EXTVOLUME_PREFIX=<user_prefix or empty if no prefix>`
- `EXTERNAL_VOLUME_NAME=<PREFIX>_<BUCKET>_EXTERNAL_VOLUME` (or `<BUCKET>_EXTERNAL_VOLUME` if no prefix)

### Step 5: Preview (Dry Run)

**IMPORTANT:** The `--region` flag is a GLOBAL option (before `create`), not on `create`.

**Execute (with prefix):**

```bash
uv run --project <SKILL_DIR> snow-utils-volumes \
  --region ${AWS_REGION} \
  create --bucket ${BUCKET} --dry-run
```

**Execute (without prefix):**

```bash
uv run --project <SKILL_DIR> snow-utils-volumes \
  --region ${AWS_REGION} --no-prefix \
  create --bucket ${BUCKET} --dry-run
```

**🔴 CRITICAL: Run the CLI dry-run, capture its output, and present it IN YOUR RESPONSE as formatted text.**

> Terminal output gets collapsed/truncated by the UI. The user cannot see it.
> You MUST copy the dry-run output into your chat response so the user can read it.

**After the command completes, you MUST:**

1. Read the full terminal output from the command
2. Copy-paste the ENTIRE output into your response using **language-tagged** markdown code blocks
3. **Split the output into labeled sections** -- each with the appropriate language tag:
   - ` ```text ` for the resource summary (AWS + Snowflake)
   - ` ```json ` for the IAM policy JSON
   - ` ```json ` for the IAM trust policy JSON
   - ` ```sql ` for the CREATE EXTERNAL VOLUME statement

> **Note:** External volumes are account-level objects in Snowflake (no database/schema prefix).

The IAM policy and trust policy JSONs are **critical** -- the user needs to review the exact
permissions and trust relationships before approving resource creation.

**❌ WRONG:** Just running the command and letting the terminal output speak for itself (it gets truncated).
**❌ WRONG:** Constructing your own summary box or template instead of showing CLI output.
**❌ WRONG:** Saying "see the output above" -- the user CANNOT see collapsed terminal output.
**❌ WRONG:** Pasting only the SQL but omitting the IAM policy / trust policy JSON.
**❌ WRONG:** Pasting everything into one bare ` ``` ` block without language tags.
**✅ RIGHT:** Pasting the CLI output with proper formatting like this:

````
Here is the dry-run preview:

**Resource Summary:**

```text
==================================================
Snowflake External Volume Manager
  [DRY RUN]
==================================================
AWS Region:       us-west-2
S3 Bucket:        iceberg-data
IAM Role:         snowflake-iceberg-data-role
IAM Policy:       snowflake-iceberg-data-policy
External Volume:  ICEBERG_DATA_EXTERNAL_VOLUME
...
```

**IAM Policy (S3 access permissions):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket", ...],
      "Resource": ["arn:aws:s3:::iceberg-data", "arn:aws:s3:::iceberg-data/*"]
    }
  ]
}
```

**IAM Trust Policy (Snowflake cross-account trust):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam:::<snowflake_account_id>:root" },
      "Action": "sts:AssumeRole",
      "Condition": { "StringEquals": { "sts:ExternalId": "..." } }
    }
  ]
}
```

**Snowflake SQL:**

```sql
CREATE OR REPLACE EXTERNAL VOLUME ICEBERG_DATA_EXTERNAL_VOLUME
  STORAGE_LOCATIONS = (
    (
      NAME = 'iceberg-data-s3'
      STORAGE_BASE_URL = 's3://iceberg-data/'
      STORAGE_PROVIDER = 'S3'
      STORAGE_AWS_ROLE_ARN = 'arn:aws:iam:::<account>:role/snowflake-iceberg-data-role'
    )
  );
```

Proceed with creating these resources? [yes/no]
````

> 🔄 **On pause/resume:** Re-run `--dry-run` and paste the complete output again before asking for confirmation.

**⚠️ STOP**: Wait for explicit user approval ("yes", "ok", "proceed") before creating resources.

### Step 6: Create Resources

**Execute (with prefix):**

```bash
uv run --project <SKILL_DIR> snow-utils-volumes \
  --region ${AWS_REGION} \
  create --bucket ${BUCKET} --output json
```

**Execute (without prefix):**

```bash
uv run --project <SKILL_DIR> snow-utils-volumes \
  --region ${AWS_REGION} --no-prefix \
  create --bucket ${BUCKET} --output json
```

**On success:**

- Update .env with created volume name
- Continue to Step 7 (verify)
- Write cleanup manifest (see Step 8)

**Note:** External volumes have many applications:

- Iceberg tables (managed data lake)
- COPY INTO unload (data export)
- External stages (data import)
- Data sharing with other platforms

**On failure:** Rollback is automatic. Present error.

### Step 7: Verify

**⏳ Wait for IAM propagation before verifying:**

```
Waiting 15 seconds for IAM propagation...
```

```bash
sleep 15
```

**Execute:**

```bash
uv run --project <SKILL_DIR> snow-utils-volumes \
  verify --volume-name ${EXTERNAL_VOLUME_NAME}
```

**If verification fails with IAM error:** Wait another 15 seconds and retry (up to 3 attempts).

**Present** verification result and continue to Step 8 for summary.

### Step 8: Write Success Summary and Cleanup Manifest

**Manifest Location:** `.snow-utils/snow-utils-manifest.md`

**Create directory if needed:**

```bash
mkdir -p .snow-utils && chmod 700 .snow-utils
```

**If manifest doesn't exist, create with header:**

```markdown
# Snow-Utils Manifest

This manifest records all Snowflake resources created by snow-utils skills.

---
```

**Append skill section with START/END markers:**

```markdown
<!-- START -- snow-utils-volumes -->
## External Volume Resources: {COMMENT_PREFIX}

**Created:** {TIMESTAMP}
**Prefix:** {PREFIX}
**Bucket:** {BUCKET}
**Region:** {AWS_REGION}
**Status:** COMPLETE

### AWS Tags (applied to S3, IAM Role, IAM Policy)
| Tag Key | Value |
|---------|-------|
| managed-by | snow-utils-volumes |
| user | {PREFIX_UPPER} |
| project | {BUCKET_UPPER} |
| snowflake-volume | {PREFIX}_{BUCKET}_EXTERNAL_VOLUME |

### Resources
| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | S3 Bucket | {PREFIX}-{BUCKET} | AWS ({AWS_REGION}) | DONE |
| 2 | IAM Policy | {PREFIX}-{BUCKET}-snowflake-policy | AWS | DONE |
| 3 | IAM Role | {PREFIX}-{BUCKET}-snowflake-role | AWS | DONE |
| 4 | External Volume | {PREFIX}_{BUCKET}_EXTERNAL_VOLUME | Snowflake | DONE |

### Cleanup

Run this command to remove all resources:

```bash
uv run --project <SKILL_DIR> snow-utils-volumes \
  --region ${AWS_REGION} \
  delete --bucket ${BUCKET} --yes --output json
```

With S3 bucket deletion:

```bash
uv run --project <SKILL_DIR> snow-utils-volumes \
  --region ${AWS_REGION} \
  delete --bucket ${BUCKET} --delete-bucket --force --yes --output json
```
<!-- END -- snow-utils-volumes -->
```

**Secure manifest file:**

```bash
chmod 600 .snow-utils/snow-utils-manifest.md
```

**Display success summary to user:**

```
✅ External Volume Setup Complete!

Resources Created:
  S3 Bucket:        {PREFIX}-{BUCKET} ({AWS_REGION})
  IAM Role:         {PREFIX}-{BUCKET}-snowflake-role
  IAM Policy:       {PREFIX}-{BUCKET}-snowflake-policy
  External Volume:  {PREFIX}_{BUCKET}_EXTERNAL_VOLUME

AWS Tags Applied:
  managed-by:       snow-utils-volumes
  user:             {PREFIX}
  project:          {BUCKET}
  snowflake-volume: {VOLUME_NAME}

Verification:
  Status:           ✅ PASSED
  Storage Access:   Confirmed
  IAM Trust:        Valid

Applications:
  - Iceberg tables (managed data lake)
  - COPY INTO unload (data export)
  - External stages (data import)

Manifest: .snow-utils/snow-utils-manifest.md
```

**Example Iceberg Table DDL (one application):**

```sql
CREATE OR REPLACE ICEBERG TABLE my_table (
    id INT,
    name STRING,
    created_at TIMESTAMP
)
    CATALOG = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'HIRC_DUCKDB_DEMO_ICEBERG_EXTERNAL_VOLUME'
    BASE_LOCATION = 'my_table/';
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

### snow-utils-volumes CLI

**Description:** Creates and manages Snowflake external volumes with S3 backend.

**Global Options (BEFORE command):**

- `-r, --region`: AWS region (default: us-west-2, or AWS_REGION env var)
- `-p, --prefix`: Custom prefix for AWS resources
- `--no-prefix`: Disable username prefix
- `-c, --comment`: Comment for external volume (auto-generated if not provided)

**Commands:**

- `create`: Create S3 bucket, IAM role/policy, external volume
- `delete`: Remove all resources
- `verify`: Test external volume connectivity
- `describe`: Show external volume properties
- `update-trust`: Re-sync IAM trust policy

**🔴 COMMAND NAMES (exact -- do NOT substitute):**

- `create` -- NOT "setup", "make", "provision", "init"
- `delete` -- NOT "remove", "destroy", "cleanup", "drop"
- `verify` -- NOT "check", "test", "validate", "ping"
- `describe` -- NOT "show", "get", "info", "status"
- `update-trust` -- NOT "sync-trust", "refresh-trust"

**Global Options (BEFORE command):**

| Option | Short | Env Var | Default | Description |
|--------|-------|---------|---------|-------------|
| `--region` | `-r` | `AWS_REGION` | `us-west-2` | AWS region |
| `--prefix` | `-p` | `EXTVOLUME_PREFIX` | current username | Prefix for AWS resources |
| `--no-prefix` | - | - | false | Disable username prefix |
| `--verbose` | `-v` | - | false | Enable verbose output |
| `--debug` | - | - | false | Enable debug output (shows SQL) |
| `--comment` | `-c` | - | auto | Comment for external volume |

### `create`

| Option | Short | Env Var | Required | Default | Description |
|--------|-------|---------|----------|---------|-------------|
| `--bucket` | `-b` | `BUCKET` | Yes | - | S3 bucket base name (will be prefixed) |
| `--role-name` | - | - | No | `{prefix}-{bucket}-snowflake-role` | IAM role name |
| `--policy-name` | - | - | No | `{prefix}-{bucket}-snowflake-policy` | IAM policy name |
| `--volume-name` | - | `EXTERNAL_VOLUME_NAME` | No | `{PREFIX}_{BUCKET}_EXTERNAL_VOLUME` | Snowflake external volume name |
| `--storage-location-name` | - | - | No | `{prefix}-{bucket}-s3-{region}` | Storage location name |
| `--external-id` | - | - | No | auto-generated | External ID for trust relationship |
| `--no-writes` | - | - | No | false | Create read-only external volume |
| `--skip-verify` | - | - | No | false | Skip external volume verification |
| `--dry-run` | - | - | No | false | Preview what would be created |
| `--force` | `-f` | - | No | false | Overwrite existing volume (CREATE OR REPLACE) |
| `--output` | `-o` | - | No | `text` | Output format: `text` or `json` |

### `delete`

| Option | Short | Env Var | Required | Default | Description |
|--------|-------|---------|----------|---------|-------------|
| `--bucket` | `-b` | `BUCKET` | Yes | - | S3 bucket base name |
| `--role-name` | - | - | No | `{prefix}-{bucket}-snowflake-role` | IAM role name |
| `--policy-name` | - | - | No | `{prefix}-{bucket}-snowflake-policy` | IAM policy name |
| `--volume-name` | - | `EXTERNAL_VOLUME_NAME` | No | `{PREFIX}_{BUCKET}_EXTERNAL_VOLUME` | Snowflake volume name |
| `--delete-bucket` | - | - | No | false | Also delete the S3 bucket |
| `--force` | - | - | No | false | Force delete bucket even if not empty |
| `--yes` | `-y` | - | No | false | Skip confirmation prompt |
| `--output` | `-o` | - | No | `text` | Output format: `text` or `json` |

### `verify`

| Option | Short | Env Var | Required | Default | Description |
|--------|-------|---------|----------|---------|-------------|
| `--volume-name` | `-v` | `EXTERNAL_VOLUME_NAME` | Yes | - | Snowflake external volume name |

### `describe`

| Option | Short | Env Var | Required | Default | Description |
|--------|-------|---------|----------|---------|-------------|
| `--volume-name` | `-v` | `EXTERNAL_VOLUME_NAME` | Yes | - | Snowflake external volume name |

### `update-trust`

| Option | Short | Env Var | Required | Default | Description |
|--------|-------|---------|----------|---------|-------------|
| `--bucket` | `-b` | `BUCKET` | No | - | S3 bucket base name (to derive role/volume names) |
| `--role-name` | `-r` | - | No | - | IAM role name to update |
| `--volume-name` | `-v` | `EXTERNAL_VOLUME_NAME` | No | - | Snowflake external volume name |

> At least `--bucket` or both `--role-name` and `--volume-name` must be provided.

**Correct command structure:**

```bash
snow-utils-volumes [GLOBAL OPTIONS] <command> [COMMAND OPTIONS]
snow-utils-volumes --region us-west-2 create --bucket iceberg-data --dry-run
snow-utils-volumes --no-prefix create --bucket iceberg-data
snow-utils-volumes delete --bucket iceberg-data --yes
snow-utils-volumes verify --volume-name MY_EXTERNAL_VOLUME
```

## Stopping Points

1. ✋ Step 1: If connection or AWS checks fail
2. ✋ Step 2: If infra check needed (prompts user)
3. ✋ Step 3: If volume exists (ask user what to do)
4. ✋ Step 4: After gathering requirements
5. ✋ Step 5: After dry-run preview (get approval)

## Output

- S3 bucket with versioning enabled
- IAM policy for S3 access
- IAM role with Snowflake trust policy
- Snowflake external volume
- Updated .env with all values

## Export for Sharing Flow

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

## Replay Flow (Minimal Approvals)

> **🚨 GOAL:** Replay is for less technical users who trust the setup. Minimize friction.
> Cortex Code constructs summary from manifest, runs `--dry-run` to show full SQL/JSON preview, gets ONE confirmation, then executes.
> **🔴 CRITICAL:** Even in replay flow, user MUST see the full SQL/JSON preview before confirmation. NEVER skip dry-run output.

**Trigger phrases:** "replay manifest", "replay volumes", "recreate external volume", "replay from manifest"

> **📍 Manifest Location:** `.snow-utils/snow-utils-manifest.md` (in current working directory)

**IMPORTANT:** This is the **snow-utils-volumes** skill. Only replay sections marked `<!-- START -- snow-utils-volumes -->`. If manifest contains other skills (PAT, Networks), ignore them - use the appropriate skill for those.

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

   Which should we use for volumes replay?
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

   **If `ADAPT_COUNT` > 0:** Extract `shared_by` from `## shared_info`, get current user's `SNOWFLAKE_USER`, show adaptation screen for volume values (BUCKET, EXTERNAL_VOLUME_NAME, EXTVOLUME_PREFIX). Three options: Accept adapted / Edit specific / Keep originals. Apply to manifest.

   **If `ADAPT_COUNT` = 0:** No markers, proceed with values as-is.

2. **Read manifest and find section** `<!-- START -- snow-utils-volumes -->`
   - If section NOT found: "No external volume resources in manifest. Nothing to replay for volumes."
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

   d. **Infer from manifest `snow-utils-volumes` section:**

      ```bash
      BUCKET=$(grep -A30 "<!-- START -- snow-utils-volumes" .snow-utils/snow-utils-manifest.md | grep "^\*\*Bucket:\*\*" | head -1 | sed 's/\*\*Bucket:\*\* //')
      AWS_REGION=$(grep -A30 "<!-- START -- snow-utils-volumes" .snow-utils/snow-utils-manifest.md | grep "^\*\*Region:\*\*" | head -1 | sed 's/\*\*Region:\*\* //')
      EXTVOLUME_PREFIX=$(grep -A30 "<!-- START -- snow-utils-volumes" .snow-utils/snow-utils-manifest.md | grep "^\*\*Prefix:\*\*" | head -1 | sed 's/\*\*Prefix:\*\* //')
      EXTERNAL_VOLUME_NAME=$(grep -A50 "<!-- START -- snow-utils-volumes" .snow-utils/snow-utils-manifest.md | grep "External Volume" | grep -o '[A-Z_]*EXTERNAL_VOLUME' | head -1)
      ```

   e. **Validate extracted values** (grep validation):

      ```bash
      for var in BUCKET AWS_REGION EXTERNAL_VOLUME_NAME; do
        val=$(eval echo \$$var)
        [ -z "$val" ] && echo "WARNING: Could not extract ${var} from manifest"
      done
      ```

      If any value is empty, ask user to enter manually or abort.

   f. **Shared manifest adapt-check (ALWAYS run for shared manifests):**

      If adaptation was already done in step 1b, skip this step.

      ```bash
      IS_SHARED=$(grep -c "## shared_info\|COCO_INSTRUCTION" .snow-utils/snow-utils-manifest.md 2>/dev/null)
      [ "$IS_SHARED" -gt 0 ] && ADAPT_COUNT=$(grep -c "# ADAPT:" .snow-utils/snow-utils-manifest.md 2>/dev/null)
      ```

      If shared AND `ADAPT_COUNT` > 0: show adaptation screen for BUCKET, EXTERNAL_VOLUME_NAME, EXTVOLUME_PREFIX (see step 1b).
      If shared AND no markers: proceed with values as-is.
      If not shared: skip.

   g. Write values (adapted or original) to `.env` (only if not already set):

      ```bash
      for var in BUCKET AWS_REGION EXTVOLUME_PREFIX EXTERNAL_VOLUME_NAME; do
        val=$(eval echo \$$var)
        [ -n "$val" ] && (grep -q "^${var}=" .env && \
          sed -i '' "s/^${var}=.*/${var}=${val}/" .env || \
          echo "${var}=${val}" >> .env)
      done
      ```

   **If .env exists and has all values:** Skip to step 4.

4. **Check Status field and act accordingly:**

| Status | Action |
|--------|--------|
| `REMOVED` | Proceed to step 6 (resources don't exist) |
| `COMPLETE` | **Collision detected** — proceed to step 5 |

5. **If Status is `COMPLETE` — Collision Strategy:**

   ```
   ⚠️ External volume resources already exist:

     Resource                    Status
     ─────────────────────────────────────
     External Volume: {EXTERNAL_VOLUME_NAME}   EXISTS
     S3 Bucket:       {BUCKET}                 EXISTS

   Choose a strategy:
   1. Use existing → skip creation, continue to next skill
   2. Replace → run 'delete' then recreate (DESTRUCTIVE)
   3. Rename → prompt for new volume name, create alongside existing
   4. Cancel → stop replay
   ```

   **⚠️ STOP**: Wait for user choice.

   | Choice | Action |
   |--------|--------|
   | **Use existing** | Skip volume creation entirely. |
   | **Replace** | Confirm with "Type 'yes, destroy' to confirm". Run delete flow, then proceed to step 6. |
   | **Rename** | Ask for new `EXTERNAL_VOLUME_NAME`. Update `.env` and proceed to step 6. |
   | **Cancel** | Stop replay. |

6. **Run dry-run to show full SQL/JSON preview:**

   ```bash
   uv run --project <SKILL_DIR> snow-utils-volumes \
     --region {AWS_REGION} \
     create --bucket {BUCKET} --dry-run
   ```

   **🔴 CRITICAL:** Terminal output gets truncated by the UI. After running the command, read the terminal output and paste the ENTIRE result into your response using language-tagged code blocks: ` ```text ` for summary, ` ```json ` for IAM/trust policy JSON, ` ```sql ` for CREATE EXTERNAL VOLUME SQL. See Step 5 formatting example above. Do NOT omit the JSON sections.

   Then ask:

   ```
   Proceed with creation? [yes/no]
   ```

   **⚠️ STOP**: Wait for user confirmation.

7. **On "yes":** Run actual command (ONE bash approval, NO further prompts):

   ```bash
   uv run --project <SKILL_DIR> snow-utils-volumes \
     --region {AWS_REGION} \
     create --bucket {BUCKET} --output json
   ```

8. **Verify (MANDATORY -- do NOT skip, even in replay):**

   ```bash
   uv run --project <SKILL_DIR> snow-utils-volumes \
     verify --volume-name {EXTERNAL_VOLUME_NAME}
   ```

   > Wait for IAM propagation (up to 60s). If verify fails, retry once after 30s. If still fails, stop and present error.

9. **Update manifest Status** from `REMOVED` to `COMPLETE` after successful creation and verification.

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

## SQL Reference (Snowflake Documentation)

> These links help Cortex Code infer correct SQL syntax when previewing or troubleshooting.

| Statement | Documentation |
|-----------|---------------|
| `CREATE EXTERNAL VOLUME` | https://docs.snowflake.com/en/sql-reference/sql/create-external-volume |
| `ALTER EXTERNAL VOLUME` | https://docs.snowflake.com/en/sql-reference/sql/alter-external-volume |
| `DROP EXTERNAL VOLUME` | https://docs.snowflake.com/en/sql-reference/sql/drop-external-volume |
| `DESC EXTERNAL VOLUME` | https://docs.snowflake.com/en/sql-reference/sql/desc-external-volume |
| `SHOW EXTERNAL VOLUMES` | https://docs.snowflake.com/en/sql-reference/sql/show-external-volumes |
| `CREATE ICEBERG TABLE` (Snowflake catalog) | https://docs.snowflake.com/en/sql-reference/sql/create-iceberg-table-snowflake |

## Troubleshooting

**Connection not found:** Ensure SNOWFLAKE_DEFAULT_CONNECTION_NAME in .env matches a configured connection. Run `snow connection list` to see available connections.

**Infrastructure not set up:** Run `uv run --project <SKILL_DIR> check-setup --run-setup` - it will check and offer to create the database and schemas.

**IAM propagation delay:** Script uses exponential backoff. Run `verify` after a minute if needed.

**S3 403 error:** Bucket name exists in another account. Choose different name.

**Trust policy mismatch:** Run `update-trust` to re-sync.

## Privilege Escalation Hints (for Apps)

**Background:** Apps using snow-utils resources should operate with restricted SA_ROLE. However, some operations genuinely require elevated privileges.

**If an app needs elevated access, suggest these patterns:**

| App Need | Recommended Approach |
|----------|---------------------|
| Create Iceberg tables | Grant CREATE ICEBERG TABLE on schema to SA_ROLE |
| Modify external volume | Use admin_role from manifest for one-time setup |
| Grant USAGE to other roles | Stored procedure with CALLER rights + admin_role |

**Example: Stored procedure for controlled escalation:**

```sql
-- Created once by admin, used by SA_ROLE
CREATE OR REPLACE PROCEDURE grant_iceberg_usage(target_role STRING)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
    -- SA_ROLE calls this, but it runs as admin_role
    GRANT USAGE ON EXTERNAL VOLUME <VOLUME_NAME> TO ROLE IDENTIFIER(:target_role);
    RETURN 'Granted USAGE to ' || :target_role;
END;
```

**IMPORTANT:** Never suggest putting admin_role in app .env. Always delegate to manifest.
