# -*- coding: utf-8 -*-
"""
fs_tags.py — centralized helpers for FS status tagging.
Creates and applies four English tags on demand:
  - FS_Linked (white)
  - FS_NotLinked (black)
  - FS_Synced (green)
  - FS_OutOfSync (yellow)

Txn-safe: never opens a DbTxn inside another one.
"""

from __future__ import annotations
from typing import Iterable, Tuple, Any, List

from gramps.gen.db import DbTxn
from gramps.gen.lib import Tag, Person

# Public tag names
TAG_LINKED        = "FS_Linked"
TAG_NOT_LINKED    = "FS_NotLinked"
TAG_SYNCED        = "FS_Synced"
TAG_OUT_OF_SYNC   = "FS_OutOfSync"

TAG_COLORS = {
    TAG_LINKED: "white",
    TAG_NOT_LINKED: "black",
    TAG_SYNCED: "green",
    TAG_OUT_OF_SYNC: "yellow",
}

# Two exclusive groups: only one tag from each set may exist at a time
EXCLUSIVE_SETS = [
    {TAG_LINKED, TAG_NOT_LINKED},
    {TAG_SYNCED, TAG_OUT_OF_SYNC},
]

# ---------------------------------------------------------------------------
# Internal helpers (ALL require an explicit txn when they need to write)

def _ensure_tag(db, name: str, *, txn: DbTxn) -> Tag:
    """Get or create tag by name using the provided txn (no nested txns)."""
    tag = db.get_tag_from_name(name)
    if tag:
        return tag
    tag = Tag()
    tag.set_name(name)
    tag.set_color(TAG_COLORS.get(name, "yellow"))
    db.add_tag(tag, txn)
    db.commit_tag(tag, txn)
    return tag

def _remove_tags_by_name(db, person: Person, names: Iterable[str]) -> bool:
    """
    Remove any tags whose *names* are in `names` from `person`.
    Returns True if the tag list changed.
    (Pure in-memory on the Person object; caller commits person if changed.)
    """
    names = set(names or [])
    if not names:
        return False
    current = set(person.get_tag_list() or [])
    if not current:
        return False

    changed = False
    for nm in names:
        tag = db.get_tag_from_name(nm)
        if tag and tag.handle in current:
            current.remove(tag.handle)
            changed = True

    if changed:
        person.set_tag_list(list(current))
    return changed

def _add_tag_by_name(db, person: Person, name: str, *, txn: DbTxn) -> bool:
    """Ensure `name` tag is on person; returns True if added."""
    tag = _ensure_tag(db, name, txn=txn)
    handles = set(person.get_tag_list() or [])
    if tag.handle not in handles:
        handles.add(tag.handle)
        person.set_tag_list(list(handles))
        return True
    return False

def _set_exclusive_tag(db, person: Person, target: str, *, txn: DbTxn) -> bool:
    """
    From the exclusive set containing `target`, remove any existing tag
    on the person, then add `target`. Returns True if person changed.
    """
    changed = False
    for group in EXCLUSIVE_SETS:
        if target in group:
            changed |= _remove_tags_by_name(db, person, group)
            break
    changed |= _add_tag_by_name(db, person, target, txn=txn)
    return changed

# ---------------------------------------------------------------------------
# FSID extraction

def _extract_fsftid(person: Person) -> str | None:
    """Try fs_utilities.get_fsftid(person); else scan attributes for FSID."""
    try:
        import fs_utilities  # type: ignore
        try:
            fsid = fs_utilities.get_fsftid(person)
            if fsid:
                s = str(fsid).strip()
                return s or None
        except Exception:
            pass
    except Exception:
        pass

    for attr in person.get_attribute_list() or []:
        try:
            atype = attr.get_type().get_string().strip().upper()
        except Exception:
            continue
        if atype in {"_FSFTID", "FSFTID", "FSID", "FS_FTID", "_FS_FTID"}:
            val = str(attr.get_value() or "").strip()
            if val:
                return val
    return None

# ---------------------------------------------------------------------------
# Public APIs

