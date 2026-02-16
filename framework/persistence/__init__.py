"""
Persistence module for JAF framework.

Provides database connection management and process repository.
"""

from framework.persistence.models import ProcessStatus
from framework.persistence.schemas import ProcessSchema

__all__ = [
    "ProcessStatus",
    "ProcessSchema",
]
