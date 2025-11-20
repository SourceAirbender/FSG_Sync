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
#
# XML ⇄ object (GedcomX) parser/serializer.
# Hardened: silence "unknown tag/class" chatter unless VERBOSE=True.

from __future__ import annotations

import xml.etree.ElementTree as ET

from gedcomx_v1.gedcomx import Gedcomx
from gedcomx_v1.json import deserialize_json, _add_class
from gedcomx_v1._utilities import all_annotations
from gedcomx_v1.dateformal import SimpleDate

VERBOSE = False


class XmlHandler:
    """
    Streaming XML → object mapper. It walks the XML tree and, based on the
    annotations of the parent object, creates/attaches instances for child
    nodes. For sets/dicts, it accumulates items; for scalars, it assigns.
    """

    def __init__(self):
        self._depth = 0
        self._obj = {1: self}
        self._rel = {1: None}
        self._attr = {1: None}
        self._keys = {1: "gedcomx"}
        self._klass = {1: self.__class__.__name__}
        self._is_set = {1: False}
        self._is_dict = {1: False}

    def start(self, tag, attrib):
        parent = self._obj.get(self._depth)
        self._depth += 1

        if self._depth == 1:
            # The root element's attributes initialize “self” (target object)
            deserialize_json(self, attrib)
            return

        # Namespace → local name
        if tag.startswith("{http://gedcomx.org/v1/}"):
            attr_name = tag[24:]
        elif tag.startswith("{http://familysearch.org/v1/}"):
            attr_name = tag[29:]
        else:
            if VERBOSE:
                print("WARNING: unknown tag:", tag)
            return

        attr_name = attr_name.replace("-", "_")
        if VERBOSE:
            print(f"  start:{attr_name} ; {attrib}")

        if attr_name == "br":
            self._obj[self._depth - 1] += "\n"
            return
        if attr_name == "space":
            self._obj[self._depth - 1] += " "
            return

        annot = all_annotations(parent.__class__).get(attr_name)
        annot_str = str(annot)

        if annot:
            # Direct attribute of the parent (scalar, object, or container)
            if VERBOSE:
                print("  annotation:", annot)

            klass = annot
            if annot_str.startswith("set["):
                # Container-of-items on the parent
                self._is_set[self._depth] = True
                self._is_dict[self._depth] = False

                # Element type inside the set
                inner_decl = annot_str[4 : len(annot_str) - 1]
                if inner_decl in ("bool", "str", "int", "float", "None"):
                    current = getattr(parent, attr_name, None) or set()
                    klass = annot.__args__[0]
                    item = klass()
                    if VERBOSE:
                        print("  primitive set; attrib=", attrib)
                    deserialize_json(item, attrib)
                    current.add(item)
                    setattr(parent, attr_name, current)
                else:
                    current = getattr(parent, attr_name, None) or set()
                    klass = annot.__args__[0]
                    item = _add_class(klass, attrib, parent)
                    current.add(item)
                    setattr(parent, attr_name, current)

                    self._keys[self._depth] = attr_name
                    self._obj[self._depth] = item
                    self._klass[self._depth] = klass
            else:
                # Scalar or nested object
                obj = getattr(parent, attr_name, None) or klass()
                if VERBOSE:
                    print("  simple:attrib=", attrib)
                deserialize_json(obj, attrib)
                setattr(parent, attr_name, obj)

                self._keys[self._depth] = attr_name
                self._obj[self._depth] = obj
                self._klass[self._depth] = annot
                self._is_set[self._depth] = False
                self._is_dict[self._depth] = False
            return

        # Not a direct attribute — try plural container on the parent
        if attr_name.startswith("family"):
            attr_name = "families" + attr_name[6:]
        elif attr_name == "child":
            attr_name = "children"
        else:
            attr_name = attr_name + "s"

        self._keys[self._depth] = attr_name
        annot = all_annotations(parent.__class__).get(attr_name)
        if not annot:
            if VERBOSE:
                print(
                    "parse-xml:WARNING:",
                    f"depth={self._depth} xml-unknown element: {parent.__class__.__name__}.{tag} attr={attr_name}",
                )
            return

        annot_s = str(annot)
        self._klass[self._depth] = annot

        if annot_s.startswith("set["):
            self._is_set[self._depth] = True
            klass = annot.__args__[0]
            if VERBOSE:
                print("   set[:", annot_s, "; attrib=", attrib)
            current = getattr(parent, attr_name, None) or set()
            obj = _add_class(klass, attrib, parent)
            current.add(obj)
            setattr(parent, attr_name, current)
            self._attr[self._depth] = current
        elif (annot_s.startswith("dict[str,") and getattr(annot, "__args__", [None, None])[1].__name__ == "Link"):
            # Special case: dict[str, Link] keyed by “rel”
            self._is_dict[self._depth] = True
            klass = annot.__args__[1]
            if VERBOSE:
                print("   dict[:", annot_s, "; attrib=", attrib)
            current = getattr(parent, attr_name, None) or dict()
            rel = attrib.pop("rel")
            obj = _add_class(klass, attrib, parent)
            self._rel[self._depth] = rel
            self._attr[self._depth] = current
            current[rel] = obj
            setattr(parent, attr_name, current)
        elif annot_s.startswith("dict[str,"):
            # Generic dict[str, X], keyed by “type”
            self._is_dict[self._depth] = True
            klass = annot.__args__[1]
            if VERBOSE:
                print("   dict[:", annot_s, "; attrib=", attrib)
            current = getattr(parent, attr_name, None) or dict()
            key = attrib.pop("type")
            obj = _add_class(klass, attrib, parent)
            self._rel[self._depth] = key
            self._attr[self._depth] = current
            current[key] = obj
            setattr(parent, attr_name, current)
        else:
            if VERBOSE:
                print(
                    "WARNING: unknown class:",
                    f"{parent.__class__.__name__}:{attr_name} - {annot_s}",
                )
        self._obj[self._depth] = obj  # type: ignore[name-defined]

    # Called for each closing tag
    def end(self, tag):
        obj = self._obj.get(self._depth)
        key = self._keys.get(self._depth)
        is_set = self._is_set.get(self._depth)
        is_dict = self._is_dict.get(self._depth)

        self._depth -= 1
        parent = self._obj.get(self._depth)
        if VERBOSE:
            print("  end:", key, ";", tag)

        if self._depth >= 1:
            if is_set:
                pass  # already added to the set
            elif is_dict:
                pass  # already attached via dict key
            else:
                if obj is not None:
                    setattr(parent, key, obj)
            # clear level
            self._obj[self._depth + 1] = None
            self._keys[self._depth + 1] = ""
            self._is_set[self._depth + 1] = False
            self._is_dict[self._depth + 1] = False

    # Character data for current node
    def data(self, data):
        if not data or data.isspace():
            return

        obj = self._obj.get(self._depth)
        key = self._keys.get(self._depth)
        klass = self._klass.get(self._depth)

        if VERBOSE:
            print("    data:", key, ";", data)

        # Normalize “modified” as epoch ms using SimpleDate
        if key == "modified":
            sd = SimpleDate(data)
            data = sd.int()

        if obj is not None and klass and (klass.__name__ == "float"):
            self._obj[self._depth] = float(data)
        elif obj is not None and klass and (klass.__name__ == "bool"):
            if data == "true":
                self._obj[self._depth] = True
            elif data == "false":
                self._obj[self._depth] = False
            else:
                self._obj[self._depth] = str(data)
        elif obj is not None and klass and klass.__name__ == "int":
            self._obj[self._depth] = int(data)
        elif obj is not None and klass and klass.__name__ == "str":
            # concatenate text chunks
            cur = getattr(self._obj, self._depth, "") if isinstance(self._obj.get(self._depth), str) else ""
            self._obj[self._depth] = (cur + data)
        elif obj is not None and klass and klass.__name__ == "DateFormal":
            # Delegate parsing of the formal date string
            deserialize_json(obj, data)
        elif obj is not None and obj.__class__.__name__ == "set":
            obj.add(data)
        elif obj is not None and klass and klass.__name__ == "set" and obj.__class__.__name__ == "TextValue":
            obj.value = data
        elif obj is not None and str(klass).startswith("dict[str,"):
            current = self._attr.get(self._depth)
            rel = self._rel.get(self._depth)
            current[rel] = data
        elif obj is not None and klass and klass.__name__ == "set":
            obj.value = data
        elif obj is not None and klass and klass.__name__ == "TextValue":
            obj.value = data
        else:
            if VERBOSE:
                print(
                    "parse-xml:WARNING:",
                    f"{self._depth}-data: key={key} ; {data} ; klass={klass} - {obj}",
                )
                if klass:
                    print("                :   klass.__name__=", klass.__name__)

    def close(self):
        # ET.XMLParser(target=...) requires a close() even if it does nothing
        pass


