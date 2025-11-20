# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Optional

# GTK
import gi
gi.require_version("Gtk", "3.0"); gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.dialog import OkDialog, WarningDialog
from gramps.gui.listmodel import ListModel, NOSORT, COLOR, TOGGLE
from gramps.gen.display.place import displayer as _pd
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.lib import Person

# Plugin deps
import datab_familysearch
import tree
import fs_utilities
import fs_compare
import fs_tags

import gedcomx_v1

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


class UIMixin:
    def init(self):
        self.gui.WIDGET = self._build_ui()
        datab_familysearch.create_status_schema(self.dbstate.db)
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.gui.WIDGET)
        self.gui.WIDGET.show_all()

        import os
        from .cache import _FsCache
        base_dir = os.path.dirname(__file__)
        self.__class__._cache = _FsCache(base_dir)

        try:
            fmt = self.config.get('preferences.place-format')
            pf = _pd.get_formats()[fmt]
            self.lang = pf.language[:2]
        except Exception:
            self.lang = (glocale.language[0] or "en")[:2]

        if not self.__class__.fs_Tree:
            self.__class__.fs_Tree = tree.Tree()
            self.__class__.fs_Tree._getsources = False

        self._refresh_status()

    def main(self):
        self._refresh_status()

    def db_changed(self):
        self.update()

    def active_changed(self, handle):
        self.update()

    def update_has_data(self):
        active_handle = self.get_active('Person')
        self.set_has_data(bool(active_handle))

    # --- UI building ---
    def _build_ui(self) -> Gtk.Widget:
        grid = Gtk.Grid(
            column_spacing=6,
            row_spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        self.btn_login = Gtk.Button(label=_("Login"))
        self.btn_login.connect("clicked", self._on_login)

        self.btn_link = Gtk.Button(label=_("Link person"))
        self.btn_link.connect("clicked", self._on_link_person)

        self.btn_compare = Gtk.Button(label=_("Compare"))
        self.btn_compare.connect("clicked", self._on_compare)

        self.btn_compare_web = Gtk.Button(label=_("Compare (Web)"))
        self.btn_compare_web.connect("clicked", self._on_compare_web)

        self.btn_import_spouse = Gtk.Button(label=_("Import spouse"))
        self.btn_import_spouse.connect("clicked", self._on_import_spouse)

        self.btn_import_children = Gtk.Button(label=_("Import children"))
        self.btn_import_children.connect("clicked", self._on_import_children)

        self.btn_import_parents = Gtk.Button(label=_("Import parents"))
        self.btn_import_parents.connect("clicked", self._on_import_parents)

        # bulk tag button
        self.btn_tag_all = Gtk.Button(label=_("Tag FS link status (all)"))
        self.btn_tag_all.connect("clicked", self._on_tag_all_link_status)

        # clear cache button
        self.btn_clear_cache = Gtk.Button(label=_("Clear cache"))
        self.btn_clear_cache.connect("clicked", self._on_clear_cache)

        self.lbl_status = Gtk.Label(label=_("Not logged in • FSID: —"))
        self.lbl_status.set_xalign(0)

        # Row 0 buttons
        grid.attach(self.btn_login,           0, 0, 1, 1)
        grid.attach(self.btn_link,            1, 0, 1, 1)
        grid.attach(self.btn_compare,         2, 0, 1, 1)
        grid.attach(self.btn_compare_web,     3, 0, 1, 1)
        grid.attach(self.btn_import_spouse,   4, 0, 1, 1)
        grid.attach(self.btn_import_children, 5, 0, 1, 1)
        grid.attach(self.btn_import_parents,  6, 0, 1, 1)
        grid.attach(self.btn_tag_all,         7, 0, 1, 1)
        grid.attach(self.btn_clear_cache,     8, 0, 1, 1)

        # Status label spans all 9 columns
        grid.attach(self.lbl_status,          0, 1, 9, 1)

        return grid

    def _refresh_status(self):
        active_handle = self.get_active('Person')
        fsid = ""
        if active_handle:
            p = self.dbstate.db.get_person_from_handle(active_handle)
            fsid = fs_utilities.get_fsftid(p) or ""
            self.__class__.FSID = fsid or None
        logged = bool(tree._fs_session and tree._fs_session.logged)
        if logged:
            who = getattr(tree._fs_session, "username", None) or _("(session)")
            txt = _("Logged in as {who} • FSID: {fsid}").format(
                who=who, fsid=fsid or "—"
            )
        else:
            txt = _("Not logged in • FSID: {fsid}").format(fsid=fsid or "—")
        self.lbl_status.set_text(txt)

    # --- Simple helpers used by compare GTK lists ---
    def _toggle_noop(self, path, val=None):
        return

    # --- Link FSID dialog ---
    def _on_link_person(self, _btn):
        ...
        # (unchanged)
        ...

    # tagging
    def _on_tag_all_link_status(self, _btn):
        total, linked, not_linked, changed = fs_tags.retag_all_link_status(
            self.dbstate.db
        )
        OkDialog(
            _(
                "Re-tagged {changed} of {total} people ({linked} linked, {not_linked} not linked)."
            ).format(
                total=total,
                linked=linked,
                not_linked=not_linked,
                changed=changed,
            )
        )

    # clear cache handler
    def _on_clear_cache(self, _btn):
        try:
            self._clear_fs_cache()
            OkDialog(_("FamilySearch cache cleared."))
        except Exception as e:
            WarningDialog(
                _("Failed to clear cache:\n{err}").format(err=str(e))
            )
