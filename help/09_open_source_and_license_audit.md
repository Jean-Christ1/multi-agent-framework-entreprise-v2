# 09 -- Open Source and License Audit

Author: Armand Amoussou
Project: JAF (Jems Agent Framework)
Reference: branch main, tag v1.4.2, commit 9cbda91

---

## 1. Project License

| Property | Value |
|----------|-------|
| License declared in `pyproject.toml` | `Proprietary` |
| LICENSE file present | No |
| License header in source files | None |

**Finding**: The project declares itself as `Proprietary` via `pyproject.toml` (`license = {text = "Proprietary"}`), but no LICENSE file exists in the repository root. This is a **compliance gap**: any proprietary project distributed internally or externally should include a formal license file defining usage rights, redistribution restrictions, and intellectual property ownership.

**Recommendation**: Add a `LICENSE` file containing the JEMS Group proprietary license terms. If the project is intended for internal-only use, include a clear "Internal Use Only" clause.

---

## 2. Complete Dependency Inventory

### 2.1 Core Dependencies (requirements-core.txt / pyproject.toml)

| Package | Version Constraint | License | Category | Transitive Risk |
|---------|-------------------|---------|----------|-----------------|
| pydantic | >=2.0,<3.0 | MIT | Data validation | Low |
| pydantic-settings | >=2.0,<3.0 | MIT | Configuration | Low |
| sqlalchemy | >=2.0,<3.0 | MIT | ORM / Persistence | Low |
| asyncpg | >=0.28,<1.0 | Apache 2.0 | PostgreSQL async driver | Low |
| aiosqlite | >=0.19,<1.0 | MIT | SQLite async driver | Low |
| python-dotenv | >=1.0,<2.0 | BSD-3-Clause | Environment loading | Low |
| packaging | >=23.0,<25.0 | Apache 2.0 / BSD-2-Clause | Version utilities | Low |
| typer | >=0.9.0 | MIT | CLI framework | Low |

### 2.2 LLM Dependencies (requirements-llm.txt)

| Package | Version Constraint | License | Category | Transitive Risk |
|---------|-------------------|---------|----------|-----------------|
| crewai | >=0.28,<1.0 | MIT | Multi-agent orchestration | **Medium** |
| openai | >=1.0,<2.0 | Apache 2.0 | OpenAI API client | Low |

### 2.3 API Dependencies (requirements.txt, additional)

| Package | Version Constraint | License | Category | Transitive Risk |
|---------|-------------------|---------|----------|-----------------|
| fastapi | >=0.100,<1.0 | MIT | Web framework | Low |
| uvicorn[standard] | >=0.23,<1.0 | BSD-3-Clause | ASGI server | Low |
| httpx | >=0.25,<1.0 | BSD-3-Clause | HTTP client | Low |

### 2.4 Demo Dependencies (requirements-demo.txt)

| Package | Version Constraint | License | Category | Transitive Risk |
|---------|-------------------|---------|----------|-----------------|
| pyarrow | >=14.0.0,<18.0 | Apache 2.0 | Columnar data | Low |
| pandas | >=2.0,<3.0 | BSD-3-Clause | Data manipulation | Low |
| faker | >=22.0.0,<30.0 | MIT | Synthetic data generation | Low |
| pyyaml | >=6.0,<7.0 | MIT | YAML parsing | Low |
| lxml | >=5.0.0,<6.0 | BSD-3-Clause | XML parsing | Low |

### 2.5 Development Dependencies (pyproject.toml [dev])

| Package | Version Constraint | License | Category | Transitive Risk |
|---------|-------------------|---------|----------|-----------------|
| pytest | >=7.0 | MIT | Testing | Low |
| pytest-asyncio | >=0.21 | MIT | Async test support | Low |
| pytest-cov | >=4.0 | MIT | Coverage reporting | Low |
| black | >=23.0 | MIT | Code formatter | Low |
| ruff | >=0.1 | MIT | Linter | Low |
| mypy | >=1.0 | MIT | Type checker | Low |
| pre-commit | >=3.0 | MIT | Git hooks | Low |

