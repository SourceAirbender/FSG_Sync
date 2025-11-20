from __future__ import annotations

# GTK
from gi.repository import Gtk

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.dialog import OkDialog, WarningDialog
from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.lib import Person, Family

# Plugin deps
import fs_import
import fs_utilities

import gedcomx_v1

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

class ImportSpouseMixin:
    def _on_import_spouse(self, _btn):
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
        spouses = []
        for rel in fsP._spouses:
            spid = rel.person1.resourceId if (rel.person2 and rel.person2.resourceId == fsP.id) else (rel.person2.resourceId if rel.person1 else None)
            if not spid:
                spid = rel.person2.resourceId if rel.person1 and rel.person1.resourceId == fsP.id else spid
            if spid:
                spouses.append((rel, spid))

        if not spouses:
            OkDialog(_("No spouses found on FamilySearch for this person."))
            return

        dlg = Gtk.Dialog(title=_("Import spouse"), transient_for=self.uistate.window, flags=0)
        dlg.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dlg.add_button(_("Import"), Gtk.ResponseType.OK)
        box = dlg.get_content_area()
        box.set_margin_top(12); box.set_margin_bottom(12); box.set_margin_start(12); box.set_margin_end(12)

        box.add(Gtk.Label(label=_("Choose the spouse to import:")))
        combo_store = Gtk.ListStore(str, str, str)
        for _rel, spid in spouses:
            sp = self._ensure_person_cached(spid, with_relatives=False)
            nm = sp.preferred_name()
            exists = self._find_person_by_fsid(spid) is not None
            label = f"{nm.akSurname()}, {nm.akGiven()} [{spid}]" + ("  ✓ " + _("already in tree") if exists else "")
            bg = "palegreen" if exists else ""
            combo_store.append([label, spid, bg])

        combo = Gtk.ComboBox.new_with_model(combo_store)
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, "text", 0)
        combo.add_attribute(cell, "background", 2)
        combo.set_active(0)

        box.add(Gtk.Label(label=_("Items already in your tree are highlighted in green (✓).")))
        box.add(combo)
        dlg.show_all()
        resp = dlg.run()
        if resp != Gtk.ResponseType.OK:
            dlg.destroy(); return
        itr = combo.get_active_iter()
        chosen = combo.get_model()[itr][1] if itr else None
        dlg.destroy()
        if not chosen:
            return

        importer = fs_import.FSToGrampsImporter()
        importer.noreimport = False
        importer.asc = 0
        importer.desc = 0
        importer.include_spouses = False
        importer.refresh_signals = False
        importer.import_tree(self, chosen)

        with DbTxn(_("Link spouses"), self.dbstate.db) as txn:
            current_fams = set(gr.get_family_handle_list())
            spouse_person = self._find_person_by_fsid(chosen)
            if not spouse_person:
                WarningDialog(_("Spouse imported but not found in the local database."))
                return
            for fh in current_fams:
                fam = self.dbstate.db.get_family_from_handle(fh)
                if fam and (fam.father_handle == spouse_person.handle or fam.mother_handle == spouse_person.handle):
                    self.dbstate.db.commit_family(fam, txn)
                    break
            else:
                fam = Family()
                if gr.get_gender() == Person.MALE:
                    fam.set_father_handle(gr.handle); fam.set_mother_handle(spouse_person.handle)
                elif gr.get_gender() == Person.FEMALE:
                    fam.set_father_handle(spouse_person.handle); fam.set_mother_handle(gr.handle)
                else:
                    fam.set_father_handle(gr.handle); fam.set_mother_handle(spouse_person.handle)
                self.dbstate.db.add_family(fam, txn)
                self.dbstate.db.commit_family(fam, txn)

        OkDialog(_("Spouse imported and linked."))

