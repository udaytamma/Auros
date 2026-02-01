# Documentation Audit Guide

**Purpose:** Systematic process for identifying and fixing discrepancies between documentation and implementation.

---

## When to Run an Audit

- After completing a major feature or refactor
- Before a release or demo
- When onboarding reveals doc confusion
- Quarterly maintenance (recommended)

---

## Audit Checklist

### 1. API Reference

| Check | How to Verify |
|-------|---------------|
| **Endpoints exist** | Compare doc endpoints with actual routers (`grep "@router" api/routers/`) |
| **Request/response shapes** | Read Pydantic schemas in `schemas.py`, compare with doc examples |
| **Query parameters** | Check function signatures in router files |
| **Status codes** | Verify error handling matches documented codes |
| **Authentication** | Check if auth is documented, matches `auth.py` implementation |

```bash
# Find all API endpoints
grep -r "@router\.\(get\|post\|patch\|delete\)" api/routers/

# Find all Pydantic response models
grep -r "response_model=" api/routers/
```

### 2. Data Model

| Check | How to Verify |
|-------|---------------|
| **Tables exist** | Compare doc tables with `models.py` classes |
| **Column names/types** | Read SQLAlchemy model definitions |
| **Constraints** | Check `nullable`, `default`, `unique` in models |
| **Relationships** | Verify foreign keys and relationships |
| **Indexes** | Check for `Index()` definitions |

```bash
# List all SQLAlchemy models
grep "class.*Base" api/models.py
```

### 3. Configuration

| Check | How to Verify |
|-------|---------------|
| **Environment variables** | Compare doc with `config.py` Settings class |
| **Default values** | Check Pydantic Field defaults |
| **Required vs optional** | Look for `| None` or default values |

```bash
# Find all env vars in config
grep -E "^\s+\w+:" api/config.py
```

### 4. URLs and Ports

| Check | How to Verify |
|-------|---------------|
| **API base URL** | Check `main.py` uvicorn config or startup scripts |
| **External URLs** | Compare seed data with docs (e.g., company URLs) |
| **Service endpoints** | Verify Ollama, Slack, etc. URLs |

### 5. UI Documentation

| Check | How to Verify |
|-------|---------------|
| **TypeScript interfaces** | Compare with actual `types/` or inline types |
| **API client methods** | Check `api/client.ts` or equivalent |
| **Component structure** | Verify components exist in `components/` |

---

## Audit Process

### Step 1: Generate Comparison List

Create a checklist by extracting key items from docs:

```bash
# Extract documented endpoints
grep -E "GET|POST|PATCH|DELETE" docs/*.md

# Extract documented env vars
grep -E "^[A-Z_]+=" docs/*.md
```

### Step 2: Verify Each Item

For each documented item:

1. **Read the implementation** - Don't assume, verify
2. **Note discrepancies** - Create a list of differences
3. **Determine source of truth** - Usually implementation wins
4. **Categorize severity**:
   - **Critical**: Would cause errors if followed (wrong URLs, missing fields)
   - **Moderate**: Misleading but functional (wrong defaults, outdated examples)
   - **Minor**: Cosmetic (formatting, typos)

### Step 3: Fix One at a Time

Process fixes sequentially to avoid confusion:

1. Read the relevant implementation file
2. Update the documentation
3. Verify the change is correct
4. Move to next item

### Step 4: Verify Build

After all fixes:

```bash
# For Next.js/React docs
npm run build

# For static site generators
npm run build && npm run lint
```

---

## Common Discrepancy Patterns

### Response Shape Changes

**Symptom**: Doc shows `{"data": [...]}`, implementation returns `[...]`

**Check**: Look at `response_model=` in router and the Pydantic schema

### Field Name Drift

**Symptom**: Doc says `new_this_week`, code uses `new_jobs`

**Check**: Compare Pydantic schema field names exactly

### Missing Endpoints

**Symptom**: Feature exists but not documented

**Check**: Scan routers for endpoints not in docs

### Deprecated Parameters

**Symptom**: Doc shows filter that was removed

**Check**: Compare router function parameters with doc

### URL/Port Changes

**Symptom**: Localhost:8000 in docs but app runs on 8008

**Check**: Review `main.py`, `docker-compose.yml`, startup scripts

### Strategy/Architecture Changes

**Symptom**: Doc describes approach that was replaced (e.g., networkidle vs load)

**Check**: Read actual implementation logic, not just signatures

---

## Audit Report Template

```markdown
# Documentation Audit Report

**Date**: YYYY-MM-DD
**Auditor**: [Name]
**Scope**: [API Reference / Data Model / Full]

## Summary

- Total items checked: X
- Discrepancies found: Y
- Critical: A
- Moderate: B
- Minor: C

## Findings

### Critical

1. **[Location]**: [Description of issue]
   - Doc says: X
   - Implementation: Y
   - Fix: [What was done]

### Moderate

1. ...

### Minor

1. ...

## Files Modified

- `docs/api-reference.md`
- `docs/data-model.md`
- ...

## Verification

- [ ] Build passes
- [ ] Examples tested
- [ ] Links verified
```

---

## Prevention

To minimize future drift:

1. **Update docs with code** - Same PR/commit when possible
2. **Code review includes docs** - Reviewers check doc accuracy
3. **Automated checks** - OpenAPI schema validation, doc link checkers
4. **Quarterly audits** - Schedule regular reviews

---

## Quick Reference Commands

```bash
# Find all router endpoints
grep -rn "@router\." api/routers/

# Find all Pydantic models
grep -rn "class.*BaseModel" api/

# Find all env var usages
grep -rn "settings\." api/

# Find documented URLs
grep -rn "localhost:" docs/

# Compare file lists
diff <(ls api/routers/) <(grep -h "^###" docs/api-reference.md)
```
