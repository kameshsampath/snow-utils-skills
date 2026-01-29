# Snow Bin Skills

CoCo skills for Snowflake automation tasks.

## Skills

| Skill | Description |
|-------|-------------|
| `iceberg-external-volume` | Create S3 bucket, IAM role/policy, and Snowflake external volume |
| `snowflake-pat` | Create service users with Programmatic Access Tokens |

## Installation

Clone into your project's `.claude/skills/` directory:

```bash
# From your project root
git clone git@github.com:kameshsampath/snow-bin-skills.git .claude/skills
```

Or clone to a central location and symlink:

```bash
# Clone once
git clone git@github.com:kameshsampath/snow-bin-skills.git ~/snow-bin-skills

# Symlink into each project
mkdir -p .claude/skills
ln -s ~/snow-bin-skills/iceberg-external-volume .claude/skills/
ln -s ~/snow-bin-skills/snowflake-pat .claude/skills/
```

## Usage

In Cortex Code, trigger the skills with phrases like:
- "setup iceberg storage" or "create external volume"
- "create PAT" or "setup service account"

## Updating

Pull latest changes:

```bash
cd .claude/skills  # or ~/snow-bin-skills if using symlinks
git pull origin main
```

## Source

These skills wrap the CLI tools from [snow-bin-utils](https://github.com/kameshsampath/snow-bin-utils).
