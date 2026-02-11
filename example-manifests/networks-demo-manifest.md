<!-- COCO_INSTRUCTION: This is a shared snow-utils manifest.
     project_name: networks-demo
     setup_steps:
       1. Check if required skills are installed: cortex skill list
       2. For each skill in ## required_skills NOT in the list, run: cortex skill add <url>
       3. Once all skills installed, ask "replay network from manifest"
     To trigger: ask "setup from shared manifest" or "replay network" -->

# Snow-Utils Manifest

This manifest tracks Snowflake resources created by snow-utils skills.

---

## shared_info

shared_by: ALICE
shared_date: 2026-02-11
original_project_dir: networks-demo
notes: |
  Networks Demo - Create Snowflake network rules and policies for IP allowlisting.
  To replay: open in Cortex Code, ask "setup from shared manifest" or "replay network"

## required_skills

snow-utils-networks: https://github.com/kameshsampath/snow-utils-skills/snow-utils-networks

## project_recipe

project_name: networks-demo

## prereqs

tools_verified: 2026-02-11
required_tools:

- snow CLI
- uv

## admin_role
snow-utils-networks: ACCOUNTADMIN

<!-- START -- snow-utils-networks:ALICE_NETWORKS_DEMO_RUNNER -->
## Network: ALICE_NETWORKS_DEMO_RUNNER

**Created:** 2026-02-11
**Network Rule:** ALICE_NETWORKS_DEMO_RUNNER_NETWORK_RULE  # ADAPT: user-prefixed
**Network Policy:** ALICE_NETWORKS_DEMO_RUNNER_NETWORK_POLICY  # ADAPT: user-prefixed
**Database:** ALICE_SNOW_UTILS  # ADAPT: user-prefixed
**Schema:** NETWORKS
**Mode:** INGRESS
**Type:** IPV4
**admin_role:** ACCOUNTADMIN
**Status:** REMOVED

| # | Type | Name | Status |
|---|------|------|--------|
| 1 | Network Rule | ALICE_NETWORKS_DEMO_RUNNER_NETWORK_RULE | DONE |
| 2 | Network Policy | ALICE_NETWORKS_DEMO_RUNNER_NETWORK_POLICY | DONE |
| 3 | Policy Assignment | → ALICE_NETWORKS_DEMO_RUNNER | DONE |
<!-- END -- snow-utils-networks:ALICE_NETWORKS_DEMO_RUNNER -->
