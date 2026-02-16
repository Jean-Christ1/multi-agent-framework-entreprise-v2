import warnings
from framework.deprecation import deprecated


# 1. @deprecated decorator created
def test_deprecated_decorator_exists():
    assert callable(deprecated)


# 2. Warnings include reason, removal version, and replacement
@deprecated(reason="Use new_func", removal_version="0.3.0", replacement="new_func")
def old_func(x):
    return x * 2


def test_deprecation_warning_content():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        old_func(1)
        assert any(
            issubclass(warn.category, DeprecationWarning)
            and "Use new_func" in str(warn.message)
            and "0.3.0" in str(warn.message)
            and "new_func" in str(warn.message)
            for warn in w
        ), "DeprecationWarning with correct content not found"


# 3. Warnings visible during test runs (pytest will fail if not visible)
def test_deprecation_warning_visible():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        old_func(2)
        assert any(issubclass(warn.category, DeprecationWarning) for warn in w)


# 4. Can be silenced with standard Python warning filters
def test_deprecation_warning_can_be_silenced():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("ignore", DeprecationWarning)
        old_func(3)
        assert not any(issubclass(warn.category, DeprecationWarning) for warn in w)
