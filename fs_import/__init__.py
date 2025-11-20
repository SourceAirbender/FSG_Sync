from __future__ import annotations

from gramps.gen.const import GRAMPS_LOCALE as glocale

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

import gedcomx_v1  # vendored gedcomx_v1 w/ a few changes

from .tool import FSImportTool
from .options import FSImportOptions
from .importer import FSToGrampsImporter
from .places import create_place, add_place, get_place_by_id
from .notes import add_note
from .events import add_event, update_event
from .names import add_name, add_names
from .sources import fetch_source_dates, add_source, IntermediateSource

# Classes
FSImportTool
FSImportOptions
FSToGrampsImporter
IntermediateSource

# Functions
create_place
add_place
get_place_by_id
add_note
add_event
update_event
add_name
add_names
fetch_source_dates
add_source

__all__ = [
    "FSImportTool",
    "FSImportOptions",
    "FSToGrampsImporter",
    "create_place",
    "add_place",
    "get_place_by_id",
    "add_note",
    "add_event",
    "update_event",
    "add_name",
    "add_names",
    "fetch_source_dates",
    "add_source",
    "IntermediateSource",
]
