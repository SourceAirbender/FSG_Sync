from __future__ import annotations

from .fsg_sync import FSG_Sync

try:
    from .mixins.constants import (
        has_minibrowser,
        APP_KEY, REDIRECT, FS_DIRECT_TAGS, FS_MENTION_ONLY,
    )
except Exception:
    pass

__all__ = ["FSG_Sync"]

