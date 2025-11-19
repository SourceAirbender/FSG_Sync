from __future__ import annotations
from typing import Dict, Optional

from gramps.gen.lib import Person
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.dialog import QuestionDialog2

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

# Public module-level caches
FS_INDEX_PEOPLE: Dict[str, str] = {}
FS_INDEX_PLACES: Dict[str, str] = {}


def build_fs_index(caller, progress, total_steps: int) -> None:
    """Build fast lookup indexes for FSFTID → handle.

    Creates two dictionaries that map FamilySearch identifiers to Gramps handles:
      * FS_INDEX_PEOPLE[fsid] = person_handle
      * FS_INDEX_PLACES[url]  = place_handle  (only for URLs tagged "FamilySearch")
    """
    global FS_INDEX_PEOPLE, FS_INDEX_PLACES

    db = caller.dbstate.db

    # Phase 1: People (FSFTID index)
    dup_warning = True
    # mutate in place so all aliases (e.g., fs_utilities.FS_INDEX_PEOPLE) stay valid
    FS_INDEX_PEOPLE.clear()

    progress.set_pass(
        _(f"Build FSID list (1/{total_steps})"),
        db.get_number_of_people(),
    )
    for person_handle in db.get_person_handles():
        progress.step()
        person: Optional[Person] = db.get_person_from_handle(person_handle)
        fsid = get_fsftid(person) if person else ""
        if not fsid:
            continue
        if fsid in FS_INDEX_PEOPLE:
            print(_("FamilySearch duplicate ID: %s ") % (fsid,))
            if dup_warning:
                qd = QuestionDialog2(
                    _("Duplicate FSFTID"),
                    _("FamilySearch duplicate ID: %s ") % (fsid,),
                    _("_Continue warning"),
                    _("_Stop warning"),
                    parent=getattr(caller.uistate, "window", None),
                )
                if not qd.run():
                    dup_warning = False
        else:
            FS_INDEX_PEOPLE[fsid] = person_handle

    # Phase 2: Places (familysearch URL → handle index)
    FS_INDEX_PLACES.clear()
    progress.set_pass(
        _(f"Build FSID list for places (2/{total_steps})"),
        db.get_number_of_places(),
    )
    for place_handle in db.get_place_handles():
        progress.step()
        place = db.get_place_from_handle(place_handle)
        for url in getattr(place, "urls", []) or []:
            if str(getattr(url, "type", "")) == "FamilySearch":
                FS_INDEX_PLACES[getattr(url, "path", "")] = place_handle


# Local import at end to avoid circular import during Gramps plugin load
from .attributes import get_fsftid
