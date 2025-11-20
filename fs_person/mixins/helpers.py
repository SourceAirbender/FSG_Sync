# -*- coding: utf-8 -*-
from __future__ import annotations
import time
from typing import Dict, Optional, List

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.lib import Person

# Plugin deps
import fs_import
import fs_utilities

import gedcomx_v1

from .constants import FS_DIRECT_TAGS, FS_MENTION_ONLY

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


class HelpersMixin:
    def _pretty_tags(self, tags: List[str]) -> str:
        labs = []
        for t in tags:
            try:
                if t.startswith("http://gedcomx.org/"):
                    labs.append(t.split("/")[-1])
                else:
                    labs.append(t)
            except Exception:
                pass
        order = [
            "Birth",
            "Baptism",
            "Christening",
            "Marriage",
            "Divorce",
            "Death",
            "Burial",
            "Gender",
            "Name",
        ]
        labs = sorted(
            set(labs),
            key=lambda x: (order.index(x) if x in order else 99, x),
        )
        return ", ".join(labs)

    def _classify_simple(self, tags: List[str]) -> str:
        if not tags:
            return "Mention"
        if all(t in FS_MENTION_ONLY for t in tags):
            return "Mention"
        if any(t in FS_DIRECT_TAGS for t in tags):
            return "Direct"
        return "Direct"

    def _gather_sr_meta(self, fsid: str) -> Dict[str, dict]:
        self._ensure_sources_cached(fsid)
        fsP = gedcomx_v1.Person._index.get(fsid) or gedcomx_v1.Person()

        meta: Dict[str, dict] = {}

        def add(sr):
            sdid = getattr(sr, "descriptionId", None)
            if not sdid:
                return
            entry = meta.setdefault(
                sdid,
                {"tags": set(), "kind": "Mention", "contributor": "", "modified": ""},
            )
            try:
                for t in getattr(sr, "tags", []) or []:
                    val = getattr(t, "resource", None) or str(t)
                    if val:
                        entry["tags"].add(val)
            except Exception:
                pass
            try:
                attr = getattr(sr, "attribution", None)
                rid = getattr(getattr(attr, "contributor", None), "resourceId", "") if attr else ""
                mod_ms = getattr(attr, "modified", None)
                mod_iso = ""
                if isinstance(mod_ms, (int, float)):
                    mod_iso = time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(mod_ms / 1000.0)
                    )

                def _to_ts(s):
                    try:
                        return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
                    except Exception:
                        return 0

                if _to_ts(mod_iso) >= _to_ts(entry["modified"]):
                    entry["contributor"] = rid or entry["contributor"]
                    entry["modified"] = mod_iso or entry["modified"]
            except Exception:
                pass

        for sr in getattr(fsP, "sources", []) or []:
            add(sr)
        for rel in getattr(fsP, "_spouses", []) or []:
            for sr in getattr(rel, "sources", []) or []:
                add(sr)

        for sdid, e in meta.items():
            tags = list(e["tags"])
            e["kind"] = self._classify_simple(tags)
            e["tags"] = tags
        return meta

    def _label_for_person_id(self, pid: str) -> str:
        try:
            self._ensure_person_cached(pid, with_relatives=False)
            p = gedcomx_v1.Person._index.get(pid)
            if p:
                nm = p.preferred_name()
                return f"{nm.akSurname()}, {nm.akGiven()} [{pid}]"
        except Exception:
            pass
        return f"[{pid}]"

    def _find_person_by_fsid(self, fsid: str) -> Optional[Person]:
        for h in self.dbstate.db.iter_person_handles():
            p = self.dbstate.db.get_person_from_handle(h)
            if fs_utilities.get_fsftid(p) == fsid:
                return p
        return None
