from __future__ import annotations

from gramps.gen.lib import (
    Citation,
    Note,
    NoteType,
    StyledTextTag,
    StyledTextTagType,
    StyledText,
    Source,
    SrcAttribute,
    Repository,
    RepoRef,
    RepositoryType,
    Url,
    UrlType,
    SourceMediaType,
)

from . import _

import fs_utilities
import tree

import gedcomx_v1


def fetch_source_dates(fs_tree):
    # SourceDescriptions in fs_tree with event dates and collection info, using the /service/tree/links/source/{id} endpoint.
    for sd in fs_tree.sourceDescriptions:
        if sd.id[:2] == "SD":
            continue
        if hasattr(sd, "_date"):
            continue
        sd._date = None
        sd._collectionUri = None
        sd._collection = None

        r = tree._fs_session.get_url(
            f"https://www.familysearch.org/service/tree/links/source/{sd.id}",
            {"Accept": "application/json"},
        )
        if r and r.text:
            data = r.json()
            e = data.get("event")
            if e:
                str_formal = e.get("eventDate")
                d = gedcomx_v1.Date()
                d.original = str_formal
                d.formal = gedcomx_v1.dateformal.DateFormal(str_formal)
                sd._date = d

            sd._collectionUri = data.get("fsCollectionUri")
            if sd._collectionUri:
                sd._collection = sd._collectionUri.removeprefix(
                    "https://www.familysearch.org/platform/records/collections/"
                )

            t = data.get("title")
            if t:
                if len(sd.titles):
                    next(iter(sd.titles)).value = t
                else:
                    tv = gedcomx_v1.TextValue()
                    tv.value = t
                    sd.titles.add(tv)

            u = data.get("uri")
            if u:
                sd.about = u.get("uri")

            n = data.get("notes")
            if len(sd.notes):
                next(iter(sd.notes)).text = n
            else:
                fn = gedcomx_v1.Note()
                fn.text = n
                sd.notes.add(fn)


