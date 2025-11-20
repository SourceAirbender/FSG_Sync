# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Tuple

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.db import DbTxn
from gramps.gen.lib import Citation, NoteType, Media, MediaRef
from gramps.gen.mime import get_type
from gramps.gen.utils.file import expand_media_path, relative_path

# Plugin deps
import fs_import
import fs_utilities

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

class SourceImportMixin:
    def _normalize_attr_name(self, s: str) -> str:
        return (s or "").strip().lower().replace("_", " ")

    def _set_attr_on_citation(self, cit: Citation, key: str, val: str):
        if not val:
            return
        key_norm = self._normalize_attr_name(key)
        try:
            updated = False
            for a in list(cit.get_attribute_list()):
                try:
                    t = a.get_type()
                    name_forms = []
                    if hasattr(t, "xml_str"):
                        name_forms.append(t.xml_str())
                    if t is not None:
                        name_forms.append(str(t))
                    if any(self._normalize_attr_name(n) == key_norm for n in name_forms if n):
                        a.set_value(val)
                        updated = True
                        break
                except Exception:
                    continue

            if not updated:
                from gramps.gen.lib import SrcAttribute
                a = SrcAttribute()
                a.set_type(key)
                a.set_value(val)
                cit.add_attribute(a)
        except Exception as e:
            print(f"Failed to set citation attribute '{key}': {e}")

    def _import_fs_sources(self, gr, items: List[Tuple]) -> int:
        existing: set[str] = set()
        cl: set[str] = set(gr.get_citation_list())
        for er in gr.get_event_ref_list():
            ev = self.dbstate.db.get_event_from_handle(er.ref)
            cl.update(ev.get_citation_list())
        for fam_h in gr.get_family_handle_list():
            fam = self.dbstate.db.get_family_from_handle(fam_h)
            cl.update(fam.get_citation_list())
            for er in fam.get_event_ref_list():
                ev = self.dbstate.db.get_event_from_handle(er.ref)
                cl.update(ev.get_citation_list())
        for ch in cl:
            c = self.dbstate.db.get_citation_from_handle(ch)
            fsid = fs_utilities.get_fsftid(c)
            if fsid:
                existing.add(fsid)

        imported = 0
        with DbTxn(_("Import FamilySearch sources"), self.dbstate.db) as txn:
            for tup in items:
                if len(tup) == 4:
                    sdid, fs_modified, contributor, final_kind = tup
                    image_paths = []
                    add_to_person = False
                elif len(tup) == 5:
                    sdid, fs_modified, contributor, final_kind, image_paths = tup
                    add_to_person = False
                else:
                    sdid, fs_modified, contributor, final_kind, image_paths, add_to_person = tup

                if sdid in existing:
                    if image_paths:
                        created = self._attach_images_to_existing_citations(sdid, image_paths, txn)
                        if add_to_person and created:
                            self._attach_media_to_person_by_handles(gr, created, txn)
                    continue

                before_handles = set(self.dbstate.db.iter_citation_handles())
                try:
                    fs_import.add_source(self.dbstate.db, txn, sdid, gr, gr.get_citation_list())
                except Exception as e:
                    print(f"fs_import.add_source failed for {sdid}: {e}")
                    continue

                new_targets = []
                for ch in self.dbstate.db.iter_citation_handles():
                    if ch in before_handles:
                        continue
                    c = self.dbstate.db.get_citation_from_handle(ch)
                    if fs_utilities.get_fsftid(c) == sdid:
                        new_targets.append(c)
                if not new_targets:
                    for ch in self.dbstate.db.iter_citation_handles():
                        if ch in before_handles:
                            continue
                        new_targets.append(self.dbstate.db.get_citation_from_handle(ch))

                all_created_handles = []
                for cit in new_targets:
                    self._set_attr_on_citation(cit, "FS Modified", fs_modified)
                    self._set_attr_on_citation(cit, "FS Contributor", contributor)
                    self._set_attr_on_citation(cit, "FS Kind", final_kind)
                    if image_paths:
                        created = self._attach_images_to_citation(cit, image_paths, txn)
                        all_created_handles.extend(created)
                    self.dbstate.db.commit_citation(cit, txn)

                if add_to_person and all_created_handles:
                    self._attach_media_to_person_by_handles(gr, all_created_handles, txn)

                imported += 1

            self.dbstate.db.commit_person(gr, txn)

        return imported

    def _attach_images_to_existing_citations(self, sdid: str, image_paths: List[str], txn: DbTxn) -> List[str]:
        created_all: List[str] = []
        for ch in self.dbstate.db.iter_citation_handles():
            c = self.dbstate.db.get_citation_from_handle(ch)
            if fs_utilities.get_fsftid(c) == sdid:
                created = self._attach_images_to_citation(c, image_paths, txn)
                created_all.extend(created)
                self.dbstate.db.commit_citation(c, txn)
        return created_all

    def _attach_images_to_citation(self, cit: Citation, image_paths: List[str], txn: DbTxn) -> List[str]:
        created_handles: List[str] = []
        if not image_paths:
            return created_handles

        try:
            base = expand_media_path(self.dbstate.db.get_mediapath(), self.dbstate.db)
        except Exception:
            base = None

        src = None
        try:
            if cit.source_handle:
                src = self.dbstate.db.get_source_from_handle(cit.source_handle)
        except Exception:
            src = None

        import os
        for p in image_paths:
            if not p:
                continue
            try:
                path_use = p
                if base and os.path.commonprefix([os.path.abspath(p), os.path.abspath(base)]) == os.path.abspath(base):
                    try:
                        path_use = relative_path(p, base)
                    except Exception:
                        path_use = p

                m = Media()
                m.set_path(path_use)
                try:
                    m.set_mime_type(get_type(p))
                except Exception:
                    pass

                try:
                    title = None
                    for nh in cit.note_list:
                        n = self.dbstate.db.get_note_from_handle(nh)
                        if n.type == NoteType.CITATION:
                            title = n.get().splitlines()[0][:120] if n.get() else None
                            break
                    if title:
                        m.set_description(title)
                except Exception:
                    pass

                self.dbstate.db.add_media(m, txn)
                self.dbstate.db.commit_media(m, txn)

                mr = MediaRef()
                mr.ref = m.handle

                attached = False
                try:
                    if hasattr(cit, "add_media_reference"):
                        cit.add_media_reference(mr)
                        attached = True
                    elif hasattr(cit, "add_media_ref"):
                        cit.add_media_ref(mr)
                        attached = True
                except Exception:
                    attached = False

                if not attached and src:
                    try:
                        if hasattr(src, "add_media_reference"):
                            src.add_media_reference(mr)
                            self.dbstate.db.commit_source(src, txn)
                            attached = True
                        elif hasattr(src, "add_media_ref"):
                            src.add_media_ref(mr)
                            self.dbstate.db.commit_source(src, txn)
                            attached = True
                    except Exception:
                        pass

                if not attached:
                    print("WARN: Could not attach media to citation or source; leaving Media unattached.")

                created_handles.append(m.handle)

            except Exception as e:
                print(f"Failed to attach media '{p}': {e}")

        return created_handles

    def _attach_media_to_person_by_handles(self, person, media_handles: List[str], txn: DbTxn):
        if not media_handles:
            return
        try:
            existing = {mr.ref for mr in person.get_media_list()}
        except Exception:
            existing = set()
        for mh in media_handles:
            if not mh or mh in existing:
                continue
            mr = MediaRef()
            mr.ref = mh
            try:
                if hasattr(person, "add_media_reference"):
                    person.add_media_reference(mr)
                elif hasattr(person, "add_media_ref"):
                    person.add_media_ref(mr)
            except Exception:
                continue
        self.dbstate.db.commit_person(person, txn)