### 2.6 Build System

| Package | License | Purpose |
|---------|---------|---------|
| hatchling | MIT | Build backend (PEP 517) |

### 2.7 CI/CD Pipeline Dependencies

| Package | License | Purpose |
|---------|---------|---------|
| build | MIT | Python package builder |
| twine | Apache 2.0 | PyPI upload tool |
| mkdocs-material | MIT | Documentation generator |
| mkdocstrings[python] | ISC | API docs from docstrings |

---

## 3. License Compatibility Analysis

### 3.1 License Distribution

| License Type | Count | Packages |
|-------------|-------|----------|
| MIT | 14 | pydantic, pydantic-settings, sqlalchemy, aiosqlite, typer, crewai, fastapi, faker, pyyaml, pytest, pytest-asyncio, pytest-cov, black, ruff, mypy, pre-commit |
| Apache 2.0 | 4 | asyncpg, openai, pyarrow, twine |
| BSD-3-Clause | 4 | python-dotenv, uvicorn, httpx, pandas, lxml |
| BSD-2-Clause | 1 | packaging (dual Apache 2.0 / BSD-2-Clause) |
| ISC | 1 | mkdocstrings |

### 3.2 Compatibility with Proprietary License

All dependencies use **permissive open-source licenses** (MIT, Apache 2.0, BSD). These licenses are fully compatible with proprietary software distribution:

- **MIT**: Permits commercial use, modification, distribution. Requires license notice preservation.
- **Apache 2.0**: Permits commercial use. Requires license notice, NOTICE file, and patent grant.
- **BSD-3-Clause**: Permits commercial use. Requires license notice and non-endorsement clause.

**Verdict**: No license incompatibility detected. All dependencies are permissive and compatible with the project's proprietary license declaration.

### 3.3 Copyleft Risk Assessment

| Risk Level | Description | Status |
|-----------|-------------|--------|
| GPL/LGPL contamination | Strong copyleft that could require source disclosure | **None detected** |
| AGPL contamination | Network copyleft for SaaS deployment | **None detected** |
| MPL contamination | File-level copyleft | **None detected** |

---

## 4. Transitive Dependency Risk

### 4.1 CrewAI (Medium Risk)

CrewAI is the highest-risk dependency due to:

- **Rapid version changes**: CrewAI is under active, breaking development. Version constraint `>=0.28,<1.0` spans significant API changes.
- **Deep transitive tree**: CrewAI pulls in LangChain, LangChain-OpenAI, and numerous sub-dependencies that are not explicitly pinned.
- **Vendor coupling**: CrewAI's internal architecture may change, breaking the `CrewAIAdapter` abstraction.
- **Mitigation**: The framework's `EngineAbstraction` pattern isolates CrewAI behind the `CrewAIAdapter`. Switching to `NativeEngine` or `NativeAdapter` eliminates this dependency entirely.

### 4.2 OpenAI (Low Risk)

- Stable API with semantic versioning.
- Well-documented breaking change policy.
- Direct dependency on the official OpenAI Python client.

### 4.3 SQLAlchemy (Low Risk)

- Mature, stable ORM with long-term support.
- Version constraint `>=2.0,<3.0` is appropriate for the async API used.

---

## 5. Open Source vs Proprietary Classification

### 5.1 Project Classification

| Aspect | Classification | Detail |
|--------|---------------|--------|
| Source code | **Proprietary** | Declared in pyproject.toml |
| Distribution model | **Internal** | Published to GitLab Package Registry |
| Author | JEMS Innovation Team | `innovation@jems-group.com` |
| External publication | **Public GitLab mirror** | `gitlab.com/llm-ai-agents-agentic-ai/` |

### 5.2 Intellectual Property Concerns