class IntermediateSource:
    # Helper DTO bridging FS SourceDescription/SourceReference and Gramps Citation/Source.
    id: str | None = None
    repository_name: str | None = None
    source_title: str | None = None
    citation_title: str | None = None
    page_or_position: str | None = None
    confidence_label: str | None = None
    url: str | None = None
    date: any = None
    note_text: str | None = None
    collection: str | None = None
    collection_url: str | None = None

    def from_fs(self, fs_sd, fs_sr):
        self.id = fs_sd.id
        self.repository_name = "FamilySearch"
        self.source_title = "FamilySearch"
        self.citation_title = None
        self.page_or_position = None
        self.confidence_label = None
        self.url = fs_sd.about
        self.date = None
        self.note_text = "\n"
        self.collection = getattr(fs_sd, "_collection", None)
        self.collection_url = (
            "https://www.familysearch.org/search/collection/" + self.collection
            if self.collection
            else None
        )

        if len(fs_sd.titles):
            self.citation_title = next(iter(fs_sd.titles)).value
        fs_citation_value = None
        if len(fs_sd.citations):
            fs_citation_value = next(iter(fs_sd.citations)).value

        if fs_sd.resourceType not in ("FSREADONLY", "LEGACY", "DEFAULT", "IGI"):
            print("Unknown resourceType !!! :", str(fs_sd.resourceType))
        if fs_sd.resourceType == "LEGACY":
            self.source_title = "Legacy NFS Sources"

        if fs_sd.resourceType != "DEFAULT":
            self.repository_name = "FamilySearch"
            if fs_citation_value:
                parts = fs_citation_value.split('"')
                if len(parts) >= 3:
                    self.source_title = parts[1]
                    self.note_text = self.note_text + "\n".join(parts[2:])

        if len(fs_sd.notes):
            self.note_text = next(iter(fs_sd.notes)).text or ""

        if fs_citation_value and fs_sd.resourceType == "DEFAULT":
            lines = fs_citation_value.split("\n")
            for line in lines:
                if line.startswith(_("Repository")):
                    self.repository_name = line.removeprefix(
                        _("Repository") + " :"
                    ).strip()
                elif line.startswith(_("Source:")):
                    self.source_title = line.removeprefix(_("Source:")).strip()
                elif line.startswith(_("Volume/Page:")):
                    self.page_or_position = line.removeprefix(
                        _("Volume/Page:")
                    ).strip()
                elif line.startswith(_("Confidence:")):
                    self.confidence_label = line.removeprefix(
                        _("Confidence:")
                    ).strip()
            if not self.source_title and len(lines) >= 1:
                self.source_title = lines[0]

        if hasattr(fs_sd, "_date") and fs_sd._date:
            self.date = fs_sd._date

    """
    def to_fs(self, fs_sd, fs_sr):
        fs_sr.id = self.id
        fs_sr.description = (
            f"https://api.familysearch.org/platform/sources/descriptions/{self.id}"
        )
        fs_sd.id = self.id
        fs_sd.titles.add(self.citation_title)
        fs_note = gedcomx_v1.Note()
        fs_note.text = self.note_text
        fs_sd.notes.add(fs_note)
        fs_sd.about = self.url
        reference_text = _("Volume/Page:") + " " + str(self.page_or_position)
        if self.source_title:
            reference_text = (
                _("Source:") + " " + self.source_title + "\n" + reference_text
            )
            if self.repository_name:
                reference_text = (
                    _("Repository") + " : " + self.repository_name + "\n" + reference_text
                )
        reference_text = (
            reference_text
            + "\n"
            + _("Confidence:")
            + " "
            + str(self.confidence_label)
        )
        fsCitation = gedcomx_v1.SourceCitation
        fsCitation.value = reference_text
        fs_sd.citations.add(fsCitation)
        fs_sd.event = dict()
        fs_sd.event["eventDate"] = str(self.date)
    """
    def from_gramps(self, db, citation):
        self.id = fs_utilities.get_fsftid(citation)
        self.repository_name = None
        self.source_title = None
        self.citation_title = None
        self.page_or_position = citation.page
        self.confidence_label = None
        self.url = fs_utilities.get_internet_address(citation)
        str_formal = fs_utilities.gramps_date_to_formal(citation.date)
        self.date = gedcomx_v1.dateformal.DateFormal(str_formal)
        self.note_text = ""
        self.collection = None
        self.collection_url = None

        if citation.source_handle:
            s = db.get_source_from_handle(citation.source_handle)
            if s:
                self.source_title = s.title
                if len(s.reporef_list) > 0:
                    dh = s.reporef_list[0].ref
                    d = db.get_repository_from_handle(dh)
                    if d:
                        self.repository_name = d.name

        conf = citation.get_confidence_level()
        if conf == Citation.CONF_VERY_HIGH:
            self.confidence_label = _("Very High")
        elif conf == Citation.CONF_HIGH:
            self.confidence_label = _("High")
        elif conf == Citation.CONF_NORMAL:
            self.confidence_label = _("Normal")
        elif conf == Citation.CONF_LOW:
            self.confidence_label = _("Low")
        elif conf == Citation.CONF_VERY_LOW:
            self.confidence_label = _("Very Low")

        title_note_handle = None
        for nh in citation.note_list:
            n = db.get_note_from_handle(nh)
            if n.type == NoteType.CITATION:
                title_note_handle = nh
                text = n.get()
                pos = text.find("\n")
                if pos > 0:
                    self.note_text = text[pos + 1 :].strip(" \n")
                    self.citation_title = text[:pos]
                else:
                    self.citation_title = text
                break

        for nh in citation.note_list:
            if nh == title_note_handle:
                continue
            n = db.get_note_from_handle(nh)
            self.note_text += n.get()

    def to_gramps(self, db, txn, obj):
        # Repository
        repo_handle = None
        if self.repository_name:
            db.dbapi.execute(
                "select handle from repository where name=?", [self.repository_name]
            )
            row = db.dbapi.fetchone()
            if row and row[0]:
                repo_handle = row[0]
            else:
                r = Repository()
                r.set_name(self.repository_name)
                rtype = RepositoryType()
                rtype.set(RepositoryType.WEBSITE)
                r.set_type(rtype)
                if self.repository_name == "FamilySearch":
                    url = Url()
                    url.path = "https://www.familysearch.org/"
                    url.set_type(UrlType.WEB_HOME)
                    r.add_url(url)
                db.add_repository(r, txn)
                db.commit_repository(r, txn)
                repo_handle = r.handle

        # Source
        src = None
        if self.source_title and not src and self.collection:
            src = db.get_source_from_gramps_id("FS_coll_" + self.collection)
        if not src and self.source_title:
            db.dbapi.execute(
                "select handle from source where title=?", [self.source_title]
            )
            row = db.dbapi.fetchone()
            if row and row[0]:
                src = db.get_source_from_handle(row[0])

        if not src and self.source_title:
            src = Source()
            if self.collection:
                src.gramps_id = "FS_coll_" + self.collection
            src.set_title(self.source_title)
            if self.collection:
                attr = SrcAttribute()
                attr.set_type(_("Internet Address"))
                attr.set_value(self.collection_url)
                src.add_attribute(attr)
            db.add_source(src, txn)
            db.commit_source(src, txn)
            if repo_handle:
                rr = RepoRef()
                rr.ref = repo_handle
                rr.set_media_type(SourceMediaType.ELECTRONIC)
                src.add_repo_reference(rr)
            db.commit_source(src, txn)

        # Citation — reuse by _FSFTID if present
        found = False
        citation = None
        for ch in db.get_citation_handles():
            c = db.get_citation_from_handle(ch)
            for attr in c.get_attribute_list():
                if attr.get_type() == "_FSFTID" and attr.get_value() == self.id:
                    found = True
                    citation = c
                    print(" citation found _FSFTID=" + self.id)
                    break
            if found:
                break

        if not citation:
            print(" citation not found _FSFTID=" + self.id)
            citation = Citation()
            attr = SrcAttribute()
            attr.set_type("_FSFTID")
            attr.set_value(self.id)
            citation.add_attribute(attr)
            db.add_citation(citation, txn)

        if self.page_or_position:
            citation.set_page(self.page_or_position)

        if self.confidence_label:
            if self.confidence_label == _("Very High"):
                citation.set_confidence_level(Citation.CONF_VERY_HIGH)
            elif self.confidence_label == _("High"):
                citation.set_confidence_level(Citation.CONF_HIGH)
            elif self.confidence_label == _("Normal"):
                citation.set_confidence_level(Citation.CONF_NORMAL)
            elif self.confidence_label == _("Low"):
                citation.set_confidence_level(Citation.CONF_LOW)
            elif self.confidence_label == _("Very Low"):
                citation.set_confidence_level(Citation.CONF_VERY_LOW)

        if self.date:
            from fs_utilities import fs_date_to_gramps_date

            citation.date = fs_date_to_gramps_date(self.date)

        if src:
            citation.set_reference_handle(src.get_handle())

        if self.url:
            u0 = fs_utilities.get_internet_address(citation)
            if not u0:
                attr = SrcAttribute()
                attr.set_type(_("Internet Address"))
                attr.set_value(self.url)
                citation.add_attribute(attr)

        db.commit_citation(citation, txn)

        if self.citation_title or len(self.note_text or ""):
            note = None
            for nh in citation.note_list:
                n = db.get_note_from_handle(nh)
                if n.type == NoteType.CITATION:
                    note = n
            if not note:
                n = Note()
                tags = []
                n.set_type(NoteType(NoteType.CITATION))
                n.append(self.citation_title or "")
                n.append("\n\n")
                tags.append(
                    StyledTextTag(
                        StyledTextTagType.BOLD,
                        True,
                        [(0, len(self.citation_title or ""))],
                    )
                )
                n.append(self.note_text or "")
                n.text.set_tags(tags)
                db.add_note(n, txn)
                db.commit_note(n, txn)
                citation.add_note(n.handle)

        db.commit_citation(citation, txn)

        # Attach to obj if not already
        for ch in obj.citation_list:
            if ch == citation.handle:
                return citation
        obj.add_citation(citation.handle)
        return citation


def add_source(db, txn, sd_id, obj, existing_citation_handles):
    # Given a FS SourceDescription id, create/attach the matching Gramps Citation/Source.
    fs_sd = gedcomx_v1.SourceDescription._index.get(sd_id)
    if not fs_sd:
        return
    isrc = IntermediateSource()
    isrc.from_fs(fs_sd, None)
    citation = isrc.to_gramps(db, txn, obj)
    return citation
