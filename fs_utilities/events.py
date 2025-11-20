from __future__ import annotations
from typing import Optional

from gramps.gen.lib import Event, Person
from gramps.gen.lib import EventRoleType


def get_fs_fact(person, fact_type):
    # Return the first FamilySearch fact on `person` matching `fact_type`
    if not person:
        return None
    for fact in getattr(person, "facts", []) or []:
        if getattr(fact, "type", None) == fact_type:
            return fact
    return None


def get_gramps_event(db, person: Optional[Person], event_type) -> Optional[Event]:
    # Return the first Gramps Event of `event_type` where role is PRIMARY
    if not person:
        return None
    for event_ref in person.get_event_ref_list():
        try:
            if int(event_ref.get_role()) != EventRoleType.PRIMARY:
                continue
        except Exception:
            continue
        event = db.get_event_from_handle(event_ref.ref)
        if event and event.get_type() == event_type:
            return event
    return None