def retag_all_link_status(db) -> Tuple[int, int, int, int]:
    """
    Tag everyone by FS link status:
      FS_Linked (white)     if person has _FSFTID
      FS_NotLinked (black)  otherwise

    Returns: (total, linked_count, not_linked_count, changed_count)
    """
    total = linked = not_linked = changed = 0

    # Always own the txn here; one bulk write txn, no nesting inside.
    with DbTxn("Retag all (FS link status)", db) as txn:
        # Ensure link-status tags exist up front in THIS txn
        _ensure_tag(db, TAG_LINKED, txn=txn)
        _ensure_tag(db, TAG_NOT_LINKED, txn=txn)

        for handle in db.iter_person_handles():
            total += 1
            p = db.get_person_from_handle(handle)
            fsid = _extract_fsftid(p)
            before = set(p.get_tag_list() or [])

            if fsid:
                _set_exclusive_tag(db, p, TAG_LINKED, txn=txn)
                linked += 1
            else:
                _set_exclusive_tag(db, p, TAG_NOT_LINKED, txn=txn)
                not_linked += 1

            after = set(p.get_tag_list() or [])
            if before != after:
                changed += 1
                db.commit_person(p, txn)

    return total, linked, not_linked, changed

def set_sync_status_for_person(db, person: Person, *, is_synced: bool) -> None:
    """
    Apply FS_Synced (green) or FS_OutOfSync (yellow) exclusively.
    Uses a short txn unless caller already has one open (compare UIs usually don't).
    """
    existing = getattr(db, "transaction", None)
    if existing:
        changed = _set_exclusive_tag(db, person, TAG_SYNCED if is_synced else TAG_OUT_OF_SYNC, txn=existing)
        if changed:
            db.commit_person(person, existing)
        return

    with DbTxn("Tag person sync state", db) as txn:
        changed = _set_exclusive_tag(db, person, TAG_SYNCED if is_synced else TAG_OUT_OF_SYNC, txn=txn)
        if changed:
            db.commit_person(person, txn)

# ---------------------------------------------------------------------------
# Compare payload → synced?

def _norm_color(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("color", value.get("status", ""))
    s = str(value).strip().lower()
    if s in {"green", "yellow", "red"}:
        return s
    if s in {"ok", "okay", "match", "matched", "equal", "same", "synced", "✓", "✔", "true", "yes", "y", "1"}:
        return "green"
    if s in {"warn", "warning", "diff", "different", "mismatch", "partial", "some", "changed"}:
        return "yellow"
    if s in {"error", "x", "no", "false", "n", "0", "bad"}:
        return "red"
    return s or "red"

def _all_green_simple_rows(rows: list) -> bool:
    if not rows:
        return True
    for r in rows:
        v = r[0] if isinstance(r, (list, tuple)) and r else r
        if _norm_color(v) != "green":
            return False
    return True

def compute_sync_from_payload(data: dict) -> bool:
    for group in (data.get("overview") or []):
        for row in (group.get("rows") or []):
            cols = row.get("columns") if isinstance(row, dict) else None
            v = cols[0] if cols else (row[0] if isinstance(row, (list, tuple)) and row else row)
            if _norm_color(v) != "green":
                return False
    if not _all_green_simple_rows(data.get("notes") or []):
        return False
    if not _all_green_simple_rows(data.get("sources") or []):
        return False
    return True

def explain_out_of_sync(data: dict) -> List[str]:
    reasons: List[str] = []
    for gi, group in enumerate(data.get("overview") or []):
        title = group.get("title", f"Group {gi+1}")
        for ri, row in enumerate(group.get("rows") or []):
            cols = row.get("columns") if isinstance(row, dict) else None
            v = cols[0] if cols else (row[0] if isinstance(row, (list, tuple)) and row else row)
            c = _norm_color(v)
            if c != "green":
                reasons.append(f"Overview → {title} → row {ri+1} not green ({c})")
                break
    for ri, row in enumerate(data.get("notes") or []):
        c = _norm_color(row[0] if isinstance(row, (list, tuple)) and row else row)
        if c != "green":
            reasons.append(f"Notes → row {ri+1} not green ({c})")
            break
    for ri, row in enumerate(data.get("sources") or []):
        c = _norm_color(row[0] if isinstance(row, (list, tuple)) and row else row)
        if c != "green":
            reasons.append(f"Sources → row {ri+1} not green ({c})")
            break
    return reasons
