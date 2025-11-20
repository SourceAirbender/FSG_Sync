# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Optional

# GTK
from gi.repository import Gtk

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.dialog import OkDialog, WarningDialog
from gramps.gen.db import DbTxn
from gramps.gen.lib import Person, Family, ChildRef

# Plugin deps
import fs_utilities
import fs_import

import gedcomx_v1

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

class ImportParentsMixin:
    def _on_import_parents(self, _btn):
        active = self.get_active('Person')
        if not active:
            WarningDialog(_("Select a person first."))
            return
        import tree
        if not (tree._fs_session and tree._fs_session.logged):
            WarningDialog(_("You must login first."))
            return

        child_gr = self.dbstate.db.get_person_from_handle(active)
        child_fsid = fs_utilities.get_fsftid(child_gr)
        if not child_fsid:
            WarningDialog(_("This Gramps person is not linked to FamilySearch yet. Use ‘Link person’."))
            return

        fsChild = self._ensure_person_cached(child_fsid, with_relatives=True)

        parent_ids = set()
        for cp in getattr(fsChild, "_parentsCP", []) or []:
            if getattr(cp, "parent1", None) and cp.parent1.resourceId:
                parent_ids.add(cp.parent1.resourceId)
            if getattr(cp, "parent2", None) and cp.parent2.resourceId:
                parent_ids.add(cp.parent2.resourceId)
        for rel in getattr(fsChild, "_parents", []) or []:
            if getattr(rel, "person1", None) and rel.person1.resourceId:
                parent_ids.add(rel.person1.resourceId)
            if getattr(rel, "person2", None) and rel.person2.resourceId:
                parent_ids.add(rel.person2.resourceId)

        parent_ids.discard(None)
        parent_ids.discard(child_fsid)
        if not parent_ids:
            OkDialog(_("No parents found on FamilySearch for this person."))
            return

        dlg = Gtk.Dialog(title=_("Import parents"), transient_for=self.uistate.window, flags=0)
        dlg.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dlg.add_button(_("Import selected"), Gtk.ResponseType.OK)
        box = dlg.get_content_area()
        box.set_margin_top(10); box.set_margin_bottom(10); box.set_margin_start(10); box.set_margin_end(10)

        store = Gtk.ListStore(bool, str, str, str)
        for pid in sorted(parent_ids):
            exists = self._find_person_by_fsid(pid) is not None
            label = self._label_for_person_id(pid) + ("  ✓ " + _("already in tree") if exists else "")
            bg = "palegreen" if exists else ""
            store.append([not exists, label, pid, bg])

        treev = Gtk.TreeView(model=store)
        cr_toggle = Gtk.CellRendererToggle()
        cr_toggle.connect("toggled", lambda _w, path: store[path].__setitem__(0, not store[path][0]))
        treev.append_column(Gtk.TreeViewColumn(_("Import"), cr_toggle, active=0))

        cr_text = Gtk.CellRendererText()
        col_label = Gtk.TreeViewColumn(_("Parent"), cr_text, text=1)
        col_label.add_attribute(cr_text, "background", 3)
        treev.append_column(col_label)

        sw = Gtk.ScrolledWindow(); sw.set_min_content_height(200); sw.add(treev)
        box.add(Gtk.Label(label=_("Items already in your tree are highlighted in green (✓).")))
        box.add(sw)

        dlg.show_all()
        resp = dlg.run()
        if resp != Gtk.ResponseType.OK:
            dlg.destroy(); return
        chosen = [row[2] for row in store if row[0] and row[2]]
        dlg.destroy()
        if not chosen:
            return

        imported_parents: List[Person] = []
        for pid in chosen:
            importer = fs_import.FSToGrampsImporter()
            importer.noreimport = False
            importer.asc = 0
            importer.desc = 0
            importer.include_spouses = False
            importer.refresh_signals = False
            importer.import_tree(self, pid)

            try:
                if fs_utilities.FS_INDEX_PEOPLE and pid in fs_utilities.FS_INDEX_PEOPLE:
                    h = fs_utilities.FS_INDEX_PEOPLE[pid]
                    pr = self.dbstate.db.get_person_from_handle(h)
                else:
                    pr = self._find_person_by_fsid(pid)
            except Exception:
                pr = self._find_person_by_fsid(pid)

            if pr:
                imported_parents.append(pr)

        if not imported_parents:
            WarningDialog(_("Parents imported but could not be located in the local database."))
            return

        with DbTxn(_("Import FamilySearch parents"), self.dbstate.db) as txn:
            fam = self._ensure_family_for_parents(imported_parents, txn)
            if fam:
                already = any(cr.ref == child_gr.handle for cr in fam.get_child_ref_list())
                if not already:
                    cref = ChildRef()
                    cref.ref = child_gr.handle
                    fam.add_child_ref(cref)
                self.dbstate.db.commit_family(fam, txn)

        OkDialog(_("Parent(s) imported and linked."))

    def _ensure_family_for_parents(self, parents: List[Person], txn: DbTxn) -> Optional[Family]:
        if not parents:
            return None
        if len(parents) == 1:
            p = parents[0]
            for fh in p.get_family_handle_list():
                fam = self.dbstate.db.get_family_from_handle(fh)
                if not fam:
                    continue
                if fam.father_handle == p.handle and not fam.mother_handle:
                    return fam
                if fam.mother_handle == p.handle and not fam.father_handle:
                    return fam
            fam = Family()
            if p.get_gender() == Person.MALE:
                fam.set_father_handle(p.handle)
            elif p.get_gender() == Person.FEMALE:
                fam.set_mother_handle(p.handle)
            else:
                fam.set_father_handle(p.handle)
            self.dbstate.db.add_family(fam, txn)
            self.dbstate.db.commit_family(fam, txn)
            return fam

        p1, p2 = parents[0], parents[1]
        for fh in p1.get_family_handle_list():
            fam = self.dbstate.db.get_family_from_handle(fh)
            if not fam:
                continue
            if {fam.father_handle, fam.mother_handle} == {p1.handle, p2.handle}:
                return fam

        fam = Family()
        if p1.get_gender() == Person.MALE and p2.get_gender() == Person.FEMALE:
            fam.set_father_handle(p1.handle); fam.set_mother_handle(p2.handle)
        elif p1.get_gender() == Person.FEMALE and p2.get_gender() == Person.MALE:
            fam.set_father_handle(p2.handle); fam.set_mother_handle(p1.handle)
        else:
            fam.set_father_handle(p1.handle); fam.set_mother_handle(p2.handle)
        self.dbstate.db.add_family(fam, txn)
        self.dbstate.db.commit_family(fam, txn)
        return fam
