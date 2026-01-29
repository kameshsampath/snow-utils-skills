---
name: iceberg-external-volume
description: "Create Snowflake external volumes for Iceberg tables with S3 storage. Use when: setting up Iceberg storage, creating external volume, configuring S3 for Snowflake. Triggers: iceberg storage, external volume, s3 snowflake, setup iceberg."
---

# Iceberg External Volume Setup

Creates S3 bucket, IAM role/policy, and Snowflake external volume for Apache Iceberg tables.

## Workflow

### Step 1: Check Environment

**Actions:**

1. **Verify** project has required files:
   ```bash
   ls -la .env pyproject.toml 2>/dev/null || echo "missing"
   ```

2. **If .env missing**, create template:
   ```bash
   cat > .env << 'EOF'
   # Snowflake connection
   SNOWFLAKE_DEFAULT_CONNECTION_NAME=

   # AWS settings  
   AWS_REGION=us-west-2

   # External volume settings
   BUCKET=
   EXTVOLUME_PREFIX=
   EOF
   ```

3. **Verify** AWS credentials:
   ```bash
   aws sts get-caller-identity
   ```

4. **Verify** Snowflake connection:
   ```bash
   snow connection test
   ```

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

### Step 3: Preview (Dry Run)

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extvolume.py \
  create --bucket <BUCKET> --region <REGION> --dry-run
```

**Present** the planned resources to user.

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
