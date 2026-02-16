# Migration Guide

This document provides instructions for migrating between major or breaking versions of the JAF Framework.

---

## Upgrading JAF Framework

### From 0.1.x to 0.2.x

#### ⚠️ Breaking Changes

**1. `context` parameter in `execute_step()` is now `TypedContext` (JAF-83)** The legacy dictionary-based context has been replaced with a structured `TypedContext` object to improve type safety and developer experience.

**Migration:**

```python
# Before
result = context["step_0_result"]

# After
# Option A: Backward compatibility (standard dict-like access)
result = context.get_raw("step_0_result")

# Option B: Recommended typed access
result = context.get("step_0_result", MyDataContract)

```

---

#### Deprecations
Raw dict returns from tools deprecated, use DataContract

---

#### New Features
- Data contracts with validation
- Lineage tracking

---

## Upgrade Checklist
- [ ] Update requirements.txt: jaf-framework>=0.2.0
- [ ] Run tests - check for deprecation warnings
- [ ] Update tool return types to DataContract (optional but recommended)
- [ ] Review CHANGELOG.md for full list of changes
