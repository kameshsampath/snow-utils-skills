# snow-utils-pat

Create and manage Snowflake Programmatic Access Tokens (PATs) for service accounts.

## Features

- **Service Account Creation** - Create dedicated users for automation
- **PAT Generation** - Generate secure tokens with configurable lifetime
- **Network Policy Integration** - Automatically creates network rules for IP-based access
- **Authentication Policy** - Restricts service account to PAT-only authentication
- **Token Rotation** - Rotate PATs without recreating infrastructure
- **Manifest Tracking** - Records resources for replay, audit, and cleanup

## Sample Prompts

### Create Service Account & PAT

```
"Create a PAT for service account"
"Set up a service account with PAT"
"Create programmatic access token"
"Set up automation credentials"
"Create a service user for CI/CD"
```

### Manage PATs

```
"Rotate my PAT"
"Rotate the PAT for MYAPP_RUNNER"
"Verify my PAT is working"
"Check PAT status"
```

### Cleanup

```
"Remove my service account"
"Clean up PAT resources"
"Delete the service account"
```

### Manifest Operations

```
"Replay PAT setup from manifest"
"Recreate service account from manifest"
"Resume PAT setup"
```

## Quick Start

1. Start CoCo in your project directory
2. Say: `"Create a PAT for service account"`
3. Follow the prompts to configure and create resources

## Prerequisites

- `uv` - Python package manager
- `snow` - Snowflake CLI
- Snowflake connection configured

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SNOWFLAKE_DEFAULT_CONNECTION_NAME` | Snowflake connection to use | (required) |
| `SA_ADMIN_ROLE` | Admin role for user/policy creation | ACCOUNTADMIN |
| `SA_USER` | Service account username | (prompted) |
| `SA_ROLE` | Role for service account | (prompted) |
| `SNOW_UTILS_DB` | Database for network rules | (prompted) |

## Resources Created

- **User** - Service account user (e.g., MYAPP_RUNNER)
- **PAT** - Programmatic access token
- **Network Rule** - IP allowlist for service account
- **Network Policy** - Assigned to service account
- **Authentication Policy** - Restricts to PAT-only auth

## Security Notes

- PAT tokens are never displayed in logs or diffs
- Network policies restrict access to specified IPs only
- Authentication policy prevents password-based login
- Tokens should be stored securely (environment variables, secrets manager)

## See Also

- [SKILL.md](./SKILL.md) - Detailed workflow for CoCo
- [snow-utils-networks](../snow-utils-networks/) - Additional network rules
- [snow-utils-volumes](../snow-utils-volumes/) - External volume creation
