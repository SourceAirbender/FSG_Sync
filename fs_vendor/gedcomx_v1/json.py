# -*- coding: utf-8 -*-
#
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

from __future__ import annotations

from .dateformal import DateFormal  # kept because other classes may use it
from ._utilities import all_annotations


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------
def serialize_json(obj):
    """
    Return a JSON-serializable representation of `obj`.
    """
    # Object-provided custom serialization
    if hasattr(obj, "serialize_json"):
        return obj.serialize_json()
    if hasattr(obj, "to_string"):
        # Many types (e.g., DateFormal) expose a text form
        return obj.to_string()

    ko = obj.__class__.__name__

    # Primitive passthrough
    if ko in ("bool", "str", "int", "float"):
        return obj

    # Collections
    if ko in ("set", "list"):
        if len(obj) == 0:
            return
        return [serialize_json(o) for o in obj]

    if ko == "dict":
        if len(obj) == 0:
            return
        x = {}
        for k, v in obj.items():
            json_k = serialize_json(k)
            json_v = serialize_json(v)
            if json_v:
                x[json_k] = json_v
        return x

    # Generic object: collect public attributes
    ser = {}
    for a in dir(obj):
        if a.startswith("_"):
            continue
        attr = getattr(obj, a)
        if callable(attr):
            continue
        # normalize attribute name to JSON key
        key = a.replace("_", "-")
        ka = attr.__class__.__name__
        if ka == "NoneType":
            continue
        if ka in ("set", "list", "str", "dict") and len(attr) == 0:
            continue
        ser[key] = serialize_json(attr)
    return ser


# ---------------------------------------------------------------------------
# Helpers for deserialization
# ---------------------------------------------------------------------------
def _add_class(klass, data, parent):
    """
    Create or reuse an instance of `klass` from the JSON `data`,
    using annotations to determine id/index behavior.
    """
    has_id = all_annotations(klass).get("id")
    has_index = all_annotations(klass).get("_index") 
    if klass.__name__ == "str":
        return str(data)

    if has_id and not has_index:
        obj = None
        if klass.__name__ == "SourceReference":
            set_name = "sources"
        else:
            set_name = klass.__name__.lower() + "s"
        if hasattr(parent, set_name) and data.get("id"):
            wanted = data.get("id")
            for f in getattr(parent, set_name):
                if getattr(f, "id", None) == wanted:
                    obj = f
                    break
        if not obj:
            obj = klass()
    elif has_id and has_index and data.get("id") in getattr(klass, "_index", {}):
        obj = klass._index[data.get("id")]
    elif has_id and has_index and data.get("id"):
        obj = klass(id=data.get("id"))
    else:
        obj = klass()

    deserialize_json(obj, data)

    if has_id and has_index and data.get("id"):
        klass._index[data["id"]] = obj
    return obj


# ---------------------------------------------------------------------------
# Deserializer
# ---------------------------------------------------------------------------
def deserialize_json(obj, data, required: bool = False):
    """
    Populate `obj` from JSON `data`.

    Args:
        obj: existing object to fill
        data: JSON/dict structure
        required: if True, skip object-provided hooks and do raw mapping
    """
    # Object-provided custom deserialization
    if not required:
        if hasattr(obj, "deserialize_json"):
            obj.deserialize_json(data)
            return
        if hasattr(obj, "parse"):  # e.g., DateFormal.parse
            obj.parse(data)
            return

    if not data:
        return

    if obj.__class__.__name__ == "str":
        obj = data
        return

    if obj.__class__.__name__ == "set":
        for v in data:
            obj.add(v)
        return

    for k in data:
        # attribute name in annotations uses underscores
        if k[:38] == "{http://www.w3.org/XML/1998/namespace}":
            attr_name = k[38:].replace("-", "_")
        else:
            attr_name = k.replace("-", "_")

        ann = all_annotations(obj.__class__).get(attr_name)
        kn = str(ann)

        if kn == "<class 'bool'>":
            if data[k] == "true":
                setattr(obj, attr_name, True)
            elif data[k] == "false":
                setattr(obj, attr_name, False)
            else:
                setattr(obj, attr_name, data[k])

        elif kn in ("<class 'bool'>", "<class 'str'>", "<class 'int'>", "<class 'float'>", "<class 'None'>"):
            setattr(obj, attr_name, data[k])

        elif kn == "<class 'set'>":
            attr = getattr(obj, attr_name, None) or set()
            # data[k] is expected to be an iterable of primitives
            try:
                attr.update(data[k])
            except TypeError:
                # be forgiving if a single primitive sneaks in
                attr.add(data[k])
            setattr(obj, attr_name, attr)

        elif kn == "<class 'list'>":
            attr = getattr(obj, attr_name, None) or list()
            # preserve original behavior; some classes may override list semantics
            attr.update(data[k])  # type: ignore[attr-defined]
            setattr(obj, attr_name, attr)

        elif kn == "<class 'dict'>":
            attr = getattr(obj, attr_name, None) or dict()
            attr.update(data[k])
            setattr(obj, attr_name, attr)

        elif kn.startswith("<class '"):
            klass = ann
            new_obj = _add_class(klass, data[k], obj)
            if new_obj:
                setattr(obj, attr_name, new_obj)
            else:
                print("deserialize_json:error : k=" + k + "; d[k]=" + str(data[k]))

        elif kn.startswith("set["):
            kn2 = kn[4 : len(kn) - 1]
            if kn2 in ("bool", "str", "int", "float", "None"):
                attr = getattr(obj, attr_name, None) or set()
                try:
                    attr.update(data[k])
                except TypeError:
                    attr.add(data[k])                
                setattr(obj, attr_name, attr)
            else:
                attr = getattr(obj, attr_name, None) or set()
                klass = ann.__args__[0]
                for x in data[k]:
                    new_obj = _add_class(klass, x, obj)
                    if new_obj:
                        found = False
                        if hasattr(klass, "iseq"):
                            for y in attr:
                                if y.iseq(new_obj):
                                    found = True
                                    break
                        if not found:
                            attr.add(new_obj)
                    else:
                        print("deserialize_json:error :  k=" + k + "; x=" + str(x))
                setattr(obj, attr_name, attr)

        elif kn.startswith("dict[str,"):
            klass = ann.__args__[1]
            attr = getattr(obj, attr_name, None) or dict()
            for k2, v in data[k].items():
                # Support dict[str, set] (e.g., identifiers)
                if klass is set:
                    if isinstance(v, (list, tuple, set)):
                        attr[k2] = set(v)
                    else:
                        attr[k2] = {v}
                    continue
                # Normal object/value path
                new_obj = _add_class(klass, v, obj)
                if new_obj is not None:
                    attr[k2] = new_obj
                else:
                    print("deserialize_json:error :   k=" + k + ";k2=" + str(k2) + "; v=" + str(v) + "; klass=" + str(klass))
            setattr(obj, attr_name, attr)        

        else:
            print("Unknown JSON Value: Error: " + obj.__class__.__name__ + ":" + k)

    # Post-process hook
    if not required:
        if hasattr(obj, "post_deserialize"):
            obj.post_deserialize(data)
        elif hasattr(obj, "postmaljsonigi"): 
            obj.postmaljsonigi(data)

def to_string(obj):
    return serialize_json(obj)


def parse(obj, d, nepre: bool = False):
    return deserialize_json(obj, d, required=nepre)
