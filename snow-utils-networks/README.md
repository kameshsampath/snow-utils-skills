# snow-utils-networks

Create and manage Snowflake network rules and policies for IP-based access control.

## Features

- **Local IP Detection** - Automatically detect your current IP for development access
- **GitHub Actions IPs** - Allowlist GitHub Actions runner IPs for CI/CD pipelines
- **Google Cloud IPs** - Allowlist GCP services (Cloud Run, GKE, Compute Engine)
- **Custom CIDRs** - Specify custom IP ranges for production environments
- **Smart Admin Role Detection** - Detects SA_ADMIN_ROLE from PAT skill if available
- **Manifest Tracking** - Records resources for replay, audit, and cleanup

## Sample Prompts

### Create Network Rules

```
"Create a network rule for my local IP"
"Create a network rule with GitHub Actions IPs"
"Create a network rule for Google Cloud"
"Create a network rule with GitHub Actions and my local IP"
"Allow my IP to access Snowflake"
"Set up network access for CI/CD"
```

### Update Network Rules

```
"Update my network rule with new IPs"
"Add GitHub Actions IPs to my network rule"
"Change the IPs in my network rule"
```

### Manage Resources

```
"List my network rules"
"Remove my network resources"
"Clean up network rules"
```

### Manifest Operations

```
"Replay network setup from manifest"
"Recreate network resources"
"Resume network setup"
```

## Quick Start

1. Start CoCo in your project directory
2. Say: `"Create a network rule for my local IP"`
3. Follow the prompts to configure and create resources

## Prerequisites

- `uv` - Python package manager
- `snow` - Snowflake CLI
- Snowflake connection configured

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SNOWFLAKE_DEFAULT_CONNECTION_NAME` | Snowflake connection to use | (required) |
| `NW_ADMIN_ROLE` | Admin role for network operations | ACCOUNTADMIN |
| `NW_RULE_NAME` | Network rule name | (prompted) |
| `NW_RULE_DB` | Database for network rules | (prompted) |
| `NW_RULE_SCHEMA` | Schema for network rules | NETWORKS |

## Resources Created

- **Network Rule** - IP allowlist with MODE=INGRESS, TYPE=IPV4
- **Network Policy** - References the network rule for user assignment

## See Also

- [SKILL.md](./SKILL.md) - Detailed workflow for CoCo
- [snow-utils-pat](../snow-utils-pat/) - Service account PAT creation
- [snow-utils-volumes](../snow-utils-volumes/) - External volume creation