def parse_xml(target_obj, xml_text, required: bool = False):
    """
    Parse an XML string into `target_obj` (a GedcomX-derived object),
    mutating it in-place using the handler above.
    """
    parser = ET.XMLParser(target=target_obj)
    parser.feed(xml_text)
    parser.close()


def to_xml(obj):
    """
    Build an ElementTree for `obj` (GedcomX-derived) by walking its public
    attributes. Sets and dicts expand into repeated child elements.
    """
    root = ET.Element(obj.__class__.__name__.lower())
    root.attrib["xmlns"] = "http://gedcomx.org/v1/"
    root.attrib["xmlns:fs"] = "http://familysearch.org/v1/"
    root.attrib["xmlns:atom"] = "http://www.w3.org/2005/Atom"
    _emit_xml(root, obj)
    return ET.ElementTree(root)


def _emit_xml(el, obj):
    """
    Recursive helper for `to_xml`: materialize all public attributes.
    """
    for a in dir(obj):
        if a.startswith("_"):
            continue
        attr = getattr(obj, a)
        if callable(attr):
            continue

        name = a
        # FS-specific renames to match expected element names
        if name == "childAndParentsRelationships":
            name = "fs:childAndParentsRelationships"
        if name == "child":
            name = "fs:child"
        if name == "parent1":
            name = "fs:parent1"
        if name == "parent2":
            name = "fs:parent2"
        if name == "parent1Facts":
            name = "fs:parent1Facts"
        if name == "parent2Facts":
            name = "fs:parent2Facts"

        ka = attr.__class__.__name__
        if ka == "NoneType":
            continue
        if ka in ("set", "list", "str", "dict") and len(attr) == 0:
            continue

        if ka in ("str", "int", "bool", "float"):
            el.attrib[name] = str(attr)

        elif ka == "set":
            # Element name is the singular form: “facts” -> “fact”
            child_name = name[:-1] if name.endswith("s") else name
            for x in attr:
                sub = ET.SubElement(el, child_name)
                _emit_xml(sub, x)

        elif ka == "dict":
            child_name = name[:-1] if name.endswith("s") else name
            for k, v in attr.items():
                sub = ET.SubElement(el, child_name)
                if child_name == "link":
                    sub.attrib["rel"] = k
                elif child_name == "identifier":
                    sub.attrib["type"] = k
                    if v.__class__.__name__ == "set":
                        first = True
                        sub.text = ""
                        for x in v:
                            if first:
                                first = False
                            else:
                                sub.text += ","
                            sub.text += x
                    else:
                        sub.text = v
                else:
                    sub.attrib["type"] = k
                    if VERBOSE:
                        print("unknown dict kind:", child_name)
                _emit_xml(sub, v)

        else:
            sub = ET.SubElement(el, name)
            _emit_xml(sub, attr)


class XmlGedcomx(XmlHandler, Gedcomx):
    """
    Concrete ElementTree target that is also a Gedcomx root object.
    Useful for one-shot parse into a full graph:
        gx = XmlGedcomx()
        parse_xml(gx, xml_str)
    """
    pass
