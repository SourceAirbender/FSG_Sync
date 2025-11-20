from __future__ import annotations

import logging
import email.utils
import time

from gramps.gui.plug import PluginWindows
from gramps.gui.utils import ProgressMeter
from gramps.gui.dialog import WarningDialog

from gramps.gen.const import GRAMPS_LOCALE as glocale

from gramps.gen.db import DbTxn

import tree
import FSG_Sync
import datab_familysearch
import fs_utilities

logger = logging.getLogger(__name__)

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


class FSCompareWindow(PluginWindows.ToolManagedWindowBatch):
    """
    The main batch window that iterates through filtered persons and compares
    them against FamilySearch.
    """

    def get_title(self):
        return _("FamilySearch Compare")

    def initial_frame(self):
        return _trans.gettext("Options")

    def run(self):
        logger.info("FSCompareWindow.run: starting")

        # Ensure FamilySearch session
        if not FSG_Sync.FSG_Sync.ensure_session(self):
            WarningDialog(_(u"Not connected to FamilySearch"))
            return

        progress = ProgressMeter(
            _(u"FamilySearch: Compare"),
            _trans.gettext("Starting"),
            can_cancel=True,
            parent=self.uistate.window,
        )

        self.uistate.set_busy_cursor(True)
        self.dbstate.db.disable_signals()

        # Ensure FS tree/cache exists
        if not FSG_Sync.FSG_Sync.fs_Tree:
            FSG_Sync.FSG_Sync.fs_Tree = tree.Tree()
            FSG_Sync.FSG_Sync.fs_Tree._getsources = False

        self.db = self.dbstate.get_database()

        # Prepare DB schema
        datab_familysearch.create_status_schema(self.db)

        # Build ordered list of persons to process
        filter_ = self.options.menu.get_option_by_name("Person").get_filter()
        days = self.options.menu.get_option_by_name("gui_days").get_value()
        force = self.options.menu.get_option_by_name("gui_needed").get_value()
        max_date = int(time.time()) - days * 24 * 3600

        person_handles = set(filter_.apply(self.db, self.db.iter_person_handles()))
        ordered = []

        progress.set_pass(_(u"Building ordered list (1/2)"), len(person_handles))
        logger.debug("Filtered list size: %d", len(person_handles))

        for handle in person_handles:
            if progress.get_cancelled():
                self._cleanup(progress)
                return
            progress.step()
            person = self.db.get_person_from_handle(handle)
            fsid = fs_utilities.get_fsftid(person)
            if fsid == "":
                continue
            self.db.dbapi.execute(
                "select status_ts from statistics_grampsfs_sync where p_handle=?",
                [handle],
            )
            row = self.db.dbapi.fetchone()
            if row and row[0]:
                if force or row[0] < max_date:
                    ordered.append([row[0], handle, fsid])
            else:
                ordered.append([0, handle, fsid])

        def key_first(item):
            return item[0]

        ordered.sort(key=key_first)

        # Process
        progress.set_pass(_(u"Processing list (2/2)"), len(ordered))
        logger.debug("Sorted list size: %d", len(ordered))

        def _prime_fetch(pair):
            # Ensure FS person header metadata (Last-Modified/Etag) and add to cache
            fsid_local = pair[2]
            fs_person = None
            date_mod = None
            etag = None

            if fsid_local in FSG_Sync.FSG_Sync.fs_Tree._persons:
                fs_person = FSG_Sync.FSG_Sync.fs_Tree._persons.get(fsid_local)

            if (
                not fs_person
                or not hasattr(fs_person, "_last_modified")
                or not getattr(fs_person, "_last_modified", None)
            ):
                path = "/platform/tree/persons/" + fsid_local
                r = tree._fs_session.head_url(path)
                while r and r.status_code == 301 and "X-Entity-Forwarded-Id" in r.headers:
                    fsid_local = r.headers["X-Entity-Forwarded-Id"]
                    logger.info("Redirected FS ID %s -> %s", pair[2], fsid_local)
                    pair[2] = fsid_local
                    path = "/platform/tree/persons/" + fsid_local
                    r = tree._fs_session.head_url(path)
                if r and "Last-Modified" in r.headers:
                    date_mod = int(
                        time.mktime(email.utils.parsedate(r.headers["Last-Modified"]))
                    )
                if r and "Etag" in r.headers:
                    etag = r.headers["Etag"]
                FSG_Sync.FSG_Sync.fs_Tree.add_persono(fsid_local)
                fs_person = FSG_Sync.FSG_Sync.fs_Tree._persons.get(fsid_local)

            if not fs_person:
                logger.warning(_(u"FS ID %s not found"), fsid_local)
                return
            fs_person._datemod = date_mod
            fs_person._etag = etag

        def _compare_pair(pair):
            person = self.db.get_person_from_handle(pair[1])
            fsid_local = pair[2]
            # link GRAMPS <-> FSID
            fs_utilities.link_gramps_fs_id(self.dbstate.db, person, fsid_local)
            logger.info("Processing %s %s", person.gramps_id, fsid_local)
            if fsid_local in FSG_Sync.FSG_Sync.fs_Tree._persons:
                fs_person = FSG_Sync.FSG_Sync.fs_Tree._persons.get(fsid_local)
                from .aggregate import compare_fs_to_gramps  # local import to avoid cycles

                compare_fs_to_gramps(fs_person, person, self.db, dupdoc=True)
            else:
                logger.warning("FS ID %s not found in cache", fsid_local)

        for pair in ordered:
            if progress.get_cancelled():
                self._cleanup(progress)
                return
            progress.step()
            _prime_fetch(pair)
            _compare_pair(pair)

        self._cleanup(progress)
        logger.info("FSCompareWindow.run: done")

    def _cleanup(self, progress):
        self.uistate.set_busy_cursor(False)
        progress.close()
        self.dbstate.db.enable_signals()
        self.dbstate.db.request_rebuild()
