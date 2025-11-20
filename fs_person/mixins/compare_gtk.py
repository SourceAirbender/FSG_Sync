# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any

# GTK
from gi.repository import Gtk

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.dialog import WarningDialog
from gramps.gui.listmodel import ListModel, NOSORT, COLOR, TOGGLE
from gramps.gen.lib import Person

# Plugin deps
import fs_utilities
import fs_compare
import fs_tags

import gedcomx_v1

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


class CompareGtkMixin:
    def _on_compare(self, _btn):
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

        self._ensure_person_cached(fsid, with_relatives=True)

        win = Gtk.Window(title=_("FamilySearch comparison"))
        win.set_transient_for(self.uistate.window)
        win.set_default_size(1140, 700)

        notebook = Gtk.Notebook()

        tv_overview, model_overview = self._make_overview_tree_model()
        notebook.append_page(tv_overview, Gtk.Label(label=_("Overview")))
        tv_notes, model_notes = self._make_notes_tree()
        notebook.append_page(tv_notes, Gtk.Label(label=_("Notes")))
        tv_sources, model_sources = self._make_sources_tree()
        tv_sources.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        notebook.append_page(tv_sources, Gtk.Label(label=_("Sources")))

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin=6)
        btn_refresh = Gtk.Button(label=_("Refresh from FamilySearch"))
        btn_import_sources = Gtk.Button(label=_("Import sources…"))
        btn_close = Gtk.Button(label=_("Close"))
        action_box.pack_start(btn_refresh, False, False, 0)
        action_box.pack_start(btn_import_sources, False, False, 0)
        action_box.pack_end(btn_close, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.pack_start(notebook, True, True, 0)
        vbox.pack_end(action_box, False, False, 0)
        win.add(vbox)

        def do_fill_all(force=False):
            if force:
                self._ensure_person_cached(fsid, with_relatives=True, force=True)
            model_overview.clear()
            self._fill_overview(model_overview, gr, fsid)
            model_notes.clear()
            self._fill_notes(model_notes, gr, fsid)
            model_sources.clear()
            self._fill_sources(model_sources, gr, fsid)

            # auto-tag after each refresh/fill
            try:
                payload = self._build_compare_json(gr, fsid)
                is_synced = fs_tags.compute_sync_from_payload(payload)
                fs_tags.set_sync_status_for_person(self.dbstate.db, gr, is_synced=is_synced)
            except Exception:
                pass

        def do_import_sources(_btn):
            self._import_sources_dialog(gr, fsid)

        btn_refresh.connect("clicked", lambda *_: do_fill_all(True))
        btn_import_sources.connect("clicked", do_import_sources)
        btn_close.connect("clicked", lambda *_: win.destroy())

        do_fill_all(False)

        # auto-tag on initial compare open
        try:
            payload = self._build_compare_json(gr, fsid)
            is_synced = fs_tags.compute_sync_from_payload(payload)
            fs_tags.set_sync_status_for_person(self.dbstate.db, gr, is_synced=is_synced)
        except Exception:
            pass

        win.show_all()

    def _make_overview_tree_model(self):
        titles = [
            (_('Color'),      1,  40, COLOR),
            (_('Property'),   2, 140),
            (_('Date'),       3, 120),
            (_('Gramps Value'), 4, 360),
            (_('FS Date'),    5, 120),
            (_('FS Value'),   6, 360),
            (' ',             NOSORT, 1),
            ('x',             8, 5, TOGGLE, True, self._toggle_noop),
            (_('xType'),      NOSORT, 0),
            (_('xGr'),        NOSORT, 0),
            (_('xFs'),        NOSORT, 0),
            (_('xGr2'),       NOSORT, 0),
            (_('xFs2'),       NOSORT, 0),
        ]
        treeview = Gtk.TreeView()
        model = ListModel(treeview, titles, list_mode="tree")
        return treeview, model

    def _make_notes_tree(self):
        treeview = Gtk.TreeView()
        titles = [
            (_('Color'), 1, 40, COLOR),
            (_('Scope'), 2, 120),
            (_('Title'), 3, 220),
            (_('Gramps Value'), 4, 360),
            (_('FS Title'), 5, 220),
            (_('FS Value'), 6, 360),
        ]
        model = ListModel(treeview, titles, list_mode="tree")
        return treeview, model

    def _make_sources_tree(self):
        treeview = Gtk.TreeView()
        titles = [
            (_('Color'), 1, 40, COLOR),
            (_('Kind'), 2, 90),
            (_('Date'), 3, 120),
            (_('Title'), 4, 260),
            (_('Gramps URL'), 5, 260),
            (_('FS Date'), 6, 120),
            (_('FS Title'), 7, 260),
            (_('FS URL'), 8, 260),
            (_('Tags'), 9, 220),
            (_('Contributor'), 10, 120),
            (_('Modified'), 11, 150),
            (_('FS ID'), NOSORT, 0),
        ]
        model = ListModel(treeview, titles, list_mode="tree")
        return treeview, model

    def _fill_overview(self, model: ListModel, gr: Person, fsid: str):
        fs_person = gedcomx_v1.Person._index.get(fsid) or gedcomx_v1.Person()
        try:
            fs_compare.compare_fs_to_gramps(fs_person, gr, self.dbstate.db, model=model, dupdoc=True)
        except Exception as e:
            WarningDialog(_("Compare failed: {e}").format(e=str(e)))

    def _fill_notes(self, model: Any, gr: Person, fsid: str):
        self._ensure_notes_cached(fsid)
        fs_person = gedcomx_v1.Person._index.get(fsid) or gedcomx_v1.Person()
        if not fs_person:
            return
        fs_placeholder = '====================' if self.__class__.fs_Tree else _('Not connected to FamilySearch')
        note_handles = gr.get_note_list()
        fs_notes_remaining = fs_person.notes.copy()

        # Person notes
        for nh in note_handles:
            n = self.dbstate.db.get_note_from_handle(nh)
            note_text = n.get()
            title = _(n.type.xml_str())
            fs_text = fs_placeholder
            fs_title = ""
            gr_note_id = None
            try:
                for t in n.text.get_tags():
                    if t.name.name == "LINK" and t.value.startswith("_fsftid="):
                        gr_note_id = t.value[8:]
                        break
            except Exception:
                pass

            found = None
            if gr_note_id:
                for x in fs_notes_remaining:
                    if x.id == gr_note_id:
                        found = x; break
            if not found:
                for x in fs_notes_remaining:
                    if x.subject == title:
                        found = x; break

            if found:
                fs_notes_remaining.remove(found)
                fs_title = found.subject or ""
                fs_text = found.text or ""
                color = "green" if (fs_title == title and (fs_text == note_text or (note_text.startswith('\ufeff') and fs_text == note_text[1:]))) else "yellow"
            else:
                color = "yellow"
            model.add([color, _('Person'), title, note_text, fs_title, fs_text])

        for x in fs_notes_remaining:
            model.add(['yellow3', _('Person'), '', '============================', x.subject or '', x.text or ''])

        # Family (spouse) notes
        fs_couples_remaining = fs_person._spouses.copy()
        for fam_h in gr.get_family_handle_list():
            fam = self.dbstate.db.get_family_from_handle(fam_h)
            if not fam:
                continue
            spouse_h = fam.mother_handle if fam.mother_handle != gr.handle else fam.father_handle
            spouse = self.dbstate.db.get_person_from_handle(spouse_h) if spouse_h else None
            spouse_fsid = fs_utilities.get_fsftid(spouse) if spouse else ''
            fs_rel = None
            for rel in list(fs_couples_remaining):
                p1 = rel.person1.resourceId if rel.person1 else ''
                p2 = rel.person2.resourceId if rel.person2 else ''
                if spouse_fsid in (p1, p2):
                    fs_rel = rel
                    fs_couples_remaining.remove(rel)
                    break
            rel_notes: set = set()
            if fs_rel:
                rel_notes = fs_rel.notes.copy()

            for nh in fam.get_note_list():
                n = self.dbstate.db.get_note_from_handle(nh)
                note_text = n.get()
                title = _(n.type.xml_str())
                fs_text = fs_placeholder
                fs_title = ""
                gr_note_id = None
                try:
                    for t in n.text.get_tags():
                        if t.name.name == "LINK" and t.value.startswith("_fsftid="):
                            gr_note_id = t.value[8:]
                            break
                except Exception:
                    pass

                found = None
                if gr_note_id:
                    for x in rel_notes:
                        if x.id == gr_note_id:
                            found = x; break
                if not found:
                    for x in rel_notes:
                        if x.subject == title:
                            found = x; break

                if found:
                    rel_notes.remove(found)
                    fs_title = found.subject or ""
                    fs_text = found.text or ""
                    color = "green" if (fs_title == title and (fs_text == note_text or (note_text.startswith('\ufeff') and fs_text == note_text[1:]))) else "yellow"
                else:
                    color = "yellow"
                model.add([color, _('Family'), title, note_text, fs_title, fs_text])

            for x in rel_notes:
                model.add(['yellow3', _('Family'), '', '============================', x.subject or '', x.text or ''])

        for rel in fs_couples_remaining:
            for x in rel.notes:
                model.add(['yellow3', _('Family'), '', '============================', x.subject or '', x.text or ''])

    def _fill_sources(self, model: Any, gr: Person, fsid: str):
        self._ensure_sources_cached(fsid)

        fs_person = gedcomx_v1.Person._index.get(fsid) or gedcomx_v1.Person()
        fs_placeholder = '====================' if self.__class__.fs_Tree else _('Not connected to FamilySearch')

        source_meta = self._gather_sr_meta(fsid)

        fs_source_ids: dict[str, None] = {}
        for sr in getattr(fs_person, "sources", []) or []:
            fs_source_ids[getattr(sr, "descriptionId", "")] = None
        for rel in getattr(fs_person, "_spouses", []) or []:
            for sr in getattr(rel, "sources", []) or []:
                fs_source_ids[getattr(sr, "descriptionId", "")] = None

        for sdid in list(fs_source_ids.keys()):
            if not sdid:
                continue
            if sdid not in gedcomx_v1.SourceDescription._index:
                sd = gedcomx_v1.SourceDescription(); sd.id = sdid
                gedcomx_v1.SourceDescription._index[sdid] = sd
                self.__class__.fs_Tree.sourceDescriptions.add(sd)
        import fs_import
        fs_import.fetch_source_dates(self.__class__.fs_Tree)

        citation_handles: set[str] = set(gr.get_citation_list())
        for er in gr.get_event_ref_list():
            ev = self.dbstate.db.get_event_from_handle(er.ref)
            citation_handles.update(ev.get_citation_list())
        for fam_h in gr.get_family_handle_list():
            fam = self.dbstate.db.get_family_from_handle(fam_h)
            citation_handles.update(fam.get_citation_list())
            for er in fam.get_event_ref_list():
                ev = self.dbstate.db.get_event_from_handle(er.ref)
                citation_handles.update(ev.get_citation_list())

        for ch in citation_handles:
            c = self.dbstate.db.get_citation_from_handle(ch)
            src_gr = fs_import.IntermediateSource(); src_gr.from_gramps(self.dbstate.db, c)
            title = src_gr.citation_title
            note_text = (src_gr.note_text or '').strip()
            gr_url = src_gr.url
            date = fs_utilities.gramps_date_to_formal(c.date)
            sd_id = fs_utilities.get_fsftid(c)

            color = "white"
            fs_title = fs_date = fs_url = ""
            fs_text = fs_placeholder
            kind = ""
            tags_disp = ""
            contributor = ""
            modified = ""

            if sd_id and sd_id in gedcomx_v1.SourceDescription._index:
                sd = gedcomx_v1.SourceDescription._index[sd_id]
                src_fs = fs_import.IntermediateSource(); src_fs.from_fs(sd, None)
                fs_title = src_fs.citation_title; fs_text = src_fs.note_text; fs_date = str(src_fs.date); fs_url = src_fs.url
                meta = source_meta.get(sd_id, {})
                kind = meta.get("kind", "")
                tags_disp = self._pretty_tags(meta.get("tags", []))
                contributor = meta.get("contributor", "")
                modified = meta.get("modified", "")
                color = "orange"
                if (fs_date == date and fs_title == title and fs_url == gr_url and (fs_text or '').strip() == note_text):
                    color = "green"
                fs_source_ids.pop(sd_id, None)
            else:
                fs_date = fs_title = fs_url = "==="

            model.add([color, kind, date, title, gr_url, fs_date, fs_title, fs_url, tags_disp, contributor, modified, sd_id or ""])

        for sdid in list(fs_source_ids.keys()):
            if not sdid:
                continue
            sd = gedcomx_v1.SourceDescription._index.get(sdid)
            fs_title = ""
            if sd and getattr(sd, "titles", None):
                for t in sd.titles:
                    fs_title += t.value
            fs_date = getattr(sd, "_date", "") or ""
            fs_url = getattr(sd, "about", "") or ""
            meta = source_meta.get(sdid, {})
            kind = meta.get("kind", _("Mention"))
            tags_disp = self._pretty_tags(meta.get("tags", []))
            contributor = meta.get("contributor", "")
            modified = meta.get("modified", "")
            model.add(['yellow3', kind, '===', '===', '===', str(fs_date), fs_title or '', fs_url or '', tags_disp, contributor, modified, sdid])
