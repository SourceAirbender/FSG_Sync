# Copyright © 2022 Jean Michault

# License: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-

__version__ = "1.1.0" 

from .gedcomx import *
from .json import serialize_json, deserialize_json
from .xml import to_xml, parse_xml, XmlGedcomx
from .fs_session import FsSession

from .vocab import (
    EVENT_TYPES,
    RELATIONSHIP_TYPES,
    FACT_TYPES,
    normalize_type,
    label_for,
    is_event_type,
    is_relationship_type,
)

__all__ = [
    *[name for name in dir() if not name.startswith("_")],
]
