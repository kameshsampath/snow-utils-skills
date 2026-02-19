<!-- CORTEX_CODE_INSTRUCTION: This is a shared snow-utils manifest.
     project_name: volumes-demo
     setup_steps:
       1. Check if required skills are installed: cortex skill list
       2. For each skill in ## required_skills NOT in the list, run: cortex skill add <url>
       3. Once all skills installed, ask "replay volumes from manifest"
     To trigger: ask "setup from shared manifest" or "replay volumes" -->

# Snow-Utils Manifest

This manifest tracks Snowflake resources created by snow-utils skills.

---

## shared_info

shared_by: ALICE
shared_date: 2026-02-11
original_project_dir: volumes-demo
notes: |
  Volumes Demo - Create a Snowflake external volume with S3 storage for Iceberg tables.
  To replay: open in Cortex Code, ask "setup from shared manifest" or "replay volumes"

## required_skills

snow-utils-volumes: https://github.com/kameshsampath/snow-utils-skills/snow-utils-volumes

## project_recipe

project_name: volumes-demo

## prereqs

tools_verified: 2026-02-11
required_tools:

- snow CLI
- aws CLI (with SSO configured)
- uv

## admin_role
snow-utils-volumes: ACCOUNTADMIN

<!-- START -- snow-utils-volumes:ALICE_VOLUMES_DEMO_VOL -->
## External Volume: ALICE_VOLUMES_DEMO_VOL

**Created:** 2026-02-11
**Volume Name:** ALICE_VOLUMES_DEMO_VOL  # ADAPT: user-prefixed
**S3 Bucket:** alice-volumes-demo  # ADAPT: user-prefixed
**AWS Region:** us-west-2
**IAM Role ARN:** arn:aws:iam::123456789012:role/alice-volumes-demo-snowflake-role  # ADAPT: user-prefixed
**admin_role:** ACCOUNTADMIN
**Status:** REMOVED

| # | Type | Name | Status |
|---|------|------|--------|
| 1 | S3 Bucket | alice-volumes-demo | DONE |
| 2 | IAM Role | alice-volumes-demo-role | DONE |
| 3 | IAM Policy | alice-volumes-demo-policy | DONE |
| 4 | External Volume | ALICE_VOLUMES_DEMO_VOL | DONE |
<!-- END -- snow-utils-volumes:ALICE_VOLUMES_DEMO_VOL -->
