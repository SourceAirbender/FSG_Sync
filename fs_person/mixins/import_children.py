# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional, List

# GTK
from gi.repository import Gtk

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.dialog import OkDialog, WarningDialog
from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer
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

class ImportChildrenMixin:
    def _on_import_children(self, _btn):
        active = self.get_active('Person')
        if not active:
            WarningDialog(_("Select a person first."))
            return
        import tree
        if not (tree._fs_session and tree._fs_session.logged):
            WarningDialog(_("You must login first."))
            return

        gr = self.dbstate.db.get_person_from_handle(active)
        fsid = fs_utilities.get_fsftid(gr)
        if not fsid:
            WarningDialog(_("This Gramps person is not linked to FamilySearch yet. Use ‘Link person’."))
            return

        fsP = self._ensure_person_cached(fsid, with_relatives=True)
        fs_children = list(getattr(fsP, "_children", []) or [])
        if not fs_children:
            OkDialog(_("No children found on FamilySearch for this person."))
            return

        dlg = Gtk.Dialog(title=_("Import children"), transient_for=self.uistate.window, flags=0)
        dlg.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dlg.add_button(_("Import selected"), Gtk.ResponseType.OK)
        box = dlg.get_content_area()
        box.set_margin_top(10); box.set_margin_bottom(10); box.set_margin_start(10); box.set_margin_end(10)

        store = Gtk.ListStore(bool, str, str, str)

        child_ids = set()
        for cp in getattr(fsP, "_children", []) or []:
            cid = getattr(getattr(cp, "child", None), "resourceId", None)
            if cid:
                child_ids.add(cid)
                continue
            p1 = getattr(getattr(cp, "person1", None), "resourceId", None)
            p2 = getattr(getattr(cp, "person2", None), "resourceId", None)
            ids = [pid for pid in (p1, p2) if pid]
            if fsid in ids:
                ids.remove(fsid)
            for pid in ids:
                child_ids.add(pid)

        child_ids.discard(None)
        child_ids.discard(fsid)

        if not child_ids:
            OkDialog(_("No children found on FamilySearch for this person."))
            dlg.destroy()
            return

        for cid in sorted(child_ids):
            exists = self._find_person_by_fsid(cid) is not None
            label = self._label_for_person_id(cid) + ("  ✓ " + _("already in tree") if exists else "")
            bg = "palegreen" if exists else ""
            store.append([not exists, label, cid, bg])

        treev = Gtk.TreeView(model=store)
        cr_toggle = Gtk.CellRendererToggle()
        cr_toggle.connect("toggled", lambda _w, path: store[path].__setitem__(0, not store[path][0]))
        col0 = Gtk.TreeViewColumn(_("Import"), cr_toggle, active=0)

        cr_text = Gtk.CellRendererText()
        col1 = Gtk.TreeViewColumn(_("Child"), cr_text, text=1)
        col1.add_attribute(cr_text, "background", 3)

        treev.append_column(col0); treev.append_column(col1)
        sw = Gtk.ScrolledWindow(); sw.set_min_content_height(260); sw.add(treev)

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

        imported = 0
        with DbTxn(_("Import FamilySearch children"), self.dbstate.db) as txn:
            for child_fsid in chosen:
                importer = fs_import.FSToGrampsImporter()
                importer.noreimport = False
                importer.asc = 0
                importer.desc = 0
                importer.include_spouses = False
                importer.refresh_signals = False
                importer.import_tree(self, child_fsid)

                child_person = self._find_person_by_fsid(child_fsid)
                if not child_person:
                    continue

                other_parent_fsid = self._infer_other_parent_fsid(child_fsid, fsid)
                other_parent_person = self._find_person_by_fsid(other_parent_fsid) if other_parent_fsid else None

                fam = self._choose_or_make_family_for_child(gr, other_parent_person, txn)
                if fam:
                    already = any(cr.ref == child_person.handle for cr in fam.get_child_ref_list())
                    if not already:
                        cref = ChildRef()
                        cref.ref = child_person.handle
                        fam.add_child_ref(cref)
                        self.dbstate.db.commit_family(fam, txn)
                    imported += 1

        OkDialog(_("{n} child(ren) imported and linked.").format(n=imported))

    def _infer_other_parent_fsid(self, child_fsid: str, known_parent_fsid: str) -> Optional[str]:
        try:
            ch = self._ensure_person_cached(child_fsid, with_relatives=True)
            for cp in getattr(ch, "_parentsCP", []) or []:
                p1 = getattr(cp, "parent1", None)
                p2 = getattr(cp, "parent2", None)
                pid1 = p1.resourceId if p1 else None
                pid2 = p2.resourceId if p2 else None
                if known_parent_fsid in (pid1, pid2):
                    return pid2 if pid1 == known_parent_fsid else pid1
        except Exception:
            pass
        return None

    def _choose_or_make_family_for_child(self, active_parent: Person, other_parent: Optional[Person], txn: DbTxn) -> Optional[Family]:
        if other_parent:
            for fh in active_parent.get_family_handle_list():
                fam = self.dbstate.db.get_family_from_handle(fh)
                if not fam:
                    continue
                if {fam.father_handle, fam.mother_handle} == {active_parent.handle, other_parent.handle}:
                    return fam

        candidates: List[Family] = []
        for fh in active_parent.get_family_handle_list():
            fam = self.dbstate.db.get_family_from_handle(fh)
            if not fam:
                continue
            if fam.father_handle == active_parent.handle or fam.mother_handle == active_parent.handle:
                candidates.append(fam)

        if other_parent:
            for fam in candidates:
                if fam.father_handle == other_parent.handle or fam.mother_handle == other_parent.handle:
                    return fam
            fam = Family()
            if active_parent.get_gender() == Person.MALE:
                fam.set_father_handle(active_parent.handle)
                fam.set_mother_handle(other_parent.handle)
            elif active_parent.get_gender() == Person.FEMALE:
                fam.set_father_handle(other_parent.handle)
                fam.set_mother_handle(active_parent.handle)
            else:
                fam.set_father_handle(active_parent.handle)
                fam.set_mother_handle(other_parent.handle)
            self.dbstate.db.add_family(fam, txn)
            self.dbstate.db.commit_family(fam, txn)
            return fam

        if len(candidates) == 1:
            return candidates[0]

        if len(candidates) > 1:
            fam = self._ask_user_pick_family(active_parent, candidates)
            if fam:
                return fam

        fam = Family()
        if active_parent.get_gender() == Person.MALE:
            fam.set_father_handle(active_parent.handle)
        elif active_parent.get_gender() == Person.FEMALE:
            fam.set_mother_handle(active_parent.handle)
        else:
            fam.set_father_handle(active_parent.handle)
        self.dbstate.db.add_family(fam, txn)
        self.dbstate.db.commit_family(fam, txn)
        return fam

    def _ask_user_pick_family(self, active_parent: Person, families: List[Family]) -> Optional[Family]:
        dlg = Gtk.Dialog(title=_("Choose a family"), transient_for=self.uistate.window, flags=0)
        dlg.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dlg.add_button(_("Use this family"), Gtk.ResponseType.OK)
        box = dlg.get_content_area()
        box.set_margin_top(10); box.set_margin_bottom(10); box.set_margin_start(10); box.set_margin_end(10)

        model = Gtk.ListStore(str, object)
        tv = Gtk.TreeView(model=model)
        sel = tv.get_selection()
        col = Gtk.TreeViewColumn(_("Family (other parent)"), Gtk.CellRendererText(), text=0)
        tv.append_column(col)
        sw = Gtk.ScrolledWindow(); sw.set_min_content_height(180); sw.add(tv)
        box.add(sw)

        for fam in families:
            other = None
            if fam.father_handle and fam.father_handle != active_parent.handle:
                other = self.dbstate.db.get_person_from_handle(fam.father_handle)
            if fam.mother_handle and fam.mother_handle != active_parent.handle:
                other = self.dbstate.db.get_person_from_handle(fam.mother_handle) or other
            label = _("(no other parent)")
            if other:
                label = name_displayer.display(other)
            model.append([label, fam])

        dlg.show_all()
        resp = dlg.run()
        chosen_fam = None
        if resp == Gtk.ResponseType.OK:
            (m, itr) = sel.get_selected()
            if itr:
                chosen_fam = m[itr][1]
        dlg.destroy()
        return chosen_fam
