---
name: snowflake-pat
description: "Create Snowflake Programmatic Access Tokens (PATs) for service accounts. Use when: setting up service user, creating PAT, configuring authentication policy, network policy for PAT. Triggers: programmatic access token, PAT, service account, snowflake authentication."
---

# Snowflake PAT Setup

Creates service users, network policies, authentication policies, and Programmatic Access Tokens for automation.

## Workflow

### Step 1: Check Environment

**Actions:**

1. **Verify** project has required files:
   ```bash
   ls -la .env 2>/dev/null || echo "missing"
   ```

2. **If .env missing**, create template:
   ```bash
   cat > .env << 'EOF'
   # Snowflake connection
   SNOWFLAKE_DEFAULT_CONNECTION_NAME=

   # Service account settings
   SA_USER=
   SA_ROLE=
   SA_ADMIN_ROLE=
   PAT_OBJECTS_DB=

   # Optional: specify local IP (auto-detected if empty)
   LOCAL_IP=
   EOF
   ```

3. **Verify** Snowflake connection:
   ```bash
   snow connection test
   ```

4. **Check** required privileges:
   - CREATE USER (or use existing user)
   - CREATE NETWORK RULE, NETWORK POLICY
   - CREATE AUTHENTICATION POLICY

**If any check fails**: Stop and help user resolve.

### Step 2: Gather Requirements

**Ask user:**
```
To create the PAT:
1. Service user name:
2. PAT role (role restriction for the token):
3. Admin role (for creating policies, default: same as PAT role):
4. Database for policy objects:
5. PAT expiry days (default: 30):
```

**⚠️ STOP**: Wait for user input.

### Step 3: Preview (Dry Run)

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <USER> --role <ROLE> --db <DB> --dry-run
```

**Present** the planned resources to user:
- Service user configuration
- Network rule and policy
- Authentication policy
- PAT name

**⚠️ STOP**: Get approval before creating resources.

### Step 4: Create Resources

**Execute:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user <USER> --role <ROLE> --db <DB> --output json
```

**On success**: 
- Token is written to .env file
- Show connection verification result

**On failure**: Present error and remediation steps.

### Step 5: Verify Connection

If `--skip-verify` was not used, connection is already verified.

Otherwise:
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  verify --user <USER>
```

## Tools

### pat.py

**Description**: Creates and manages Snowflake PATs with network and auth policies.

**Commands:**
- `create`: Create service user, policies, and PAT
- `remove`: Remove all PAT-related resources
- `rotate`: Rotate existing PAT
- `verify`: Test PAT connection

**Create Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  create --user USER --role ROLE --db DATABASE \
  [--admin-role ADMIN_ROLE] [--dry-run] [--output json]
```

**Key Options:**
- `--user`: Service user name (required)
- `--role`: PAT role restriction (required)
- `--admin-role`: Role for creating policies (default: same as --role)
- `--db`: Database for policy objects (required)
- `--pat-name`: Custom PAT name (default: {USER}_PAT)
- `--rotate`: Replace existing PAT
- `--dry-run`: Preview without creating
- `--output json`: Machine-readable output
- `--local-ip`: Override auto-detected IP
- `--default-expiry-days`: Token expiry (default: 30)
- `--skip-verify`: Skip connection verification

**Remove Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pat.py \
  remove --user USER --db DATABASE
```

## Stopping Points

- ✋ Step 1: If environment checks fail
- ✋ Step 2: After gathering requirements  
- ✋ Step 3: After dry-run preview (get approval)
- ✋ Step 4: If creation fails

## Output

- Service user (TYPE = SERVICE)
- Network rule with local IP
- Network policy (ENFORCED_REQUIRED)
- Authentication policy (PROGRAMMATIC_ACCESS_TOKEN only)
- PAT token (saved to .env)
- Verified connection

## Troubleshooting

**Network policy blocking**: Ensure your IP is in the network rule. Run with `--local-ip` to specify.

**Permission denied**: Admin role needs CREATE NETWORK RULE, CREATE NETWORK POLICY, CREATE AUTHENTICATION POLICY privileges.

**PAT already exists**: Use `--rotate` to replace existing PAT.

**Connection verification failed**: Check network policy allows your IP and auth policy is correctly assigned.

## Security Notes

- PAT tokens are stored in .env with proper escaping
- Network policy restricts access to specified IPs only
- Auth policy enforces PAT-only authentication (no password)
- Tokens have configurable expiry (default 30 days, max 365)
