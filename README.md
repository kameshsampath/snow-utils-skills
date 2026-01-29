# Snow Utils Skills

CoCo skills for Snowflake automation tasks.

## Overview

These skills were built using the [snow-bin-utils](https://github.com/kameshsampath/snow-bin-utils) project. They follow the Claude Skills style but are called **CoCo skills** for use with CoCo/Cortex Code.

> [!IMPORTANT]
> Currently, the skills only support external volumes with AWS (S3).

## Skills

| Skill | Description |
|-------|-------------|
| `iceberg-external-volume` | Create S3 bucket, IAM role/policy, and Snowflake external volume |
| `snowflake-pat` | Create service users with Programmatic Access Tokens |

## Installation

Add skills using the CoCo or Cortex CLI:

```bash
# Using coco
coco skill add https://github.com/kameshsampath/snow-utils-skills

# Or using cortex
cortex skill add https://github.com/kameshsampath/snow-utils-skills
```

## Usage

Trigger the skills with phrases like:

- "setup iceberg storage" or "create external volume"
- "create PAT" or "setup service account"

## Updating

To update to the latest version:

```bash
# Using coco
coco skill update snow-utils-skills

# Or using cortex
cortex skill update snow-utils-skills
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this software, please cite it using the information in [CITATION.cff](CITATION.cff).
