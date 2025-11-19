from __future__ import annotations

import logging
import email.utils
import time

import tree
import fs_utilities
import FSG_Sync
import datab_familysearch

from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.lib import Person, EventType

from .comparators import (
    compare_gender,
    compare_names,
    compare_fact,
    compare_parents,
    compare_spouses,
    compare_other_facts,
)

logger = logging.getLogger(__name__)

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


def compare_fs_to_gramps(fs_person, gr_person: Person, db, model=None, dupdoc=False):
    """
    Compare a FamilySearch person vs a Gramps person and (optionally) populate
    a GTK model with color-coded comparison rows.

    This function also updates FS status bookkeeping (FSStatusDB) for the
    Gramps person and optionally checks for FS duplicates/documents.
    """
    db_state = datab_familysearch.FSStatusDB(db, gr_person.handle)
    db_state.get()

    # Skip if nothing changed since last run
    if (
        model is None
        and hasattr(fs_person, "_datmod")
        and db_state.status_ts > fs_person._datmod
        and db_state.status_ts > gr_person.change
    ):
        return

    if fs_person.id:
        db_state.fsid = fs_person.id

    FS_Family = FS_Essentials = FS_Facts = FS_Parents = FS_Dup = FS_Dok = False

    tag_fs_dok = db.get_tag_from_name("FS_Dok")
    if tag_fs_dok and tag_fs_dok.handle in gr_person.tag_list:
        FS_Dok = True
    tag_fs_dup = db.get_tag_from_name("FS_Dup")
    if tag_fs_dup and tag_fs_dup.handle in gr_person.tag_list:
        FS_Dup = True

    # Core comparisons
    rows = []

    row = compare_gender(gr_person, fs_person)
    if row:
        rows.append(row)
        if row[0] != "green":
            FS_Essentials = True

    name_rows = compare_names(gr_person, fs_person)
    if name_rows:
        if name_rows[0][0] != "green":
            FS_Essentials = True
        rows.append(name_rows.pop(0))

    row = compare_fact(db, gr_person, fs_person, EventType.BIRTH, "http://gedcomx.org/Birth")
    if row:
        rows.append(row)
        if row[0] != "green":
            FS_Essentials = True

    row = compare_fact(db, gr_person, fs_person, EventType.BAPTISM, "http://gedcomx.org/Baptism")
    if row:
        rows.append(row)
        if row[0] != "green":
            FS_Essentials = True

    row = compare_fact(db, gr_person, fs_person, EventType.DEATH, "http://gedcomx.org/Death")
    if row:
        rows.append(row)
        if row[0] != "green":
            FS_Essentials = True

    row = compare_fact(db, gr_person, fs_person, EventType.BURIAL, "http://gedcomx.org/Burial")
    if row:
        rows.append(row)
        if row[0] != "green":
            FS_Essentials = True

    col_fs = (
        _("Not connected to FamilySearch")
        if not FSG_Sync.FSG_Sync.fs_Tree
        else "===================="
    )

    # Essentials section
    if model and rows:
        if not FSG_Sync.FSG_Sync.fs_Tree:
            es_id = model.add(
                [
                    "white",
                    _("Essentials"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "EssentialsKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        elif FS_Essentials:
            es_id = model.add(
                [
                    "red",
                    _("Essentials"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "EssentialsKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        else:
            es_id = model.add(
                [
                    "green",
                    _("Essentials"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "EssentialsKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        for line in rows:
            model.add(line, node=es_id)

    # Other names
    if name_rows and model:
        any_non_green = any(line[0] != "green" for line in name_rows)
        if not FSG_Sync.FSG_Sync.fs_Tree:
            nm_id = model.add(
                [
                    "white",
                    _("Other names"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "OtherNamesKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        elif any_non_green:
            nm_id = model.add(
                [
                    "red",
                    _("Other names"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "OtherNamesKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        else:
            nm_id = model.add(
                [
                    "green",
                    _("Other names"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "OtherNamesKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        for line in name_rows:
            model.add(line, node=nm_id)

    # Parents
    parent_rows = compare_parents(db, gr_person, fs_person)
    FS_Parents = any(line[0] != "green" for line in parent_rows)
    if model and parent_rows:
        if not FSG_Sync.FSG_Sync.fs_Tree:
            pr_id = model.add(
                [
                    "white",
                    _("Parents"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "ParentsKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        elif FS_Parents:
            pr_id = model.add(
                [
                    "red",
                    _("Parents"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "ParentsKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        else:
            pr_id = model.add(
                [
                    "green",
                    _("Parents"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "ParentsKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        for line in parent_rows:
            model.add(line, node=pr_id)

    # Families (spouses/children/events)
    fam_rows = compare_spouses(db, gr_person, fs_person)
    FS_Family = any(line[0] != "green" for line in fam_rows)
    if model and fam_rows:
        if not FSG_Sync.FSG_Sync.fs_Tree:
            fam_id = model.add(
                [
                    "white",
                    _("Families"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "FamiliesKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        elif FS_Family:
            fam_id = model.add(
                [
                    "red",
                    _("Families"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "FamiliesKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        else:
            fam_id = model.add(
                [
                    "green",
                    _("Families"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "FamiliesKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        for line in fam_rows:
            model.add(line, node=fam_id)

    # Other facts
    other_rows = compare_other_facts(db, gr_person, fs_person)
    FS_Facts = any(line[0] != "green" for line in other_rows)
    if model and other_rows:
        if not FSG_Sync.FSG_Sync.fs_Tree:
            fact_id = model.add(
                [
                    "white",
                    _("Facts"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "FactsKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        elif FS_Facts:
            fact_id = model.add(
                [
                    "red",
                    _("Facts"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "FactsKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        else:
            fact_id = model.add(
                [
                    "green",
                    _("Facts"),
                    "==========",
                    "============================",
                    "==========",
                    col_fs,
                    "",
                    False,
                    "FactsKey",
                    None,
                    None,
                    None,
                    None,
                ]
            )
        for line in other_rows:
            model.add(line, node=fact_id)

    if not FSG_Sync.FSG_Sync.fs_Tree:
        return

    # Ensure we have Last-Modified/Etag for this person; handle FSID redirect
    if fs_person.id and (
        not hasattr(fs_person, "_last_modified") or not fs_person._last_modified
    ):
        path = "/platform/tree/persons/" + fs_person.id
        r = tree._fs_session.head_url(path)
        while r.status_code == 301 and "X-Entity-Forwarded-Id" in r.headers:
            fsid = r.headers["X-Entity-Forwarded-Id"]
            fs_utilities.link_gramps_fs_id(db, gr_person, fsid)
            fs_person.id = fsid
            path = "/platform/tree/persons/" + fs_person.id
            r = tree._fs_session.head_url(path)
        if "Last-Modified" in r.headers:
            fs_person._last_modified = int(
                time.mktime(email.utils.parsedate(r.headers["Last-Modified"]))
            )
        if "Etag" in r.headers:
            fs_person._etag = r.headers["Etag"]

    if not hasattr(fs_person, "_last_modified"):
        fs_person._last_modified = 0

    # "Identical" if no section indicates differences
    FS_Identical = not (FS_Family or FS_Essentials or FS_Facts or FS_Parents)

    # Optionally query for potential duplicates/documents
    if fs_person.id and dupdoc:
        path = "/platform/tree/persons/" + fs_person.id + "/matches"
        r = tree._fs_session.head_url(
            path, {"Accept": "application/x-gedcomx-atom+json"}
        )
        if r and r.status_code == 200:
            FS_Dup = True
        if r and r.status_code != 200:
            FS_Dup = False

        path = (
            "https://www.familysearch.org/service/tree/tree-data/record-matches/"
            + fs_person.id
        )
        r = tree._fs_session.get_url(path, {"Accept": "application/json"})
        if r and r.status_code == 200:
            try:
                js = r.json()
                if (
                    js
                    and "data" in js
                    and "matches" in js["data"]
                    and len(js["data"]["matches"]) >= 1
                ):
                    FS_Dok = True
                else:
                    FS_Dok = False
            except Exception as e:
                logger.warning(
                    "WARNING: corrupted file from %s, error: %s", path, e
                )
                logger.debug(
                    "Response content: %s", getattr(r, "content", b"")
                )

    # Update local status bookkeeping
    db_state.status_ts = int(time.time())
    if FS_Identical and (
        not db_state.confirmed_ts
        or (gr_person.change > db_state.confirmed_ts)
        or (fs_person._last_modified > db_state.confirmed_ts)
    ):
        db_state.confirmed_ts = db_state.status_ts

    FS_GrampsNewer = bool(
        db_state.confirmed_ts and gr_person.change > db_state.confirmed_ts
    )
    FS_RemoteNewer = bool(
        db_state.confirmed_ts and fs_person._last_modified > db_state.confirmed_ts
    )

    return []
