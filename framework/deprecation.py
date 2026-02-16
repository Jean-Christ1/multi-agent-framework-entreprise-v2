import warnings
from functools import wraps


def deprecated(reason: str, removal_version: str, replacement: str = None):
    """
    Decorator to mark functions/methods as deprecated.

    Usage:
        @deprecated(
            reason="Raw dict returns are being phased out",
            removal_version="0.3.0",
            replacement="Return a DataContract instead"
        )
        def old_method(self):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            msg = f"{func.__name__} is deprecated: {reason}. "
            msg += f"Will be removed in v{removal_version}. "
            if replacement:
                msg += f"Use {replacement} instead."
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator
