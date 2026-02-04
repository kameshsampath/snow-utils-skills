# snow-utils-skills

[Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) skills for Snowflake infrastructure automation.

## What is this?

A collection of skills that enable natural language automation of common Snowflake infrastructure tasks. Ask Cortex Code to create service accounts, network rules, or external volumes - it handles the complexity.

## Skills

| Skill | Description | Sample Prompts |
|-------|-------------|----------------|
| [snow-utils-pat](./snow-utils-pat/) | Service account PAT creation | "Create a PAT for service account", "Rotate my PAT" |
| [snow-utils-networks](./snow-utils-networks/) | Network rules & policies | "Create network rule for my IP", "Allow GitHub Actions" |
| [snow-utils-volumes](./snow-utils-volumes/) | External volumes for Iceberg | "Create external volume for S3" |

## Quick Start

### 1. Install Prerequisites

```bash
# Python package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Snowflake CLI
uv tool install snowflake-cli
```

### 2. Configure Snowflake Connection

```bash
snow connection add
snow connection test -c <connection_name>
```

### 3. Use with Cortex Code

Open Cortex Code and try:

```
"Create a PAT for my service account"
"Create a network rule for my local IP"
"Set up an external volume for S3"
```

## Features

- **Natural Language Interface** - Describe what you want, skills handle the details
- **Interactive Workflows** - Prompts for confirmation at each step
- **Manifest Tracking** - All resources recorded for replay, audit, and cleanup
- **Idempotent Operations** - Safe to re-run without side effects
- **Smart Detection** - Skills share configuration when used together

## Documentation

- [Cortex Code Documentation](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code)
- [Snowflake CLI Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index)

## Project Structure

```
snow-utils-skills/
├── common/                    # Shared Python utilities
├── snow-utils-pat/           # PAT skill
│   ├── SKILL.md              # Skill workflow (for CoCo)
│   ├── README.md             # User documentation
│   └── scripts/              # CLI tools
├── snow-utils-networks/      # Networks skill
│   ├── SKILL.md
│   ├── README.md
│   └── scripts/
├── snow-utils-volumes/       # Volumes skill
│   ├── SKILL.md
│   ├── README.md
│   └── scripts/
├── TESTING.md                # Test cases for all skills
└── TODO.md                   # v2 roadmap
```

## License

Apache 2.0
