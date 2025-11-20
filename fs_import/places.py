from __future__ import annotations

from gramps.gen.lib import Place, PlaceName, PlaceType, Url, UrlType, PlaceRef

from . import _

import fs_utilities
import tree
from constants import GEDCOMX_TO_GRAMPS_PLACES

import gedcomx_v1


def create_place(db, txn, fs_place, parent):
    # Create a Gramps Place from a FamilySearch PlaceDescription (fs_place),
    # link to its parent (if any), add FS URLs, set coordinates and type, commit
    place = Place()
    # Two URLs: FS description API and human page
    u1 = Url()
    u1.path = (
        f"https://api.familysearch.org/platform/places/description/{fs_place.id}"
    )
    u1.type = UrlType("FamilySearch")
    u2 = Url()
    u2.path = fs_place.links["place"].href.removesuffix("?flag=fsh")
    u2.type = UrlType("FamilySearch")
    tmp = Place()
    tmp.add_url(u1)
    tmp.add_url(u2)
    place._merge_url_list(tmp)

    name = PlaceName()
    name.set_value(fs_place.display.name)
    place.set_name(name)
    place.set_title(fs_place.display.name)

    if hasattr(fs_place, "type"):
        mapped = GEDCOMX_TO_GRAMPS_PLACES.get(fs_place.type)
        ptype = PlaceType(mapped) if mapped else None
    else:
        ptype = None

    # Coordinates (stored as strings in Gramps)
    place.lat = str(fs_place.latitude)
    place.long = str(fs_place.longitude)

    # Fallback type inference by hierarchy if not mapped
    if not ptype:
        if not parent:
            ptype = PlaceType(1)
        else:
            if parent.place_type == PlaceType(1):
                ptype = PlaceType(9)
            elif parent.place_type == PlaceType(9):
                ptype = PlaceType(10)
            elif parent.place_type == PlaceType(10):
                ptype = PlaceType(14)
            elif parent.place_type == PlaceType(14):
                ptype = PlaceType(20)

    if parent:
        pref = PlaceRef()
        pref.ref = parent.handle
        place.add_placeref(pref)

    place.set_type(ptype)
    db.add_place(place, txn)
    db.commit_place(place, txn)

    fs_place._handle = place.handle
    if fs_utilities.FS_INDEX_PLACES:
        fs_utilities.FS_INDEX_PLACES[u1.path] = place.handle
        fs_utilities.FS_INDEX_PLACES[u2.path] = place.handle
    return place


def get_place_by_id(db, fs_place):
    # Find the Gramps Place from a FamilySearch place id (or cached links).
    if (
        not getattr(fs_place, "id", None)
        and getattr(fs_place, "description", None)
        and fs_place.description[:1] == "#"
    ):
        fs_place.id = fs_place.description[1:]
    if not getattr(fs_place, "id", None):
        return None

    api_url = (
        f"https://api.familysearch.org/platform/places/description/{fs_place.id}"
    )
    if hasattr(fs_place, "links") and fs_place.links and fs_place.links.get("place"):
        human_url = fs_place.links["place"].href.removesuffix("?flag=fsh")
    else:
        human_url = None

    # Fast path via global cache
    if fs_utilities.FS_INDEX_PLACES:
        handle = fs_utilities.FS_INDEX_PLACES.get(api_url) or (
            human_url and fs_utilities.FS_INDEX_PLACES.get(human_url)
        )
        if handle:
            try:
                return db.get_place_from_handle(handle)
            except Exception:
                pass
        else:
            return None

    # Build FSID map on first use
    if not fs_utilities.FS_INDEX_PLACES:
        print(_("Building FSID list for places"))
        fs_utilities.FS_INDEX_PLACES = {}
        for handle in db.get_place_handles():
            place = db.get_place_from_handle(handle)
            for url in place.urls:
                if str(url.type) == "FamilySearch":
                    fs_utilities.FS_INDEX_PLACES[url.path] = handle

    handle = fs_utilities.FS_INDEX_PLACES.get(api_url)
    return db.get_place_from_handle(handle) if handle else None


def add_place(db, txn, fs_place):
    # Ensure a FS place exists in Gramps: reuse by cached handle or lookup,
    # else fetch from FS and create it (recursing parent first).
    if not hasattr(fs_place, "_handle"):
        fs_place._handle = None
    if fs_place._handle:
        try:
            return db.get_place_from_handle(fs_place._handle)
        except Exception:
            pass

    # Lookup prior to network
    gr_place = get_place_by_id(db, fs_place)
    if gr_place:
        fs_place._handle = gr_place.handle
        return gr_place

    if not getattr(fs_place, "id", None):
        return None

    print("add_place:" + fs_place.id)
    endpoint = f"/platform/places/description/{fs_place.id}"
    r = tree._fs_session.get_url(endpoint, {"Accept": "application/json,*/*"})
    if not (r and r.status_code == 200):
        if r:
            print("WARNING: Status code:", r.status_code)
        return None

    try:
        data = r.json()
    except Exception as e:
        print(f"WARNING: corrupted file from {endpoint}, error: {e}")
        print(r.content)
        return None

    if "places" not in data:
        return None

    g = gedcomx_v1.Gedcomx()
    gedcomx_v1.deserialize_json(g, data)
    fs_place_id = data["places"][0]["id"]

    fs_desc = gedcomx_v1.PlaceDescription._index.get(fs_place_id)
    if fs_desc.jurisdiction:
        parent_id = fs_desc.jurisdiction.resourceId
        fs_parent = gedcomx_v1.PlaceDescription._index.get(parent_id)
        gr_parent = add_place(db, txn, fs_parent)
    else:
        gr_parent = None

    # Handle merged places
    if fs_place_id != fs_place.id:
        existing = get_place_by_id(db, fs_desc)
        if not existing:
            existing = add_place(db, txn, fs_desc)
        u1 = Url()
        u1.path = (
            f"https://api.familysearch.org/platform/places/description/{fs_place.id}"
        )
        u1.type = UrlType("FamilySearch")
        u2 = Url()
        u2.path = fs_desc.links["place"].href.removesuffix("?flag=fsh")
        u2.type = UrlType("FamilySearch")
        tmp = Place()
        tmp.add_url(u1)
        tmp.add_url(u2)
        existing._merge_url_list(tmp)
        if fs_utilities.FS_INDEX_PLACES:
            fs_utilities.FS_INDEX_PLACES[u1.path] = existing.handle
            fs_utilities.FS_INDEX_PLACES[u2.path] = existing.handle
        db.commit_place(existing, txn)
        return existing

    return create_place(db, txn, fs_desc, gr_parent)
