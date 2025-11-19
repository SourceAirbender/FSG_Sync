# -*- coding: utf-8 -*-
from __future__ import annotations


def create_status_schema(db) -> None:
    # Ensure the 'statistics_grampsfs_sync' table exists 
    if not db.dbapi.table_exists("statistics_grampsfs_sync"):
        db.dbapi.execute(
            "CREATE TABLE statistics_grampsfs_sync ("
            "p_handle VARCHAR(50) PRIMARY KEY NOT NULL, "
            "fsid CHAR(8), "
            "is_root INTEGER, "
            "status_ts INTEGER, "
            "confirmed_ts INTEGER, "
            "gramps_modified_ts INTEGER, "
            "fs_modified_ts INTEGER, "
            "essential_conflict INTEGER, "
            "conflict INTEGER"
            ")"
        )


class FSStatusDB:
    """
    Row object for statistics_grampsfs_sync

    Attributes:
        p_handle: str
        fsid: str | None
        is_root: bool (stored as 0/1)
        status_ts: int | None
        confirmed_ts: int | None
        gramps_modified_ts: int | None
        fs_modified_ts: int | None
        essential_conflict: bool (stored as 0/1)
        conflict: bool (stored as 0/1)
    """
    def __init__(self, db, p_handle: str | None = None):
        self.db = db
        self.p_handle = p_handle
        self.fsid: str | None = None
        self.is_root: bool = False
        self.status_ts: int | None = None
        self.confirmed_ts: int | None = None
        self.gramps_modified_ts: int | None = None
        self.fs_modified_ts: int | None = None
        self.essential_conflict: bool = False
        self.conflict: bool = False

    def commit(self, txn=None) -> None:
        """
        Insert or update this row
        If a transaction is provided by the caller, it will be handled upstream.
        """
        if not self.p_handle:
            print("datab_familysearch.FSStatusDB.commit: missing p_handle")
            return

        self.db.dbapi.execute(
            "SELECT 1 FROM statistics_grampsfs_sync WHERE p_handle=?",
            [self.p_handle],
        )
        row = self.db.dbapi.fetchone()

        vals = [
            self.fsid,
            1 if self.is_root else 0,
            self.status_ts,
            self.confirmed_ts,
            self.gramps_modified_ts,
            self.fs_modified_ts,
            1 if self.essential_conflict else 0,
            1 if self.conflict else 0,
        ]

        if row:
            sql = (
                "UPDATE statistics_grampsfs_sync SET "
                "fsid=?, is_root=?, status_ts=?, confirmed_ts=?, "
                "gramps_modified_ts=?, fs_modified_ts=?, "
                "essential_conflict=?, conflict=? "
                "WHERE p_handle=?"
            )
            self.db.dbapi.execute(sql, vals + [self.p_handle])
        else:
            sql = (
                "INSERT INTO statistics_grampsfs_sync ("
                "p_handle, fsid, is_root, status_ts, confirmed_ts, "
                "gramps_modified_ts, fs_modified_ts, essential_conflict, conflict"
                ") VALUES (?,?,?,?,?,?,?,?,?)"
            )
            self.db.dbapi.execute(sql, [self.p_handle] + vals)

    def get(self, person_handle: str | None = None) -> None:
        """
        Load row by handle into this object; if not found, keep defaults and set handle.
        """
        if not person_handle:
            person_handle = self.p_handle
        if not person_handle:
            print("datab_familysearch.FSStatusDB.get: missing person_handle")
            return

        self.db.dbapi.execute(
            "SELECT p_handle, fsid, is_root, status_ts, confirmed_ts, "
            "gramps_modified_ts, fs_modified_ts, essential_conflict, conflict "
            "FROM statistics_grampsfs_sync WHERE p_handle=?",
            [person_handle],
        )
        row = self.db.dbapi.fetchone()
        if row:
            (
                self.p_handle,
                self.fsid,
                is_root,
                self.status_ts,
                self.confirmed_ts,
                self.gramps_modified_ts,
                self.fs_modified_ts,
                essential_conflict,
                conflict,
            ) = row
            self.is_root = bool(is_root)
            self.essential_conflict = bool(essential_conflict)
            self.conflict = bool(conflict)
        else:
            self.p_handle = person_handle
            # others remain defaults


__all__ = ["create_status_schema", "FSStatusDB"]
