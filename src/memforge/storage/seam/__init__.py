"""Pluggable storage seam: caller context, protocols, and concrete impls.

Each store is bound to one datastore at construction. The seam is the
boundary a different storage backend plugs in behind.
"""

from __future__ import annotations

from memforge.storage.seam.context import AccessScope, LOCAL_DEV_USER_ID
from memforge.storage.seam.protocols import (
    KeywordSearch,
    RelationalStore,
    VectorStore,
)

__all__ = [
    "AccessScope",
    "LOCAL_DEV_USER_ID",
    "KeywordSearch",
    "RelationalStore",
    "VectorStore",
]
