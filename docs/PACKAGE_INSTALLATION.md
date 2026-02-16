# JAF Framework - Package Installation Guide

This guide explains how to install and use the JAF Framework as a Python package.

## Prerequisites

- **Python 3.11 or higher** is required
- pip (Python package installer)

## Installation Options

### 1. Install from Local Repository

Basic installation with core dependencies only:

```bash
pip install .
```

Or in editable/development mode:

```bash
pip install -e .
```

**Verify installation:**

```bash
python3 -c "import framework; print(f'JAF Framework v{framework.__version__} installed')"
```

### 2. Install with LLM Support

Includes CrewAI and OpenAI dependencies:

```bash
pip install .[llm]
```

### 3. Install with Demo Dependencies

Includes Pandas, PyArrow, Faker, and other demo tools:

```bash
pip install .[demo]
```

### 4. Install with Development Tools

Includes pytest, black, ruff, mypy for development:

```bash
pip install .[dev]
```

### 5. Install All Optional Dependencies

To install all optional dependencies (LLM, Demo, and Development tools):

```bash
pip install .[llm,demo,dev]
```

### 6. Install from GitLab Package Registry

Once published to GitLab package registry:

```bash
pip install jaf-framework --index-url https://gitlab.jems-group.com/api/v4/projects/<project-id>/packages/pypi/simple
```

## Core Dependencies

The package includes these core dependencies by default:

- `pydantic>=2.0,<3.0` - Data validation
- `pydantic-settings>=2.0,<3.0` - Settings management
- `sqlalchemy>=2.0,<3.0` - Database ORM
- `asyncpg>=0.28,<1.0` - Async PostgreSQL driver
- `aiosqlite>=0.19,<1.0` - Async SQLite driver
- `python-dotenv>=1.0,<2.0` - Environment variables

## Usage

After installation, you can import and use the framework:

```python
import framework

# Check version
print(framework.__version__)  # Output: 0.1.0

# Import core components
from framework import Actor, EventBus, Orchestrator
from framework.types import Plan, PlanStep

# Your code here...
```

## Package Structure

The package includes the following main components:

- `framework.actor` - Actor base classes and registry
- `framework.engine` - Engine abstraction and adapters (Native, CrewAI, VertexAI)
- `framework.event_bus` - Event-driven architecture components
- `framework.orchestrator` - Orchestration logic
- `framework.state_machine` - Process state management
- `framework.persistence` - Database models and repositories
- `framework.types` - Type definitions and schemas

## Validation

Run the validation script to verify the installation:

```bash
./validate_package.sh
```

This will check:
- ✓ pyproject.toml exists with all metadata
- ✓ Python version compatibility
- ✓ Package version is accessible
- ✓ All optional dependencies are configured

## Building the Package

To build distribution files:

```bash
pip install build
python -m build
```

This creates:
- `dist/jaf_framework-0.1.0-py3-none-any.whl` (wheel)
- `dist/jaf-framework-0.1.0.tar.gz` (source distribution)

## Publishing to GitLab Package Registry

1. Build the package (see above)
2. Configure authentication:
   ```bash
   export TWINE_USERNAME=<your-gitlab-username>
   export TWINE_PASSWORD=<your-gitlab-personal-access-token>
   ```
3. Upload to GitLab:
   ```bash
   pip install twine
   python -m twine upload --repository-url https://gitlab.jems-group.com/api/v4/projects/<project-id>/packages/pypi dist/*
   ```

## Troubleshooting

### Python Version Error

If you see: `ERROR: Package 'jaf-framework' requires a different Python: X.X.X not in '>=3.11'`

**Solution**: Upgrade to Python 3.11 or higher.

```bash
python3 --version  # Check your Python version
```

### Import Errors

If you encounter import errors after installation, try:

```bash
pip install -e . --force-reinstall
```

### Missing Dependencies

For specific features, install the corresponding extras:
- LLM features: `pip install .[llm]`
- Demo examples: `pip install .[demo]`
- Development: `pip install .[dev]`

## License

Proprietary - JEMS Group

## Support

For issues or questions:
- GitLab: https://gitlab.jems-group.com/jems/interne/jems-multi-agent-framework
- Email: innovation@jems-group.com
