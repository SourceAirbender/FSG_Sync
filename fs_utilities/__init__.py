from __future__ import annotations

from .index import (
    build_fs_index,
    FS_INDEX_PEOPLE,
    FS_INDEX_PLACES,
)
from .dates import (
    fs_date_to_gramps_date,
    gramps_date_to_formal,
)
from .attributes import (
    get_fsftid,
    get_internet_address,
)
from .events import (
    get_fs_fact,
    get_gramps_event,
)
from .linking import (
    link_gramps_fs_id,
)

get_url = get_internet_address

__all__ = [
    "build_fs_index",
    "fs_date_to_gramps_date",
    "gramps_date_to_formal",
    "get_fsftid",
    "get_internet_address",
    "get_fs_fact",
    "get_gramps_event",
    "link_gramps_fs_id",
    "FS_INDEX_PEOPLE",
    "FS_INDEX_PLACES",
    "get_url",
]
