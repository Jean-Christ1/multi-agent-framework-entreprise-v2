#!/bin/bash
# Validation script for pyproject.toml package setup
# This script validates all acceptance criteria for JAF-framework package

echo "=================================================="
echo "JAF Framework Package Validation"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
if [ $(echo "$PYTHON_VERSION >= 3.11" | bc -l) -eq 1 ]; then
    echo -e "${GREEN}✓${NC} Python version $PYTHON_VERSION (>= 3.11 required)"
else
    echo -e "${RED}✗${NC} Python version $PYTHON_VERSION (>= 3.11 required)"
    echo "Note: Package requires Python 3.11+. Install process will fail on older versions."
fi
echo ""

# Acceptance Criteria 1: pyproject.toml created with all metadata
echo "1. Checking pyproject.toml exists with all metadata..."
if [ -f "pyproject.toml" ]; then
    echo -e "${GREEN}✓${NC} pyproject.toml exists"

    # Check key sections
    grep -q "\[build-system\]" pyproject.toml && echo -e "${GREEN}  ✓${NC} build-system configured"
    grep -q "name = \"jaf-framework\"" pyproject.toml && echo -e "${GREEN}  ✓${NC} Package name set"
    grep -q "version = \"0.1.0\"" pyproject.toml && echo -e "${GREEN}  ✓${NC} Version set"
    grep -q "requires-python = \">=3.11\"" pyproject.toml && echo -e "${GREEN}  ✓${NC} Python version constraint set"
else
    echo -e "${RED}✗${NC} pyproject.toml not found"
fi
echo ""

# Acceptance Criteria 2-5: Installation with different extras
if [ $(echo "$PYTHON_VERSION >= 3.11" | bc -l) -eq 1 ]; then
    echo "2. Testing 'pip install .' from repo root..."
    python3 -m pip install -e . > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} pip install -e . works"
    else
        echo -e "${RED}✗${NC} pip install -e . failed"
    fi
    echo ""

    echo "3. Testing 'pip install .[llm]' for LLM dependencies..."
    python3 -m pip install -e ".[llm]" --dry-run 2>&1 | grep -q "crewai\|openai"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} pip install .[llm] includes LLM dependencies"
    else
        echo -e "${RED}✗${NC} LLM dependencies not configured correctly"
    fi
    echo ""

    echo "4. Testing 'pip install .[demo]' for demo dependencies..."
    python3 -m pip install -e ".[demo]" --dry-run 2>&1 | grep -q "pandas\|faker\|pyarrow"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} pip install .[demo] includes demo dependencies"
    else
        echo -e "${RED}✗${NC} Demo dependencies not configured correctly"
    fi
    echo ""

    echo "5. Testing 'pip install .[dev]' for dev tools..."
    python3 -m pip install -e ".[dev]" --dry-run 2>&1 | grep -q "pytest\|black\|ruff"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} pip install .[dev] includes dev dependencies"
    else
        echo -e "${RED}✗${NC} Dev dependencies not configured correctly"
    fi
    echo ""
else
    echo "2-5. Skipping installation tests (Python >= 3.11 required)"
    echo ""
fi

# Acceptance Criteria 6: Package version accessible via framework.__version__
echo "6. Testing package version accessible via framework.__version__..."
VERSION=$(python3 -c "import sys; sys.path.insert(0, '.'); import framework; print(framework.__version__)" 2>/dev/null)
if [ "$VERSION" = "0.1.0" ]; then
    echo -e "${GREEN}✓${NC} framework.__version__ = $VERSION"
else
    echo -e "${RED}✗${NC} framework.__version__ not accessible or incorrect"
fi
echo ""

# Additional checks
echo "Additional package configuration checks:"
echo "----------------------------------------"
grep -q "\[tool.hatch.build.targets.wheel\]" pyproject.toml && echo -e "${GREEN}✓${NC} Wheel build target configured"
grep -q "packages = \[\"framework\"\]" pyproject.toml && echo -e "${GREEN}✓${NC} Framework package included in build"
grep -q "\[project.urls\]" pyproject.toml && echo -e "${GREEN}✓${NC} Project URLs configured"
grep -q "\[project.optional-dependencies\]" pyproject.toml && echo -e "${GREEN}✓${NC} Optional dependencies configured"

echo ""
echo "=================================================="
echo "Validation Complete"
echo "=================================================="
