"""
Compatibility utilities for JAF Framework.

Provides version checking and compatibility helpers for downstream projects.
"""

from framework._version import __version__


def require_version(min_version: str) -> None:
    """
    Raise if framework version is below minimum.

    This utility allows downstream projects to enforce minimum version
    requirements for JAF Framework.

    Args:
        min_version: Minimum required version string (e.g., "0.2.0")

    Raises:
        RuntimeError: If installed JAF version is below minimum required

    Example:
        >>> from framework.compat import require_version
        >>> require_version("0.2.0")  # Raises if JAF < 0.2.0
    """
    from packaging.version import Version

    if Version(__version__) < Version(min_version):
        raise RuntimeError(
            f"This project requires jaf-framework >= {min_version}, "
            f"but {__version__} is installed"
        )
