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
#
# Small helpers for annotation lookup and instance initialization.

from __future__ import annotations

from collections import ChainMap


def all_annotations(klass) -> ChainMap:
    """
    Return a ChainMap of type annotations for `klass`, including those
    inherited from its MRO. Keys are attribute names; values are types.
    """
    return ChainMap(
        *(k.__annotations__ for k in klass.__mro__ if "__annotations__" in k.__dict__)
    )


def init_class(obj):
    """
    Initialize all annotated attributes of `obj` to sensible defaults:
    - set → empty set()
    - dict → empty dict()
    - set[T] → empty set()
    - dict[K,V] → empty dict()
    - everything else → None
    """
    for attr, decl in all_annotations(obj.__class__).items():
        if decl in (set, dict):
            setattr(obj, attr, decl())
        elif str(decl).startswith("set["):
            setattr(obj, attr, set())
        elif str(decl).startswith("dict["):
            setattr(obj, attr, dict())
        else:
            setattr(obj, attr, None)
