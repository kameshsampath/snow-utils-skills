<!-- COCO_INSTRUCTION: This is a shared snow-utils manifest.
     project_name: pat-demo
     setup_steps:
       1. Check if required skills are installed: cortex skill list
       2. For each skill in ## required_skills NOT in the list, run: cortex skill add <url>
       3. Once all skills installed, ask "replay pat from manifest"
     To trigger: ask "setup from shared manifest" or "replay pat" -->

# Snow-Utils Manifest

This manifest tracks Snowflake resources created by snow-utils skills.

---

## shared_info

shared_by: ALICE
shared_date: 2026-02-11
original_project_dir: pat-demo
notes: |
  PAT Demo - Create a Snowflake Programmatic Access Token for a service account.
  To replay: open in Cortex Code, ask "setup from shared manifest" or "replay pat"

## required_skills

snow-utils-pat: https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat

## project_recipe

project_name: pat-demo

## prereqs

tools_verified: 2026-02-11
required_tools:

- snow CLI
- uv

## admin_role
snow-utils-pat: ACCOUNTADMIN

<!-- START -- snow-utils-pat:ALICE_PAT_DEMO_RUNNER -->
## PAT: ALICE_PAT_DEMO_RUNNER

**Created:** 2026-02-11
**User:** ALICE_PAT_DEMO_RUNNER  # ADAPT: user-prefixed
**Role:** ALICE_PAT_DEMO_ACCESS  # ADAPT: user-prefixed
**Database:** ALICE_SNOW_UTILS  # ADAPT: user-prefixed
**PAT Name:** ALICE_PAT_DEMO_RUNNER_PAT  # ADAPT: user-prefixed
**Default Expiry (days):** 90
**Max Expiry (days):** 365
**Auth Policy:** ALICE_PAT_DEMO_RUNNER_AUTH_POLICY  # ADAPT: user-prefixed
**admin_role:** ACCOUNTADMIN
**Status:** REMOVED

| # | Type | Name | Status |
|---|------|------|--------|
| 1 | Database | ALICE_SNOW_UTILS | DONE |
| 2 | User | ALICE_PAT_DEMO_RUNNER | DONE |
| 3 | Role | ALICE_PAT_DEMO_ACCESS | DONE |
| 4 | Auth Policy | ALICE_PAT_DEMO_RUNNER_AUTH_POLICY | DONE |
| 5 | PAT | ALICE_PAT_DEMO_RUNNER_PAT | DONE |
<!-- END -- snow-utils-pat:ALICE_PAT_DEMO_RUNNER -->
