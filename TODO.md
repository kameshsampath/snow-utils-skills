# Snow-Utils Skills - v2 Roadmap

This document tracks planned enhancements for v2. Created from design discussions on 2026-02-04.

---

## 1. Per-Project Manifest Structure

**Current:** Each skill creates its own manifest section

```markdown
<!-- START -- snow-utils-pat:MYAPP_RUNNER -->
<!-- START -- snow-utils-networks:MYAPP_RULE -->
<!-- START -- snow-utils-volumes:MYAPP_VOLUME -->
```

**Proposed:** Single section per project, subsections for resources

```markdown
<!-- START -- snow-utils:MYAPP -->
## Project: MYAPP

### PAT Resources
#### MYAPP_RUNNER
| Type | Name | Status |
|------|------|--------|
| User | MYAPP_RUNNER | DONE |
| PAT | MYAPP_RUNNER_PAT | DONE |

### Network Resources
...

### Volume Resources
...

### Cleanup Commands
...
<!-- END -- snow-utils:MYAPP -->
```

**Benefits:**

- All project resources in one place
- Easier to see full project state
- Single cleanup flow per project

---

## 2. Multi-Resource Support

### Multiple PATs per Project

**Use case:** Same project needs multiple service accounts

- MYAPP_RUNNER (main automation)
- MYAPP_READONLY (dashboards)
- MYAPP_ADMIN (admin operations)

**Current limitation:** `.env` holds single SA_USER/SA_ROLE/SA_PAT

**Proposed:**

- `.env` = "current working state" (latest created)
- Manifest = "source of truth" (all created resources)
- Operations read manifest, offer choices if multiple exist
- CLI commands require explicit `--user` for multi-PAT scenarios

### Multiple Network Rules per Project

**Use case:** Different IP sources for different purposes

- MYAPP_LOCAL_RULE (developer access)
- MYAPP_GITHUB_RULE (CI/CD)
- MYAPP_API_EGRESS_RULE (external API access)

**Current limitation:** `.env` holds single NW_RULE_NAME

**Proposed:** Same pattern as PAT - manifest tracks all, Cortex Code offers choices

---

## 3. .env-less Mode

**Use case:** One-off resource creation, CI/CD, demos

**Current flow:**

1. Skill reads/writes .env
2. Creates resources
3. Records to manifest

**Proposed flow:**

1. Cortex Code prompts for ALL required values (no .env read)
2. Creates resources
3. Records to manifest with ALL config (no .env write)
4. Replay reads from manifest only

**Manifest stores complete config:**

```markdown
<!-- START -- snow-utils-networks:MYAPP_RULE -->
## Network: MYAPP_RULE

**Config:**
- Database: KAMESHS_SNOW_UTILS
- Schema: NETWORKS
- Admin Role: ACCOUNTADMIN
- Connection: snowhouse

**Resources:**
| Type | Name | Status |
|------|------|--------|
| Network Rule | MYAPP_RULE | DONE |
| Network Policy | MYAPP_POLICY | DONE |

**IP Sources:**
- Local IP: 192.168.1.1/32
- GitHub Actions: yes
...
<!-- END -->
```

**Implementation options:**

- `--no-env` flag on CLI
- Or: `.env` always optional, manifest is primary

---

## 4. Cross-Skill Admin Role Detection

**Current:**

- Networks → PAT: Detects SA_ADMIN_ROLE, offers to map to NW_ADMIN_ROLE ✓
- PAT → Networks: Does NOT detect NW_ADMIN_ROLE

**Proposed:** Bidirectional detection

- If SA_ADMIN_ROLE empty but NW_ADMIN_ROLE set → offer to reuse
- Symmetric behavior between skills

**Priority:** Low (PAT is typically run first)

---

## 5. Smart Multi-Resource Operations

When manifest has multiple resources:

**Cleanup:**

```
Cortex Code: "Found 3 network rules in manifest. Which to remove?"
  1. MYAPP_LOCAL_RULE (COMPLETE)
  2. MYAPP_GITHUB_RULE (COMPLETE)
  3. MYAPP_API_RULE (REMOVED)
  4. All of the above
```

**Replay:**

```
Cortex Code: "Found 2 PATs in manifest. Which to replay?"
  1. MYAPP_RUNNER (REMOVED) - can replay
  2. MYAPP_READONLY (COMPLETE) - already exists
```

---

## 6. Unified Project Cleanup

**Current:** Per-skill cleanup commands

**Proposed:** Single command to clean entire project

```bash
# Clean all MYAPP resources across all skills
snow-utils cleanup --project MYAPP
```

Or Cortex Code-driven:

```
User: "Clean up MYAPP project"

Cortex Code reads manifest, finds all MYAPP resources:
- 2 PATs
- 3 Network Rules
- 1 Volume

Executes cleanup in dependency order:
1. Unset policies from users
2. Drop PATs
3. Drop users
4. Drop network policies
5. Drop network rules
6. Drop volumes
```

---

## 7. CLI Confirmation Handling for Non-Interactive Mode

**Current:** CLI uses `@click.confirmation_option` which requires `--yes` flag in non-interactive context (Cortex Code bash).

**Workaround:** SKILL.md instructs Cortex Code to add `--yes` to delete commands.

**Proposed:** CLI checks `--output json` mode and skips confirmation:

```python
# Before (requires --yes in Cortex Code)
@click.confirmation_option(prompt="Delete this network rule?")
def rule_delete_cmd(...):

# After (auto-skips in json mode)
@click.option("-o", "--output", type=click.Choice(["text", "json"]), default="text")
def rule_delete_cmd(..., output: str):
    if output == "text":
        if not click.confirm("Delete this network rule?", default=True):
            raise click.Abort()
    # proceed with delete
```

**Affected commands:**

- `snow-utils-networks rule delete`
- `snow-utils-networks policy delete`
- `snow-utils-pat remove`

**Pattern:** `--output json` = non-interactive (Cortex Code), `--output text` = interactive (CLI)

---

## Implementation Order (Suggested)

1. **Per-project manifest structure** - Foundation for other features
2. **Multi-resource support** - Needed for real-world usage
3. **.env-less mode** - Clean separation of concerns
4. **Smart multi-resource operations** - Better UX
5. **Unified project cleanup** - Convenience
6. **Cross-skill admin detection** - Nice to have

---

## Notes

- v1 (current): Single resource per type, .env-driven, works for most use cases
- v2: Multi-resource, manifest-driven, production-ready workflows
- Consider backward compatibility with v1 manifests
