from __future__ import annotations

from gramps.gen.lib import Note, NoteType, StyledText, StyledTextTag, StyledTextTagType

from . import _


def add_note(db, txn, fs_note, existing_note_handles):
    # Add a Gramps Note from a FS note if it doesn't already exist (matched by title/type and a LINK tag storing _fsftid).
    # Try to find an existing one by subject + _fsftid
    for nh in existing_note_handles:
        n = db.get_note_from_handle(nh)
        title = _(n.type.xml_str())
        if title == fs_note.subject:
            for tag in n.text.get_tags():
                if tag.name == StyledTextTagType.LINK:
                    fs_id = tag.value
                    if title == fs_note.subject and fs_id == "_fsftid=" + fs_note.id:
                        return n

    gr_note = Note()
    gr_note.set_format(Note.FORMATTED)
    gr_note.set_type(NoteType(fs_note.subject))
    if fs_note.id:
        # Store FSFTID in a LINK tag on the first char (with an invisible char at start)
        tags = [
            StyledTextTag(
                StyledTextTagType.LINK,
                "_fsftid=" + fs_note.id,
                [(0, 1)],
            )
        ]
        gr_note.set_styledtext(StyledText("\ufeff" + (fs_note.text or ""), tags))

    db.add_note(gr_note, txn)
    db.commit_note(gr_note, txn)
    return gr_note
