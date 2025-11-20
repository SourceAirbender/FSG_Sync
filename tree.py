# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Iterable, Set

import asyncio
import email.utils
import time

import gedcomx_v1
from gedcomx_v1.dateformal import DateFormal

from constants import MAX_PERSONS  

# Single session shared by all Tree instances
_fs_session = None 


class Tree(gedcomx_v1.Gedcomx):
    """
    Thin helper around gedcomx_v1 to batch-load people and their relations.
    """

    def __init__(self):
        gedcomx_v1._utilities.init_class(self)
        self._fam = dict()
        self._places = dict()
        self._persons: dict[str, gedcomx_v1.Person] = {}
        self._getsources = True
        self._sources = dict()
        self._notes = []

    # ---- Person loading ----------------------------------------------------

    def add_person(self, fsid: str) -> None:
        """
        Load a single person from FamilySearch into this Tree, cache headers.
        """
        global _fs_session
        if not _fs_session:
            return

        url = f"/platform/tree/persons/{fsid}"
        r = _fs_session.get_url(url)
        if not r:
            return

        try:
            data = r.json()
        except Exception as e:
            print("WARNING: corrupted response from %s, error: %s" % (url, e))
            try:
                print(r.content)
            except Exception:
                pass
            data = None

        if not data:
            return

        # Materialize into gedcomx_v1's global indices
        gedcomx_v1.deserialize_json(self, data)

        try:
            fs_person = gedcomx_v1.Person._index[fsid]
        except KeyError:
            return

        # Preserve server cache validators for smarter reloads downstream
        if "Last-Modified" in r.headers:
            try:
                fs_person._last_modified = int(
                    time.mktime(email.utils.parsedate(r.headers["Last-Modified"]))
                )
            except Exception:
                pass
        if "Etag" in r.headers:
            fs_person._etag = r.headers["Etag"]

        self._persons[fsid] = fs_person

    def add_persons(self, fids: Iterable[str]) -> None:
        """
        Concurrently add multiple individuals by FSID.
        """

        async def _load_many(loop, ids: Iterable[str]):
            tasks = set()
            for fid in ids:
                if fid not in self._persons:
                    tasks.add(loop.run_in_executor(None, self.add_person, fid))
            for t in tasks:
                await t

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_load_many(loop, fids))

        # Ensure local dict mirrors gedcomx_v1 index for these ids
        for fid in fids:
            if fid in gedcomx_v1.Person._index:
                self._persons[fid] = gedcomx_v1.Person._index[fid]

    # ---- Relationship expansion -------------------------------------------

    def add_parents(self, fids: Set[str]) -> Set[str]:
        """
        Ensure parents of the given FSIDs are loaded; return the set of new IDs.
        """
        rels: Set[str] = set()
        for fid in (fids & set(self._persons.keys())):
            p = self._persons[fid]
            for rel in getattr(p, "_parents", []) or []:
                if rel.person1:
                    rels.add(rel.person1.resourceId)
                if rel.person2:
                    rels.add(rel.person2.resourceId)
            for cp in getattr(p, "_parentsCP", []) or []:
                if cp.parent1:
                    rels.add(cp.parent1.resourceId)
                if cp.parent2:
                    rels.add(cp.parent2.resourceId)

        rels.difference_update(fids)
        self.add_persons(rels)
        return set(filter(None, rels))

    def add_spouses(self, fids: Set[str]) -> Set[str]:
        """
        Ensure spouses of the given FSIDs are loaded; return the set of new IDs.
        """
        rels: Set[str] = set()
        for fid in (fids & set(self._persons.keys())):
            p = self._persons[fid]
            if getattr(p, "_spouses", None):
                for rel in p._spouses:
                    if rel.person1:
                        rels.add(rel.person1.resourceId)
                    if rel.person2:
                        rels.add(rel.person2.resourceId)

        rels.difference_update(fids)
        self.add_persons(rels)
        return set(filter(None, rels))

    def add_children(self, fids: Set[str]) -> Set[str]:
        """
        Ensure children of the given FSIDs are loaded; return the set of new IDs.
        """
        rels: Set[str] = set()
        for fid in (fids & set(self._persons.keys())):
            p = self._persons[fid]
            if getattr(p, "_children", None):
                for rel in p._children:
                    if getattr(rel, "person1", None):
                        rels.add(rel.person1.resourceId)
                    if getattr(rel, "person2", None):
                        rels.add(rel.person2.resourceId)

        rels.difference_update(fids)
        self.add_persons(rels)
        return set(filter(None, rels))


__all__ = ["Tree", "_fs_session", "DateFormal"]
