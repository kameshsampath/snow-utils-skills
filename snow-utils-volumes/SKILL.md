---
name: snow-utils-volumes
description: "Create Snowflake external volumes for Iceberg tables with S3 storage. Use when: setting up Iceberg storage, creating external volume, configuring S3 for Snowflake. Triggers: iceberg storage, external volume, s3 snowflake, setup iceberg."
---

# Iceberg External Volume Setup

Creates S3 bucket, IAM role/policy, and Snowflake external volume for Apache Iceberg tables.

## Workflow

**📋 PREREQUISITE:** This skill requires `snow-utils-pat` to be run first. If SA_PAT is not set in .env, stop and direct user to run snow-utils-pat.

**🚫 FORBIDDEN ACTIONS - NEVER DO THESE:**

- NEVER run SQL queries to discover/find/check values (no SHOW ROLES, SHOW DATABASES, SHOW EXTERNAL VOLUMES)
- NEVER auto-populate empty .env values by querying Snowflake
- NEVER use flags that bypass user interaction: `--yes`, `-y`, `--auto-setup`, `--auto-approve`, `--quiet`, `--force`, `--non-interactive`
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER skip SQL/JSON in dry-run output - always show BOTH summary AND full SQL/JSON
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
   - Keys to check: SNOWFLAKE_DEFAULT_CONNECTION_NAME, SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT_URL, SA_ROLE, SA_USER, SNOW_UTILS_DB, SA_PAT, EXTERNAL_VOLUME_NAME, BUCKET, AWS_REGION, EXTVOLUME_PREFIX

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

Read SA_ROLE, SA_USER, SNOW_UTILS_DB, and SA_PAT from .env:

```bash
grep -E "^(SA_ROLE|SA_USER|SNOW_UTILS_DB|SA_PAT)=" .env
```

**If SA_ROLE or SNOW_UTILS_DB is empty**, run check_setup.py first:

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/check_setup.py
```

**If SA_PAT is empty:**

⚠️ **STOP** - Service account PAT is required before creating volumes.

Tell the user:

```
SA_PAT is not set. You need to create a PAT for the service account first.

Run the snow-utils-pat skill to create the PAT:
  "Create a PAT for service account"

This ensures the external volume is created using the service account credentials.
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

Read SNOWFLAKE_USER from .env for default prefix:

```bash
grep "^SNOWFLAKE_USER=" .env | cut -d= -f2
```

**Ask user with prefix explanation:**

```
External Volume Configuration:

> **Note:** By default, all AWS resources (S3 bucket, IAM role, IAM policy) are prefixed 
> with your username to avoid naming conflicts in shared AWS accounts.
> Example: If you enter "iceberg-data" as bucket name with prefix "kameshs":
>   - S3 Bucket: kameshs-iceberg-data
>   - IAM Role: kameshs-iceberg-data-snowflake-role
>   - External Volume: KAMESHS_ICEBERG_DATA_EXTERNAL_VOLUME
> You can disable prefixing if you prefer raw names.

1. Bucket name (base name): 
2. AWS region [default: us-west-2]:
3. Use username prefix? [Y/n]:
   - If yes, prefix will be: <SNOWFLAKE_USER>
   - If no, resources will use raw bucket name
4. Allow writes? [default: yes]:
```

**⚠️ STOP**: Wait for user input.

**After user provides input, update .env:**

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
    ALLOW_WRITES = TRUE;
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

**On success:** Update .env with created volume name, show example Iceberg table DDL.

**On failure:** Rollback is automatic. Present error.

### Step 7: Verify

**Execute:**

```bash
set -a && source .env && set +a && uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  verify --volume-name ${EXTERNAL_VOLUME_NAME}
```

**Present** verification result and summary of created resources.

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

### extvolume.py

**Description:** Creates and manages Snowflake external volumes with S3 backend.

**Global Options (BEFORE command):**

- `-r, --region`: AWS region (default: us-west-2, or AWS_REGION env var)
- `-p, --prefix`: Custom prefix for AWS resources
- `--no-prefix`: Disable username prefix

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

## Troubleshooting

**Connection not found:** Ensure SNOWFLAKE_DEFAULT_CONNECTION_NAME in .env matches a configured connection. Run `snow connection list` to see available connections.

**Infrastructure not set up:** Run check_setup.py - it will prompt and offer to create.

**IAM propagation delay:** Script uses exponential backoff. Run `verify` after a minute if needed.

**S3 403 error:** Bucket name exists in another account. Choose different name.

**Trust policy mismatch:** Run `update-trust` to re-sync.
