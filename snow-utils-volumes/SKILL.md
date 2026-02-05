---
name: snow-utils-volumes
description: "Create Snowflake external volumes with S3 storage. Use when: setting up external storage, creating external volume, configuring S3 for Snowflake, Iceberg tables, unloading data. Triggers: external volume, s3 snowflake, iceberg storage, data lake storage, replay volumes, replay volume manifest, recreate external volume, replay all manifests, replay all snow-utils."
---

# External Volume Setup (AWS S3)

Creates S3 bucket, IAM role/policy, and Snowflake external volume for cloud storage access.

**Use cases:** Iceberg tables, data lake access, COPY INTO unload, external stages.

## Workflow

**⚠️ CONNECTION USAGE:** This skill uses the **user's Snowflake connection** (SNOWFLAKE_DEFAULT_CONNECTION_NAME) for all operations. External volumes are account-level objects requiring elevated privileges (default: ACCOUNTADMIN).

**📋 NO PREREQUISITE:** This skill does NOT require snow-utils-pat. It operates independently using the user's connection.

> **📋 MANIFEST AS SOURCE OF TRUTH**
>
> Location: `.snow-utils/snow-utils-manifest.md`
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
- NEVER use flags that bypass user interaction (except documented `--yes` for CoCo automation)
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER skip SQL/JSON in dry-run output - always show BOTH summary AND full SQL/JSON
- NEVER hardcode admin roles - get admin_role from manifest
- NEVER put admin_role in app .env - apps should use SA_ROLE
- NEVER skip manifest - always update manifest IMMEDIATELY after user input
- NEVER leave .snow-utils unsecured - always chmod 700/600
- NEVER delete .snow-utils directory or manifest file - preserve for audit/cleanup/replay
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
command -v aws >/dev/null 2>&1 && echo "aws: OK" || echo "aws: MISSING"
```

**If any tool is MISSING, stop and provide installation instructions:**

| Tool | Install Command |
|------|-----------------|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `snow` | `pip install snowflake-cli` or `uv tool install snowflake-cli` |
| `aws` | `brew install awscli` or see [AWS CLI Install](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |

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
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -A1 "## admin_role" | grep "volumes:"
```

**If admin_role exists for volumes:** Use it.

**If admin_role NOT set for volumes, check other skills:**

```bash
cat .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -E "^(pat|networks):" | head -1
```

**If another skill has admin_role, ask user:**

```
Found admin_role from another skill:
  pat: USERADMIN
  
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
volumes: <USER_ROLE>
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
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  --region ${AWS_REGION} \
  create --bucket ${BUCKET} --dry-run
```

**Execute (without prefix):**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  --region ${AWS_REGION} --no-prefix \
  create --bucket ${BUCKET} --dry-run
```

**🔴 CRITICAL: SHOW BOTH SUMMARY AND FULL SQL/JSON**

After running dry-run, display output in TWO parts:

**Part 1 - Resource Summary (brief):**

```
AWS Resources:
  S3 Bucket:        kameshs-hirc-demo
  IAM Role ARN:     arn:aws:iam::<ACCOUNT_ID>:role/kameshs-hirc-demo-snowflake-role
  IAM Policy ARN:   arn:aws:iam::<ACCOUNT_ID>:policy/kameshs-hirc-demo-snowflake-policy

Snowflake Objects (account-level):
  External Volume:  KAMESHS_HIRC_DEMO_EXTERNAL_VOLUME
```

> **Note:** External volumes are account-level objects in Snowflake (no database/schema prefix).

**Part 2 - Full SQL and JSON (MANDATORY - do not skip on first display):**

Show these in formatted code blocks:

**IAM Policy JSON:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:GetObjectVersion", "s3:DeleteObject", "s3:DeleteObjectVersion"],
      "Resource": "arn:aws:s3:::bucket-name/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": "arn:aws:s3:::bucket-name"
    }
  ]
}
```

**IAM Trust Policy JSON:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "<SNOWFLAKE_IAM_USER_ARN>"},
      "Action": "sts:AssumeRole",
      "Condition": {"StringEquals": {"sts:ExternalId": "..."}}
    }
  ]
}
```

**Snowflake SQL:**

```sql
CREATE EXTERNAL VOLUME IF NOT EXISTS VOLUME_NAME
    STORAGE_LOCATIONS = (
        (
            NAME = 'storage-location-name'
            STORAGE_PROVIDER = 'S3'
            STORAGE_BASE_URL = 's3://bucket/'
            STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::...:role/...'
            STORAGE_AWS_EXTERNAL_ID = '...'
        )
    )
    ALLOW_WRITES = TRUE
    COMMENT = 'Used by KAMESHS - DEMO app - managed by snow-utils-volumes';
