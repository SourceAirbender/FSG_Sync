from __future__ import annotations
from typing import Optional

from gramps.gen.const import GRAMPS_LOCALE as glocale

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


def _iter_attrs(gr_obj):
    # Helper: robustly yield attributes from a Gramps object

    # Prefers get_attribute_list() when available; falls back to attribute_list.
    if not gr_obj:
        return []
    attrs = []
    try:
        if hasattr(gr_obj, "get_attribute_list"):
            attrs = gr_obj.get_attribute_list() or []
        else:
            attrs = getattr(gr_obj, "attribute_list", []) or []
    except Exception:
        attrs = getattr(gr_obj, "attribute_list", []) or []
    return attrs


def get_fsftid(gr_obj) -> str:
    # Return the value of the `_FSFTID` attribute in a Gramps object, else ''
    if not gr_obj:
        return ""
    for attr in _iter_attrs(gr_obj):
        if attr.get_type() == "_FSFTID":
            return attr.get_value() or ""
    return ""


def get_internet_address(gr_obj) -> Optional[str]:
    # Return the value of the 'Internet Address' attribute, if present
    if not gr_obj:
        return None
    for attr in _iter_attrs(gr_obj):
        if attr.get_type() == _("Internet Address"):
            return attr.get_value()
    return None
