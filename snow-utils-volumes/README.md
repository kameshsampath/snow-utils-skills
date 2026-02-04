# snow-utils-volumes

Create and manage Snowflake external volumes for Iceberg tables with cloud storage.

## Features

- **S3 Integration** - Create external volumes backed by AWS S3
- **IAM Trust Policy** - Generates IAM trust policy for Snowflake access
- **Prefix Support** - Organize data with customizable path prefixes
- **Multi-Region** - Support for different AWS regions
- **Manifest Tracking** - Records resources for replay, audit, and cleanup

## Sample Prompts

### Create External Volumes

```
"Create an external volume for S3"
"Set up Iceberg storage on S3"
"Create external volume for my-bucket"
"Set up external volume in us-west-2"
```

### Manage Volumes

```
"List my external volumes"
"Describe my external volume"
"Show external volume details"
```

### Cleanup

```
"Remove my external volume"
"Delete the external volume"
"Clean up Iceberg storage"
```

### Manifest Operations

```
"Replay volume setup from manifest"
"Recreate external volume"
```

## Quick Start

1. Start CoCo in your project directory
2. Say: `"Create an external volume for S3"`
3. Follow the prompts to configure bucket and create resources

## Prerequisites

- `uv` - Python package manager
- `snow` - Snowflake CLI
- `aws` - AWS CLI (for IAM policy creation)
- Snowflake connection configured
- AWS credentials configured

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SNOWFLAKE_DEFAULT_CONNECTION_NAME` | Snowflake connection to use | (required) |
| `AWS_REGION` | AWS region for S3 bucket | us-west-2 |
| `EV_BUCKET` | S3 bucket name | (prompted) |
| `EV_NAME` | External volume name | (prompted) |
| `EV_PREFIX` | Path prefix in bucket | (optional) |

## Resources Created

- **External Volume** - Snowflake external volume pointing to S3
- **IAM Role** - AWS IAM role with trust policy for Snowflake
- **IAM Policy** - S3 access policy for the bucket

## AWS Setup

The skill generates the IAM trust policy automatically. You'll need to:

1. Create the IAM role in AWS
2. Attach the generated trust policy
3. Grant S3 access to the bucket

## See Also

- [SKILL.md](./SKILL.md) - Detailed workflow for CoCo
- [snow-utils-pat](../snow-utils-pat/) - Service account PAT creation
- [snow-utils-networks](../snow-utils-networks/) - Network rules & policies
