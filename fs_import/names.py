from __future__ import annotations

from gramps.gen.lib import Name, NameType

from .notes import add_note


def add_name(db, txn, fs_name, gr_person):
    # Add one Name from FS to a Gramps Person (type mapped; notes preserved).
    name = Name()
    if fs_name.type == "http://gedcomx.org/MarriedName":
        name.set_type(NameType(NameType.MARRIED))
    elif fs_name.type == "http://gedcomx.org/AlsoKnownAs":
        name.set_type(NameType(NameType.AKA))
    elif fs_name.type == "http://gedcomx.org/BirthName":
        name.set_type(NameType(NameType.BIRTH))
    else:
        #nickName, AdoptiveName, FormalName, ReligiousName, etc
        name.set_type(NameType(NameType.CUSTOM))

    name.set_first_name(fs_name.akGiven())
    s = name.get_primary_surname()
    s.set_surname(fs_name.akSurname())

    for fs_note in fs_name.notes:
        note = add_note(db, txn, fs_note, name.note_list)
        name.add_note(note.handle)

    if getattr(fs_name, "preferred", False):
        gr_person.set_primary_name(name)
    else:
        gr_person.add_alternate_name(name)


def add_names(db, txn, fs_person, gr_person):
    for fs_name in fs_person.names:
        add_name(db, txn, fs_name, gr_person)
