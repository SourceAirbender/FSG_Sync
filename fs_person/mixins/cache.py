# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import time
import email.utils
from typing import Optional, Tuple

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale

# Plugin deps
import tree

# vendored gedcomx_v1
import gedcomx_v1

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


class _FsCacheEntry:
    """In-memory metadata for an FSID cached on disk."""
    def __init__(self, etag: Optional[str], last_mod: Optional[int]):
        self.etag = etag
        self.last_modified = last_mod
        self.loaded_notes = False
        self.loaded_sources = False


class _FsCache:
    """Simple JSON-on-disk cache: one file per FSID under <base>/fs_cache/."""
    def __init__(self, base_dir: str):
        self.mem: dict[str, _FsCacheEntry] = {}
        self.base_dir = os.path.join(base_dir, "fs_cache")
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, fsid: str) -> str:
        return os.path.join(self.base_dir, f"{fsid}.json")

    def get_meta(self, fsid: str) -> Optional[_FsCacheEntry]:
        return self.mem.get(fsid)

    def set_meta(self, fsid: str, etag: Optional[str], last_mod: Optional[int]):
        entry = self.mem.get(fsid) or _FsCacheEntry(etag, last_mod)
        entry.etag = etag
        entry.last_modified = last_mod
        self.mem[fsid] = entry

    def mark_loaded(self, fsid: str, *, notes: bool = False, sources: bool = False):
        e = self.mem.get(fsid)
        if not e:
            e = _FsCacheEntry(None, None)
            self.mem[fsid] = e
        if notes:
            e.loaded_notes = True
        if sources:
            e.loaded_sources = True

    def write_json(self, fsid: str, data: dict, etag: Optional[str], last_mod: Optional[int]):
        """
        Atomically write the cache blob to disk (fsync + replace).
        File layout:
          {
            "etag": "...",
            "last_modified": 1690000000,
            "person": { "persons": [ <GedcomX Person JSON> ] }
          }
        """
        path = self._path(fsid)
        tmp_path = path + ".tmp"
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"etag": etag, "last_modified": last_mod, "person": data},
                    f,
                    ensure_ascii=False,
                )
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception as e:
            # Keep logs minimal; avoid breaking UI flows
            print(f"[FS Cache] failed to write {fsid}: {e}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def read_json(self, fsid: str) -> Optional[Tuple[dict, Optional[str], Optional[int]]]:
        """
        Read cache file for FSID.
        Returns: (person_blob, etag, last_modified) or None on error/missing.
        """
        p = self._path(fsid)
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                blob = json.load(f)
            return blob.get("person"), blob.get("etag"), blob.get("last_modified")
        except Exception:
            return None

    def clear(self) -> None:
        """
        Clear all cached FS JSON files on disk and reset in-memory metadata.
        """
        self.mem.clear()
        try:
            for fname in os.listdir(self.base_dir):
                if not fname.endswith(".json"):
                    continue
                try:
                    os.remove(os.path.join(self.base_dir, fname))
                except Exception:
                    # Don't hard-fail if one file can't be deleted.
                    pass
        except Exception as e:
            print(f"[FS Cache] failed to clear cache dir {self.base_dir}: {e}")


class CacheMixin:
    """
    Mix-in that ensures a person (and optionally relatives) is available
    in the in-memory Tree, using a disk cache to avoid re-downloading.
    """

    def _ensure_person_cached(
        self,
        fsid: str,
        *,
        with_relatives: bool,
        force: bool = False,
    ) -> gedcomx_v1.Person:
        etag: Optional[str] = None
        last_mod: Optional[int] = None

        # If we don't already have the person (or force refresh), probe headers.
        if force or (fsid not in self.__class__.fs_Tree._persons):
            r = tree._fs_session.head_url(f"/platform/tree/persons/{fsid}")
            if r and r.status_code == 301 and "X-Entity-Forwarded-Id" in r.headers:
                fsid = r.headers["X-Entity-Forwarded-Id"]
            if r:
                etag = r.headers.get("Etag")
                lm = r.headers.get("Last-Modified")
                last_mod = int(time.mktime(email.utils.parsedate(lm))) if lm else None

        # Compare against in-memory metadata
        ce = self._cache.get_meta(fsid) if getattr(self.__class__, "_cache", None) else None
        up_to_date = (not force) and ce and (
            (ce.etag and etag and ce.etag == etag)
            or (ce.last_modified and last_mod and ce.last_modified == last_mod)
        )

        if not up_to_date:
            # Try disk cache first
            disk = None if force or not getattr(self.__class__, "_cache", None) else self._cache.read_json(fsid)
            if disk and (etag is None or disk[1] == etag) and (last_mod is None or disk[2] == last_mod):
                try:
                    # disk[0] := {"persons":[ <person json> ]}
                    gedcomx_v1.deserialize_json(self.__class__.fs_Tree, disk[0])
                except Exception as e:
                    print(f"[FS Cache] deserialize (disk) failed for {fsid}: {e}")
                p = gedcomx_v1.Person._index.get(fsid)
                if p:
                    p._etag = disk[1]
                    p._last_modified = disk[2]
                    self.__class__.fs_Tree._persons[fsid] = p
                    self._cache.set_meta(fsid, disk[1], disk[2])

            # If still missing, fetch and write cache
            if fsid not in self.__class__.fs_Tree._persons:
                self.__class__.fs_Tree.add_persons([fsid])
                p = gedcomx_v1.Person._index.get(fsid)
                if p:
                    self.__class__.fs_Tree._persons[fsid] = p
                    if getattr(self.__class__, "_cache", None):
                        self._cache.set_meta(
                            fsid,
                            getattr(p, "_etag", None),
                            getattr(p, "_last_modified", None),
                        )
                        # Serialize just the person (as a one-person GedcomX blob)
                        try:
                            full_tree = gedcomx_v1.serialize_json(self.__class__.fs_Tree)
                            persons = []
                            for pj in (full_tree.get("persons") or []):
                                pid = pj.get("id") or pj.get("@id")
                                if pid == fsid:
                                    persons = [pj]
                                    break
                            if not persons and full_tree.get("persons"):
                                persons = [full_tree["persons"][0]]
                            person_only = {"persons": persons}
                            self._cache.write_json(
                                fsid,
                                person_only,
                                getattr(p, "_etag", None),
                                getattr(p, "_last_modified", None),
                            )
                        except Exception as e:
                            print(f"[FS Cache] serialize/write failed for {fsid}: {e}")

        if with_relatives:
            self.__class__.fs_Tree.add_spouses({fsid})
            self.__class__.fs_Tree.add_children({fsid})
            self.__class__.fs_Tree.add_parents({fsid})

        return gedcomx_v1.Person._index.get(fsid) or gedcomx_v1.Person()

    def _ensure_notes_cached(self, fsid: str) -> None:
        _get_json = getattr(tree._fs_session, "get_jsonurl", None) or getattr(
            tree._fs_session, "get_json", None
        )
        if _get_json:
            _get_json(f"/platform/tree/persons/{fsid}/notes")

        self.__class__.fs_Tree.add_spouses({fsid})
        p = gedcomx_v1.Person._index.get(fsid)
        if p:
            for rel in getattr(p, "_spouses", []) or []:
                if _get_json:
                    _get_json(f"/platform/tree/couple-relationships/{rel.id}/notes")

        if getattr(self.__class__, "_cache", None):
            self._cache.mark_loaded(fsid, notes=True)

    def _ensure_sources_cached(self, fsid: str) -> None:
        _get_json = getattr(tree._fs_session, "get_jsonurl", None) or getattr(
            tree._fs_session, "get_json", None
        )
        if _get_json:
            _get_json(f"/platform/tree/persons/{fsid}/sources")

        self.__class__.fs_Tree.add_spouses({fsid})
        p = gedcomx_v1.Person._index.get(fsid)
        if p:
            for rel in getattr(p, "_spouses", []) or []:
                try:
                    if _get_json:
                        _get_json(f"/platform/tree/couple-relationships/{rel.id}/sources")
                except Exception:
                    # Swallow occasional endpoint quirks without breaking the UI
                    pass

        if getattr(self.__class__, "_cache", None):
            self._cache.mark_loaded(fsid, sources=True)

    def _clear_fs_cache(self) -> None:
        """
        Clear disk + in-memory FS compare cache.
        (Used by the UI 'Clear cache' button.)
        """
        if getattr(self.__class__, "_cache", None):
            self.__class__._cache.clear()
