---
name: snow-utils-skills
description: "Snowflake infrastructure automation skills. Use when: creating service accounts, PATs, network rules, external volumes, S3 storage. Triggers: PAT, programmatic access token, service account, network rule, network policy, external volume, S3, Iceberg storage."
---

# Snow-Utils Skills

Collection of Snowflake infrastructure automation skills.

## Available Sub-Skills

This repository contains multiple skills. Load the specific skill for your task:

| Task | Skill to Load | Trigger Phrases |
|------|---------------|-----------------|
| Service Account / PAT | `snow-utils-pat/SKILL.md` | "create PAT", "service account", "programmatic access token" |
| Network Rules & Policies | `snow-utils-networks/SKILL.md` | "network rule", "network policy", "IP allowlist", "GitHub Actions IPs" |
| External Volumes (S3) | `snow-utils-volumes/SKILL.md` | "external volume", "S3 storage", "Iceberg storage" |

## How to Use

When the user requests infrastructure automation, load the appropriate sub-skill:

1. **For PAT/Service Account requests:** Load `snow-utils-pat/SKILL.md`
2. **For Network requests:** Load `snow-utils-networks/SKILL.md`
3. **For External Volume/S3 requests:** Load `snow-utils-volumes/SKILL.md`

## Workflow

1. Identify which infrastructure component the user needs
2. Load the corresponding sub-skill SKILL.md file
3. Follow that skill's workflow

## Stopping Points

- Before loading a sub-skill: Confirm which component the user needs
