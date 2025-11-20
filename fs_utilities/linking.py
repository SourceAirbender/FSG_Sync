from __future__ import annotations
from typing import Optional

from gramps.gen.db import DbTxn
from gramps.gen.lib import Attribute, SrcAttribute, Person, Event, Citation
from gramps.gen.const import GRAMPS_LOCALE as glocale

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

# Import indexes so we can keep them in sync when a Person is updated
from .index import FS_INDEX_PEOPLE


def link_gramps_fs_id(db, gr_object, fsid: str) -> None:
    """Attach or update the `_FSFTID` attribute on a Gramps object and commit.
    Updates global `FS_INDEX_PEOPLE` if the object is a Person.
    """
    if not fsid or gr_object is None:
        return

    # Prepare transaction context
    internal_txn = False
    if getattr(db, "transaction", None):
        txn = db.transaction
    else:
        internal_txn = True
        txn = DbTxn(_("FamilySearch tags"), db)

    # Find existing attribute or create a new one
    existing_attr: Optional[Attribute] = None
    for a in gr_object.get_attribute_list():
        if a.get_type() == "_FSFTID":
            existing_attr = a
            if a.get_value() != fsid:
                a.set_value(fsid)
            break

    if existing_attr is None:
        if isinstance(gr_object, Citation):
            attr = SrcAttribute()
        else:
            attr = Attribute()
        attr.set_type("_FSFTID")
        attr.set_value(fsid)
        gr_object.add_attribute(attr)

    # Commit by type
    if isinstance(gr_object, Person):
        db.commit_person(gr_object, txn)
        # Keep the index in sync
        FS_INDEX_PEOPLE[fsid] = gr_object.get_handle()
    elif isinstance(gr_object, Event):
        db.commit_event(gr_object, txn)
    elif isinstance(gr_object, Citation):
        db.commit_citation(gr_object, txn)
    else:
        print(
            "fs_utilities.link_gramps_fs_id: unsupported class:",
            gr_object.__class__.__name__,
        )

    if internal_txn:
        db.transaction_commit(txn)