| Concern | Assessment |
|---------|------------|
| Source code visibility | Repository is public on gitlab.com, exposing proprietary code |
| License enforcement | No LICENSE file means default copyright applies (all rights reserved) but unclear terms |
| Contributor agreement | No CLA (Contributor License Agreement) in CONTRIBUTING.md |
| Patent claims | No patent declarations; Apache 2.0 dependencies include patent grants |

**Recommendation**: If the project is intended as proprietary:
1. Add a LICENSE file with explicit JEMS Group proprietary terms.
2. Add copyright headers to all source files.
3. Evaluate whether the public GitLab mirror should be private.
4. Add a CLA or IP assignment clause to CONTRIBUTING.md.

---

## 6. Supply Chain Security

### 6.1 Dependency Pinning

| Aspect | Current State | Recommendation |
|--------|--------------|----------------|
| Version ranges | Minimum-maximum ranges (e.g., `>=2.0,<3.0`) | Acceptable for library; use lock file for deployment |
| Lock file | **Not present** | Generate `requirements.lock` or use `pip-compile` |
| Hash verification | **Not configured** | Add `--require-hashes` for production deployments |
| Dependency source | PyPI (default) | Consider using private PyPI mirror for supply chain control |

### 6.2 Known Vulnerability Monitoring

| Tool | Configured | Recommendation |
|------|-----------|----------------|
| pip-audit | No | Add to CI pipeline: `pip-audit -r requirements.txt` |
| Safety | No | Alternative: `safety check -r requirements.txt` |
| Dependabot / Renovate | No | Configure for automated dependency updates |
| Snyk | No | Consider for enterprise-grade vulnerability scanning |

### 6.3 Build Reproducibility

| Aspect | Current State | Risk |
|--------|--------------|------|
| Build system | Hatchling (PEP 517) | Low risk, deterministic |
| Python version | 3.11 pinned in CI | Good practice |
| Dependency resolution | Non-deterministic (ranges) | Medium risk without lock file |

---

## 7. Compliance Checklist

| Requirement | Status | Action Required |
|-------------|--------|-----------------|
| LICENSE file in repository root | Missing | Create LICENSE with proprietary terms |
| Copyright headers in source files | Missing | Add headers to all `.py` files |
| Third-party license notices (NOTICE file) | Missing | Create NOTICE file listing all dependencies and their licenses |
| Apache 2.0 NOTICE compliance | Not verified | Verify if asyncpg, openai, pyarrow include NOTICE files |
| GPL/copyleft contamination | Clear | No action required |
| CLA for contributors | Missing | Add CLA to CONTRIBUTING.md |
| Dependency vulnerability scanning | Not configured | Add pip-audit or safety to CI |
| Lock file for reproducible builds | Missing | Generate and commit lock file |
| SBOM (Software Bill of Materials) | Missing | Generate SBOM for enterprise compliance |
| Export control classification | Not assessed | Review if LLM/AI components require export classification |

---

## 8. Summary

### Risk Matrix

| Category | Risk Level | Justification |
|----------|-----------|---------------|
| License compatibility | **Low** | All dependencies use permissive licenses |
| Copyleft contamination | **None** | No GPL/LGPL/AGPL dependencies |
| Supply chain security | **Medium** | No lock file, no vulnerability scanning, no hash verification |
| IP protection | **High** | Public repository, no LICENSE file, no copyright headers |
| Transitive dependency risk | **Medium** | CrewAI's deep dependency tree is unpinned |
| Compliance documentation | **High** | Missing LICENSE, NOTICE, SBOM, copyright headers |

### Priority Actions

1. **Immediate**: Add LICENSE file with JEMS Group proprietary terms.
2. **Immediate**: Add copyright headers to all source files.
3. **Short-term**: Generate and commit a dependency lock file.
4. **Short-term**: Add `pip-audit` to the CI pipeline.
5. **Medium-term**: Create NOTICE file with third-party license attributions.
6. **Medium-term**: Generate SBOM for enterprise compliance reporting.
7. **Medium-term**: Evaluate public repository exposure and consider making it private.
