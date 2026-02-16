#!/bin/bash
# Validation script for version management implementation
# Tests all acceptance criteria for JAF Framework version management

echo "=================================================="
echo "JAF Framework Version Management Validation"
echo "=================================================="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to project directory
cd "$(dirname "$0")"

# Test 1: from framework import __version__ returns version string
echo "1. Testing 'from framework import __version__'..."
VERSION=$(python3 -c "from framework import __version__; print(__version__)" 2>&1)
if [ "$VERSION" = "0.1.0" ]; then
    echo -e "${GREEN}✓${NC} __version__ = '$VERSION'"
else
    echo -e "${RED}✗${NC} Failed to import __version__: $VERSION"
fi
echo ""

# Test 2: from framework import __version_info__ returns tuple
echo "2. Testing 'from framework import __version_info__'..."
VERSION_INFO=$(python3 -c "from framework import __version_info__; print(__version_info__)" 2>&1)
if [ "$VERSION_INFO" = "(0, 1, 0)" ]; then
    echo -e "${GREEN}✓${NC} __version_info__ = $VERSION_INFO"
else
    echo -e "${RED}✗${NC} Failed to import __version_info__: $VERSION_INFO"
fi
echo ""

# Test 3: require_version() utility for downstream projects
echo "3. Testing require_version() utility..."

# Test with matching version
python3 -c "from framework.compat import require_version; require_version('0.1.0')" 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} require_version('0.1.0') works"
else
    echo -e "${RED}✗${NC} require_version('0.1.0') failed"
fi

# Test with lower version (should pass)
python3 -c "from framework.compat import require_version; require_version('0.0.1')" 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} require_version('0.0.1') works"
else
    echo -e "${RED}✗${NC} require_version('0.0.1') failed"
fi

# Test with higher version (should fail)
python3 -c "from framework.compat import require_version; require_version('0.2.0')" 2>&1 > /dev/null
if [ $? -ne 0 ]; then
    echo -e "${GREEN}✓${NC} require_version('0.2.0') correctly raises error"
else
    echo -e "${RED}✗${NC} require_version('0.2.0') should have raised error"
fi
echo ""

# Test 4: Version in pyproject.toml matches _version.py
echo "4. Testing version consistency between files..."
python3 -c "
from framework._version import __version__, __version_info__
import re

with open('pyproject.toml', 'r') as f:
    content = f.read()
    match = re.search(r'version\s*=\s*\"([^\"]+)\"', content)
    pkg_version = match.group(1) if match else None

if __version__ == pkg_version:
    print('✓ Versions match: {} == {}'.format(__version__, pkg_version))
    exit(0)
else:
    print('✗ Version mismatch: _version.py={}, pyproject.toml={}'.format(__version__, pkg_version))
    exit(1)
" 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Version in pyproject.toml matches _version.py"
else
    echo -e "${RED}✗${NC} Version mismatch between files"
fi
echo ""

# Test 5: Version bump checklist documented in CONTRIBUTING.md
echo "5. Testing CONTRIBUTING.md documentation..."
if [ -f "CONTRIBUTING.md" ]; then
    echo -e "${GREEN}✓${NC} CONTRIBUTING.md exists"

    grep -q "Version Bumping Checklist" CONTRIBUTING.md && echo -e "${GREEN}  ✓${NC} Contains version bumping checklist"
    grep -q "_version.py" CONTRIBUTING.md && echo -e "${GREEN}  ✓${NC} References _version.py"
    grep -q "pyproject.toml" CONTRIBUTING.md && echo -e "${GREEN}  ✓${NC} References pyproject.toml"
else
    echo -e "${RED}✗${NC} CONTRIBUTING.md not found"
fi
echo ""

# Additional checks
echo "Additional checks:"
echo "----------------"

# Check if _version.py exists
if [ -f "framework/_version.py" ]; then
    echo -e "${GREEN}✓${NC} framework/_version.py exists"
else
    echo -e "${RED}✗${NC} framework/_version.py not found"
fi

# Check if compat.py exists
if [ -f "framework/compat.py" ]; then
    echo -e "${GREEN}✓${NC} framework/compat.py exists"
else
    echo -e "${RED}✗${NC} framework/compat.py not found"
fi

# Check if packaging dependency is in pyproject.toml
grep -q "packaging>=" pyproject.toml && echo -e "${GREEN}✓${NC} packaging dependency added to pyproject.toml"

# Check __all__ exports
python3 -c "from framework import __all__; assert '__version__' in __all__; assert '__version_info__' in __all__; print('✓ Version exports in __all__')" 2>&1

echo ""
echo "=================================================="
echo "Validation Complete"
echo "=================================================="
