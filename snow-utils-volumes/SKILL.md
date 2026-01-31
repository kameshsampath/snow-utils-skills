---
name: snow-utils-volumes
description: "Create Snowflake external volumes for Iceberg tables with S3 storage. Use when: setting up Iceberg storage, creating external volume, configuring S3 for Snowflake. Triggers: iceberg storage, external volume, s3 snowflake, setup iceberg."
---

# Iceberg External Volume Setup

Creates S3 bucket, IAM role/policy, and Snowflake external volume for Apache Iceberg tables.

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

3. **Verify** AWS credentials:
   ```bash
   aws sts get-caller-identity
   ```
   Show the output to user (Account ID, User ARN) to confirm correct AWS account.

4. **Verify** Snowflake connection:
   ```bash
   snow connection list
   ```
   If user needs to choose a connection, ask them and then:
   - Set `SNOWFLAKE_DEFAULT_CONNECTION_NAME=<chosen_connection>` in .env
   - Use this connection for all subsequent `snow` CLI commands

**If any check fails**: Stop and help user resolve.

### Step 2: Gather Requirements

**Ask user:**
```
To create the external volume:
1. Bucket name (base name, will be prefixed): 
2. AWS region (default: us-west-2):
3. Prefix for resources (default: your username):
4. Allow writes? (default: yes):
```

**⚠️ STOP**: Wait for user input.

**After user provides input, update `.env` with their values:**
```bash
# Update .env with user inputs (merge, don't overwrite existing values)
```

Update these variables in `.env`:
- `BUCKET=<user_bucket_name>`
- `AWS_REGION=<user_region>`
- `EXTVOLUME_PREFIX=<user_prefix>`
- `EXTERNAL_VOLUME_NAME=<PREFIX>_<BUCKET>_EXTERNAL_VOLUME`

This ensures values are saved for future runs and the script can read them.

### Step 3: Preview (Dry Run)

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  create --bucket <BUCKET> --region <REGION> --dry-run
```

**CRITICAL: Display the ACTUAL command output to the user.**

The dry-run output includes:
- **Step 2: IAM Policy JSON** - Full policy document 
- **Step 3: IAM Trust Policy JSON** - Initial and final trust policies
- **Step 4: Snowflake SQL** - CREATE EXTERNAL VOLUME statement

**YOU MUST copy/paste the JSON and SQL directly from the command output.**

Format the output for the user as follows:

**Resources to be created:**
- S3 Bucket: `<from output>`
- IAM Policy: `<from output>`  
- IAM Role: `<from output>`
- External Volume: `<from output>`

**1. IAM Policy (S3 Access Permissions):**
This policy grants Snowflake access to the S3 bucket.
```json
<COPY THE FULL JSON FROM "Policy Document:" IN STEP 2 OF OUTPUT>
```

**2. IAM Role Trust Policy (Initial - with placeholder):**
This is the initial trust policy before Snowflake's IAM user ARN is known.
```json
<COPY THE FULL JSON FROM "Initial Trust Policy (before Snowflake IAM user is known):" IN STEP 3>
```

**3. IAM Role Trust Policy (Final - after external volume created):**
This is the final trust policy after Snowflake provides its IAM user ARN.
```json
<COPY THE FULL JSON FROM "Final Trust Policy (after external volume creation):" IN STEP 3>
```

**4. Snowflake SQL:**
```sql
<COPY THE CREATE EXTERNAL VOLUME SQL FROM STEP 4 OF OUTPUT>
```

**ALL 4 SECTIONS ABOVE ARE REQUIRED. DO NOT:**
- Summarize as "aws iam create-policy --policy-name ..."
- Skip the IAM Policy JSON (S3 permissions)
- Skip the Initial Trust Policy (with placeholder ARN)
- Abbreviate or omit any JSON

**Users MUST review S3 permissions AND trust relationships before approving.**

**⚠️ STOP**: Get approval before creating resources.

### Step 4: Create Resources

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  create --bucket <BUCKET> --region <REGION> --output json
```

**On success**: Show example Iceberg table DDL.

**On failure**: Rollback is automatic. Present error and ask user how to proceed.

### Step 5: Verify

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  verify --volume-name <VOLUME_NAME>
```

**Present** verification result.

## Tools

### extvolume.py

**Description**: Creates and manages Snowflake external volumes with S3 backend.

**Commands:**
- `create`: Create S3 bucket, IAM role/policy, external volume
- `delete`: Remove all resources
- `verify`: Test external volume connectivity
- `describe`: Show external volume properties
- `update-trust`: Re-sync IAM trust policy

**Create Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  [--region REGION] [--prefix PREFIX] [--no-prefix] \
  create --bucket BUCKET [--dry-run] [--output json]
```

**Key Options:**
- `--bucket`: S3 bucket base name (required)
- `--region`: AWS region (default: us-west-2)
- `--prefix`: Resource prefix (default: username)
- `--no-prefix`: Disable prefix
- `--dry-run`: Preview without creating
- `--output json`: Machine-readable output
- `--no-writes`: Read-only volume
- `--skip-verify`: Skip connectivity check

**Delete Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  delete --bucket BUCKET [--delete-bucket] [--force]
```

## Stopping Points

- ✋ Step 1: If environment checks fail
- ✋ Step 2: After gathering requirements
- ✋ Step 3: After dry-run preview (get approval)
- ✋ Step 4: If creation fails

## Output

- S3 bucket with versioning enabled
- IAM policy for S3 access
- IAM role with Snowflake trust policy
- Snowflake external volume
- Example Iceberg table DDL

## Troubleshooting

**IAM propagation delay**: Script uses exponential backoff, but may still timeout. Run `verify` after a minute.

**S3 403 error**: Bucket name already exists in another account. Choose different name.

**Trust policy mismatch**: Run `update-trust` to re-sync IAM trust policy.

**External volume verification failed**: Check IAM role trust policy includes Snowflake's IAM user ARN.