```

**FORBIDDEN:** Showing only summary without SQL/JSON. User MUST see BOTH parts on first display.

**⚠️ STOP**: Wait for explicit user approval ("yes", "ok", "proceed") before creating resources.

### Step 6: Create Resources

**Execute (with prefix):**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  --region ${AWS_REGION} \
  create --bucket ${BUCKET} --output json
```

**Execute (without prefix):**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
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
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
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
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  --region ${AWS_REGION} \
  delete --bucket ${BUCKET} --yes --output json
```

With S3 bucket deletion:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
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

### check_setup.py (from common)

**Description:** Pre-flight check for snow-utils infrastructure. Prompts interactively.

**Usage:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR>/../common python -m snow_utils_common.check_setup
```

**⚠️ DO NOT ADD ANY FLAGS.**

**Options:**

- `--quiet`, `-q`: Exit 0 if ready, 1 if not (scripting only)

### extvolume.py

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

**Create Options:**

- `--bucket`, `-b`: S3 bucket base name (required)
- `--dry-run`: Preview without creating
- `--output json`: Machine-readable output

**Correct command structure:**

```bash
extvolume.py [GLOBAL OPTIONS] create [CREATE OPTIONS]
extvolume.py --region us-west-2 create --bucket my-bucket --dry-run
extvolume.py --no-prefix create --bucket my-bucket
```

## Stopping Points

- ✋ Step 1: If connection or AWS checks fail
- ✋ Step 2: If infra check needed (prompts user)
- ✋ Step 3: If volume exists (ask user what to do)
- ✋ Step 4: After gathering requirements
- ✋ Step 5: After dry-run preview (get approval)

## Output

- S3 bucket with versioning enabled
- IAM policy for S3 access
- IAM role with Snowflake trust policy
- Snowflake external volume
- Updated .env with all values

## Replay Flow (Minimal Approvals)

> **🚨 GOAL:** Replay is for less technical users who trust the setup. Minimize friction.
> CoCo constructs summary from manifest (no dry-run needed), gets ONE confirmation, then executes.

**Trigger phrases:** "replay manifest", "replay volumes", "recreate external volume", "replay from manifest"

> **📍 Manifest Location:** `.snow-utils/snow-utils-manifest.md` (in current working directory)

**IMPORTANT:** This is the **snow-utils-volumes** skill. Only replay sections marked `<!-- START -- snow-utils-volumes -->`. If manifest contains other skills (PAT, Networks), ignore them - use the appropriate skill for those.

**If user asks to replay/recreate from manifest:**

1. **Read manifest from current project directory:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md
   ```

2. **Find section** `<!-- START -- snow-utils-volumes -->`
   - If section NOT found: "No external volume resources in manifest. Nothing to replay for volumes."
   - If section found: Continue to step 3

3. **Check Status field and act accordingly:**

| Status | Action |
|--------|--------|
| `REMOVED` | Proceed with creation (resources don't exist) |
| `COMPLETE` | Warn: "Resources already exist. Run 'delete' first or choose 'recreate' to cleanup and recreate." |

1. **If Status is NOT `REMOVED`**, stop and inform user of appropriate action.

2. **If Status is `REMOVED`**, extract values and display summary:

```
ℹ️  Replay from manifest will create:

  Resources:
    • S3 Bucket:        {PREFIX}-{BUCKET}
    • IAM Policy:       {PREFIX}-{BUCKET}-snowflake-policy
    • IAM Role:         {PREFIX}-{BUCKET}-snowflake-role
    • External Volume:  {PREFIX}_{BUCKET}_EXTERNAL_VOLUME

  AWS Tags (applied to all AWS resources):
    • managed-by:       snow-utils-volumes
    • user:             {PREFIX_UPPER}
    • project:          {BUCKET_UPPER}
    • snowflake-volume: {PREFIX}_{BUCKET}_EXTERNAL_VOLUME

  Configuration:
    Prefix:   {PREFIX}
    Bucket:   {BUCKET}
    Region:   {AWS_REGION}

Proceed with creation? [yes/no]
```

1. **On "yes":** Run actual command (ONE bash approval, NO further prompts):

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  --region {AWS_REGION} \
  create --bucket {BUCKET} --output json
```

1. **Update manifest Status** from `REMOVED` to `COMPLETE` after successful creation.

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

6. **On "yes":** Execute each skill's replay in order:

   **For each skill in timestamp order:**
   - Extract values from that skill's manifest section
   - Execute the appropriate create command
   - Update that section's status to `COMPLETE`
   - If ANY skill fails: STOP immediately, report which skill failed
   - Do NOT continue to next skill on failure

7. **On completion:** Display summary:

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

## Troubleshooting

**Connection not found:** Ensure SNOWFLAKE_DEFAULT_CONNECTION_NAME in .env matches a configured connection. Run `snow connection list` to see available connections.

**Infrastructure not set up:** Run `python -m snow_utils_common.check_setup` from common - it will prompt and offer to create.

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
