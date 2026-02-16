## Changelog

The project maintains a `CHANGELOG.md` following the Keep a Changelog format.

### Before the first release
- All notable changes must be added under the `[Unreleased]` section.
- Planned versions (e.g. `0.1.0`) may be documented without a Git tag.

### After a release
1. Create a Git tag following Semantic Versioning (e.g. `v0.1.0`).
2. Move relevant entries from `[Unreleased]` into the released version section.
3. Update comparison links at the bottom of `CHANGELOG.md`.

### Changelog entries
- Use user-facing language.
- Group changes under: Added, Changed, Deprecated, Removed, Fixed, Security.
- Reference issue IDs when available (e.g. `JAF-123`).

# Contributing to JAF Framework

Thank you for your interest in contributing to the JEMS Agent Framework (JAF)!

## Development Setup

1. Clone the repository
2. Install in development mode:
   ```bash
   pip install -e .[dev]
   ```
3. Install pre-commit hooks:
   ```bash
   pip install pre-commit
   pre-commit install
   ```
4. Run tests:
   ```bash
   pytest
   ```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality before commits:

- **black**: Python code formatter (enforces consistent style)
- **ruff**: Fast Python linter (catches common errors and style issues)
- **mypy**: Static type checker (validates type hints) - ✅ **enabled**
- **pre-commit-hooks**: Additional quality checks (trailing whitespace, YAML/TOML validation, etc.)

#### Initial Setup

Install pre-commit and set up hooks:
```bash
pip install pre-commit
pre-commit install
```

#### Running Hooks Manually

Test hooks on all files:
```bash
pre-commit run --all-files
```

Test hooks on specific files:
```bash
pre-commit run --files path/to/file.py
```

#### Updating Hooks

Update hooks to latest versions:
```bash
pre-commit autoupdate
```

**Note**: All code must pass pre-commit hooks (including mypy type checking) before merging. CI/CD pipeline enforces the same checks.

#### Bypassing Hooks (Not Recommended)

If you absolutely must bypass hooks (e.g., WIP commit):
```bash
git commit --no-verify -m "WIP: work in progress"
```

**Note**: All code must pass pre-commit hooks before merging. CI/CD pipeline enforces the same checks.

## Version Bumping Checklist

When releasing a new version, follow this checklist:

### 1. Update Version Number

Update the version in **ONE PLACE ONLY**:

- [ ] Update version in `framework/_version.py`:
  ```python
  __version__ = "X.Y.Z"
  __version_info__ = (X, Y, Z)
  ```

### 2. Update Package Configuration

- [ ] Update version in `pyproject.toml` to match `_version.py`:
  ```toml
  [project]
  version = "X.Y.Z"
  ```

### 3. Verify Version Consistency

Run this command to verify all versions match:

```bash
python3 -c "
from framework._version import __version__, __version_info__
import tomllib

with open('pyproject.toml', 'rb') as f:
    pyproject = tomllib.load(f)

pkg_version = pyproject['project']['version']
assert __version__ == pkg_version, f'Version mismatch: _version.py={__version__}, pyproject.toml={pkg_version}'
assert __version_info__ == tuple(map(int, __version__.split('.'))), 'version_info mismatch'
print(f'✓ All versions match: {__version__}')
"
```

### 4. Update Documentation

- [ ] Update CHANGELOG.md with release notes
- [ ] Update README.md if API changes
- [ ] Update version references in documentation

### 5. Testing

- [ ] Run full test suite: `pytest`
- [ ] Test installation: `pip install -e .`
- [ ] Verify version import:
  ```bash
  python3 -c "from framework import __version__, __version_info__; print(__version__, __version_info__)"
  ```
- [ ] Test `require_version()` utility:
  ```bash
  python3 -c "from framework.compat import require_version; require_version('0.1.0')"
  ```

### 6. Git Tagging

- [ ] Commit version changes:
  ```bash
  git add framework/_version.py pyproject.toml
  git commit -m "Bump version to X.Y.Z"
  ```
- [ ] Create Git tag:
  ```bash
  git tag -a vX.Y.Z -m "Release version X.Y.Z"
  ```
- [ ] Push tag:
  ```bash
  git push origin vX.Y.Z
  ```

### 7. Build and Publish

- [ ] Build distribution:
  ```bash
  python -m build
  ```
- [ ] Verify wheel contents:
  ```bash
  unzip -l dist/jaf_framework-X.Y.Z-py3-none-any.whl | grep _version.py
  ```
- [ ] Publish to GitLab Package Registry:
  ```bash
  python -m twine upload --repository-url https://gitlab.jems-group.com/api/v4/projects/<project-id>/packages/pypi dist/*
  ```

## Semantic Versioning

JAF Framework follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking API changes
- **MINOR** (0.Y.0): New features, backward compatible
- **PATCH** (0.0.Z): Bug fixes, backward compatible

## Deprecation Policy

When deprecating public APIs, use the `@deprecated` decorator from `framework.deprecation` and provide a reason, removal version, and replacement if available. Deprecated features will emit a warning for at least one MINOR version before removal. Document all deprecations in the changelog under the "Deprecated" section.

## Code Style

- Follow PEP 8
- Use `black` for formatting: `black .`
- Use `ruff` for linting: `ruff check .`
- Use type hints: `mypy framework/`

## Testing

- Write tests for all new features
- Maintain test coverage above 80%
- Use pytest fixtures for common setup

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Add tests for new functionality
4. Update documentation as needed
5. Ensure all tests pass
6. Submit pull request with description of changes

## Questions?

Contact: innovation@jems-group.com
