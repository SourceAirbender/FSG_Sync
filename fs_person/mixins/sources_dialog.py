# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, List, Tuple

# GTK
from gi.repository import Gtk
try:
    from gi.repository import Pango
except Exception:
    Pango = None

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.dialog import OkDialog, WarningDialog

# Plugin deps
import fs_import
import fs_utilities
 
import gedcomx_v1

_has_img_picker = False
try:
    import fs_source_image
    _has_img_picker = True
except Exception:
    # UI will hide/disable image actions when false
    pass
    
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


class SourcesDialogMixin:
    def _import_sources_dialog(self, gr, fsid: str):
        items = self._collect_fs_sources(fsid)
        if not items:
            OkDialog(_("No FamilySearch sources found to import."))
            return

        by_sdid: Dict[str, List] = {}
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
            sdid = fs_utilities.get_fsftid(c)
            if sdid:
                by_sdid.setdefault(sdid, []).append(c)

        def detect_color_for_sdid(sdid: str) -> str:
            if sdid not in by_sdid:
                return "yellow3"
            sd = gedcomx_v1.SourceDescription._index.get(sdid)
            if not sd:
                return "orange"
            src_fs = fs_import.IntermediateSource(); src_fs.from_fs(sd, None)
            fs_title = src_fs.citation_title or ""
            fs_text = (src_fs.note_text or "")
            fs_date = str(src_fs.date) if getattr(src_fs, "date", "") else ""
            fs_url = src_fs.url or ""
            for c in by_sdid.get(sdid, []):
                src_gr = fs_import.IntermediateSource(); src_gr.from_gramps(self.dbstate.db, c)
                title = src_gr.citation_title or ""
                note_text = (src_gr.note_text or "").strip()
                gr_url = src_gr.url or ""
                date = fs_utilities.gramps_date_to_formal(c.date)
                if (fs_date == date and fs_title == title and fs_url == gr_url and (fs_text or "").strip() == note_text):
                    return "green"
            return "orange"

        dlg = Gtk.Dialog(title=_("Import FamilySearch sources"), transient_for=self.uistate.window, flags=0)
        dlg.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dlg.add_button(_("Import selected"), Gtk.ResponseType.OK)
        box = dlg.get_content_area()
        box.set_margin_top(8); box.set_margin_bottom(8); box.set_margin_start(8); box.set_margin_end(8)

        images_by_sdid: Dict[str, List[str]] = {}
        last_dir = self.CONFIG.get("preferences.fs_image_download_dir") or ""

        store = Gtk.ListStore(bool, str, str, str, str, str, str, str, str, str, str, int, bool)
        for sdid, auto_kind, title, date_s, url, tags, contributor in items:
            color = detect_color_for_sdid(sdid)
            store.append([True, color, "", auto_kind or "", "Auto", title or "", date_s or "", url or "", tags or "", contributor or "", sdid, 0, True])

        treeview = Gtk.TreeView(model=store)
        treeview.set_activate_on_single_click(True)

        toggle = Gtk.CellRendererToggle()
        toggle.connect("toggled", lambda _w, path: store[path].__setitem__(0, not store[path][0]))
        col0 = Gtk.TreeViewColumn(_("Import"), toggle, active=0)

        color_cell = Gtk.CellRendererText()
        color_col = Gtk.TreeViewColumn(_("Color"))
        color_col.pack_start(color_cell, True)
        color_col.add_attribute(color_cell, "text", 2)
        color_col.add_attribute(color_cell, "cell-background", 1)
        color_col.set_min_width(40)
        color_col.set_fixed_width(40)

        col_auto = Gtk.TreeViewColumn(_("Detected"), Gtk.CellRendererText(), text=3)

        kind_model = Gtk.ListStore(str)
        for v in ("Auto", "Direct", "Mention"):
            kind_model.append([v])
        cell_combo = Gtk.CellRendererCombo()
        cell_combo.set_property("editable", True)
        cell_combo.set_property("model", kind_model)
        cell_combo.set_property("text-column", 0)
        cell_combo.set_property("has-entry", False)

        def on_combo_edited(_cell, path, new_text):
            if new_text in ("Auto", "Direct", "Mention"):
                store[path][4] = new_text

        cell_combo.connect("edited", on_combo_edited)
        col_kind = Gtk.TreeViewColumn(_("Import as"), cell_combo, text=4)

        col_title = Gtk.TreeViewColumn(_("Title"), Gtk.CellRendererText(), text=5)
        col_date  = Gtk.TreeViewColumn(_("FS Date"), Gtk.CellRendererText(), text=6)
        col_url   = Gtk.TreeViewColumn(_("URL"), Gtk.CellRendererText(), text=7)
        col_tags  = Gtk.TreeViewColumn(_("Tags"), Gtk.CellRendererText(), text=8)
        col_con   = Gtk.TreeViewColumn(_("Contributor"), Gtk.CellRendererText(), text=9)

        col_img_ct = Gtk.TreeViewColumn(_("Images"), Gtk.CellRendererText(), text=11)

        cr_person = Gtk.CellRendererToggle()
        def _on_person_gallery_toggled(_w, path):
            store[path][12] = not store[path][12]
        cr_person.connect("toggled", _on_person_gallery_toggled)
        col_person = Gtk.TreeViewColumn(_("To Person gallery"), cr_person, active=12)

        action_cell = Gtk.CellRendererText()
        if Pango:
            action_cell.set_property("underline", Pango.Underline.SINGLE)
            action_cell.set_property("foreground", "steelblue")
        action_col = Gtk.TreeViewColumn(_("Actions"), action_cell, text=2)

        def _action_cell_data_func(_col, cell, model, itr, _data=None):
            cell.set_property("text", _("Manage Images…"))
        action_col.set_cell_data_func(action_cell, _action_cell_data_func)

        for col in (col0, color_col, col_auto, col_kind, col_title, col_date, col_url, col_tags, col_con, col_img_ct, col_person, action_col):
            treeview.append_column(col)

        def manage_images_for_sdid(sdid: str, url_for_picker: str) -> int:
            nonlocal last_dir
            import os, re

            def _sanitize_base(name: str) -> str:
                base = (name or "").strip()
                if not base:
                    base = "image"
                base = re.sub(r'[\\\/<>:"|?*\n\r\t]+', '_', base)
                return base

            def _unique_path(dirpath: str, base: str, ext: str) -> str:
                candidate = os.path.join(dirpath, base + ext)
                if not os.path.exists(candidate):
                    return candidate
                i = 1
                while True:
                    candidate = os.path.join(dirpath, f"{base} ({i}){ext}")
                    if not os.path.exists(candidate):
                        return candidate
                    i += 1

            imgs = images_by_sdid.setdefault(sdid, [])

            dlg2 = Gtk.Dialog(title=_("Manage images"), transient_for=dlg, flags=0)
            dlg2.add_button(_("Close"), Gtk.ResponseType.CLOSE)

            if _has_img_picker:
                btn_add = Gtk.Button(label=_("Add images…"))
                dlg2.get_action_area().pack_start(btn_add, False, False, 0)

            btn_rename = Gtk.Button(label=_("Rename files"))
            dlg2.get_action_area().pack_start(btn_rename, False, False, 0)

            box = dlg2.get_content_area()
            box.set_margin_top(8); box.set_margin_bottom(8); box.set_margin_start(8); box.set_margin_end(8)

            model = Gtk.ListStore(str, str, str, str)

            def _split_path(p: str):
                d, fname = os.path.split(p)
                base, ext = os.path.splitext(fname)
                return d, base, ext or ""

            for p in imgs:
                d, b, e = _split_path(p)
                model.append([d, b, e, p])

            tv = Gtk.TreeView(model=model)

            cr_base = Gtk.CellRendererText()
            cr_base.set_property("editable", True)
            def on_base_edited(_cell, path, new_text):
                row = model[path]
                row[1] = _sanitize_base(new_text)
            cr_base.connect("edited", on_base_edited)
            col_base = Gtk.TreeViewColumn(_("Filename (without extension)"), cr_base, text=1)

            cr_ext = Gtk.CellRendererText()
            col_ext = Gtk.TreeViewColumn(_("Extension"), cr_ext, text=2)

            tv.append_column(col_base)
            tv.append_column(col_ext)

            sw = Gtk.ScrolledWindow()
            sw.set_min_content_height(260)
            sw.add(tv)

            help_lbl = Gtk.Label()
            help_lbl.set_xalign(0)
            help_lbl.set_line_wrap(True)
            help_lbl.set_text(_("Tips:\n• Double-click the name to edit.\n• Extensions are preserved.\n• If a file with the new name exists, a numeric suffix will be added."))

            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            v.pack_start(help_lbl, False, False, 0)
            v.pack_start(sw, True, True, 0)
            box.add(v)

            def _refresh_imgs_from_model():
                new_list = []
                for d, b, e, _old in model:
                    import os
                    new_list.append(os.path.join(d, b + e))
                return new_list

            def do_add(_btn):
                nonlocal last_dir
                if not _has_img_picker:
                    return
                try:
                    saved = fs_source_image.pick_images(url_for_picker, parent_window=dlg2, start_dir=last_dir, title=_("Add Source Image"))
                except Exception as e:
                    WarningDialog(_("Could not open image picker:\n{e}").format(e=str(e)))
                    return
                if not saved:
                    return
                for p in saved:
                    d, b, e = _split_path(p)
                    model.append([d, b, e, p])
                try:
                    last_dir_local = os.path.dirname(saved[0])
                except Exception:
                    last_dir_local = last_dir
                if last_dir_local:
                    last_dir = last_dir_local
                    self.CONFIG.set("preferences.fs_image_download_dir", last_dir)
                    self.CONFIG.save()

            def do_rename(_btn):
                import os
                for row in list(model):
                    d, b_new, e, full_old = row[:]
                    d = d or ""
                    b_new = (b_new or "").strip()
                    d_old, fname_old = os.path.split(full_old)
                    base_old, ext_old = os.path.splitext(fname_old)
                    if d_old and not d:
                        d = d_old
                    if not e:
                        e = ext_old
                    if base_old == b_new and d_old == d and ext_old == e:
                        continue
                    def _unique_path(dirpath: str, base: str, ext: str) -> str:
                        candidate = os.path.join(dirpath, base + ext)
                        if not os.path.exists(candidate):
                            return candidate
                        i = 1
                        while True:
                            candidate = os.path.join(dirpath, f"{base} ({i}){ext}")
                            if not os.path.exists(candidate):
                                return candidate
                            i += 1
                    target = _unique_path(d or d_old, b_new, e)
                    try:
                        os.rename(full_old, target)
                        d_new, fname_new = os.path.split(target)
                        base_new, ext_new = os.path.splitext(fname_new)
                        row[0] = d_new
                        row[1] = base_new
                        row[2] = ext_new
                        row[3] = target
                    except Exception as ex:
                        WarningDialog(_("Rename failed for:\n{p}\n\n{err}").format(p=full_old, err=str(ex)))
                images_by_sdid[sdid] = _refresh_imgs_from_model()

            if _has_img_picker:
                btn_add.connect("clicked", do_add)
            btn_rename.connect("clicked", do_rename)

            dlg2.show_all()
            dlg2.run()
            dlg2.destroy()

            images_by_sdid[sdid] = _refresh_imgs_from_model()
            return len(images_by_sdid[sdid])

        def on_row_activated(tv, path, column):
            if column is not action_col:
                return
            row = store[path]
            sdid = row[10]
            source_url = row[7] or ""
            new_count = manage_images_for_sdid(sdid, source_url)
            row[11] = new_count

        treeview.connect("row-activated", on_row_activated)

        sw = Gtk.ScrolledWindow(); sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC); sw.set_min_content_height(360)
        sw.add(treeview)

        btn_all = Gtk.CheckButton.new_with_label(_("Select all"))
        btn_all.set_active(True)

        def on_all_toggled(btn):
            val = btn.get_active()
            for row in store:
                row[0] = val

        btn_all.connect("toggled", on_all_toggled)

        legend = Gtk.Label(
            label=_("Tip: Click “Actions → Manage Images…” to add/rename files before import.\n"
                    "Downloaded files are remembered and will be attached on import.")
        )
        legend.set_xalign(0)
        legend.set_line_wrap(True)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        v.pack_start(btn_all, False, False, 0)
        v.pack_start(legend, False, False, 0)
        v.pack_start(sw, True, True, 0)
        box.add(v)

        dlg.show_all()
        resp = dlg.run()
        if resp != Gtk.ResponseType.OK:
            dlg.destroy(); return

        source_meta = self._gather_sr_meta(fsid)

        selected_items = []
        for row in store:
            if not row[0]:
                continue
            sdid = row[10]
            auto_kind = row[3] or "Mention"
            chosen = row[4] or "Auto"
            final_kind = auto_kind if chosen == "Auto" else chosen
            contributor = row[9] or ""
            modified = (source_meta.get(sdid, {}) or {}).get("modified", "")
            img_list = images_by_sdid.get(sdid, [])[:]
            add_to_person = bool(row[12])
            selected_items.append((sdid, modified, contributor, final_kind, img_list, add_to_person))

        dlg.destroy()
        if not selected_items:
            return

        count = self._import_fs_sources(gr, selected_items)
        OkDialog(_("{n} source(s) imported.").format(n=count))

    def _collect_fs_sources(self, fsid: str) -> List[Tuple[str, str, str, str, str, str, str]]:
        self._ensure_sources_cached(fsid)
        fs_person = gedcomx_v1.Person._index.get(fsid)
        if not fs_person:
            return []

        meta = self._gather_sr_meta(fsid)

        sdids: set[str] = set()
        for sr in getattr(fs_person, "sources", []) or []:
            sdids.add(getattr(sr, "descriptionId", ""))
        for rel in getattr(fs_person, "_spouses", []) or []:
            for sr in getattr(rel, "sources", []) or []:
                sdids.add(getattr(sr, "descriptionId", ""))

        for sdid in list(sdids):
            if not sdid:
                continue
            if sdid not in gedcomx_v1.SourceDescription._index:
                sd = gedcomx_v1.SourceDescription(); sd.id = sdid
                gedcomx_v1.SourceDescription._index[sdid] = sd
                self.__class__.fs_Tree.sourceDescriptions.add(sd)
        fs_import.fetch_source_dates(self.__class__.fs_Tree)

        out: List[Tuple[str, str, str, str, str, str, str]] = []
        for sdid in sdids:
            if not sdid:
                continue
            sd = gedcomx_v1.SourceDescription._index.get(sdid)
            if not sd:
                continue
            isrc = fs_import.IntermediateSource(); isrc.from_fs(sd, None)
            title = isrc.citation_title or ""
            date_s = str(isrc.date) if getattr(isrc, "date", "") else ""
            url = isrc.url or ""
            m = meta.get(sdid, {})
            auto_kind = m.get("kind", "Mention")
            tags_disp = self._pretty_tags(m.get("tags", []))
            contributor = m.get("contributor", "")
            out.append((sdid, auto_kind, title, date_s, url, tags_disp, contributor))
        return out
