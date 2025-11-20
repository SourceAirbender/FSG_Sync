<<<<<<< HEAD
# Copyright © 2024 Gabriel Rios

# License: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
#
# gedcomx_v1.vocab — GedcomX vocabularies and helpers
#
#
# Sources:
# - http://gedcomx.org/EventType
# - http://gedcomx.org/RelationshipType
# - http://gedcomx.org/FactType


from __future__ import annotations

from typing import Dict, Set

GX = "http://gedcomx.org/"


EVENT_TYPES: Dict[str, str] = {
    "Adoption":               GX + "Adoption",
    "AdultChristening":       GX + "AdultChristening",
    "Annulment":              GX + "Annulment",
    "Baptism":                GX + "Baptism",
    "BarMitzvah":             GX + "BarMitzvah",
    "BatMitzvah":             GX + "BatMitzvah",
    "Birth":                  GX + "Birth",
    "Blessing":               GX + "Blessing",
    "Burial":                 GX + "Burial",
    "Census":                 GX + "Census",
    "Christening":            GX + "Christening",
    "Circumcision":           GX + "Circumcision",
    "Confirmation":           GX + "Confirmation",
    "Cremation":              GX + "Cremation",
    "Death":                  GX + "Death",
    "Divorce":                GX + "Divorce",
    "DivorceFiling":          GX + "DivorceFiling",
    "Education":              GX + "Education",
    "Emigration":             GX + "Emigration",
    "Engagement":             GX + "Engagement",
    "FirstCommunion":         GX + "FirstCommunion",
    "Funeral":                GX + "Funeral",
    "Immigration":            GX + "Immigration",
    "LandTransaction":        GX + "LandTransaction",
    "Marriage":               GX + "Marriage",
    "MarriageBanns":          GX + "MarriageBanns",
    "MarriageContract":       GX + "MarriageContract",
    "MarriageLicense":        GX + "MarriageLicense",
    "MarriageNotice":         GX + "MarriageNotice",
    "MarriageSettlement":     GX + "MarriageSettlement",
    "MilitaryAward":          GX + "MilitaryAward",
    "MilitaryDraftRegistration": GX + "MilitaryDraftRegistration",
    "MilitaryInduction":      GX + "MilitaryInduction",
    "MilitaryService":        GX + "MilitaryService",
    "Mission":                GX + "Mission",
    "Naturalization":         GX + "Naturalization",
    "Ordination":             GX + "Ordination",
    "Pardon":                 GX + "Pardon",
    "Probate":                GX + "Probate",
    "Residence":              GX + "Residence",
    "Retirement":             GX + "Retirement",
    "Stillbirth":             GX + "Stillbirth",
    "Will":                   GX + "Will",
}

# --- RelationshipType (canonical GedcomX relationship types) ----------------
RELATIONSHIP_TYPES: Dict[str, str] = {
    # Core
    "Couple":             GX + "Couple",
    "ParentChild":        GX + "ParentChild",
    "AncestorDescendant": GX + "AncestorDescendant",
    # Social & historical (present in GedcomX vocab and used by FS records)
    "EnslavedOf":         GX + "EnslavedOf",
    "OwnerOf":            GX + "OwnerOf",
}


FACT_TYPES: Dict[str, str] = {
    # Vital / rites
    "Birth":                  GX + "Birth",
    "Christening":            GX + "Christening",
    "AdultChristening":       GX + "AdultChristening",
    "Baptism":                GX + "Baptism",
    "BarMitzvah":             GX + "BarMitzvah",
    "BatMitzvah":             GX + "BatMitzvah",
    "Confirmation":           GX + "Confirmation",
    "FirstCommunion":         GX + "FirstCommunion",
    "Circumcision":           GX + "Circumcision",
    "Blessing":               GX + "Blessing",
    "Death":                  GX + "Death",
    "Burial":                 GX + "Burial",
    "Cremation":              GX + "Cremation",
    "Stillbirth":             GX + "Stillbirth",
    "Funeral":                GX + "Funeral",

    # Marital / couple lifecycle
    "Engagement":             GX + "Engagement",
    "Marriage":               GX + "Marriage",
    "MarriageBanns":          GX + "MarriageBanns",
    "MarriageContract":       GX + "MarriageContract",
    "MarriageLicense":        GX + "MarriageLicense",
    "MarriageNotice":         GX + "MarriageNotice",
    "MarriageSettlement":     GX + "MarriageSettlement",
    "Annulment":              GX + "Annulment",
    "Divorce":                GX + "Divorce",
    "DivorceFiling":          GX + "DivorceFiling",

    # Migration / residence / civil
    "Residence":              GX + "Residence",
    "Census":                 GX + "Census",
    "Emigration":             GX + "Emigration",
    "Immigration":            GX + "Immigration",
    "Naturalization":         GX + "Naturalization",
    "LandTransaction":        GX + "LandTransaction",
    "Probate":                GX + "Probate",
    "Will":                   GX + "Will",
    "Pardon":                 GX + "Pardon",

    # Education / work / service / religion
    "Education":              GX + "Education",
    "Occupation":             GX + "Occupation",
    "MilitaryAward":          GX + "MilitaryAward",
    "MilitaryDraftRegistration": GX + "MilitaryDraftRegistration",
    "MilitaryInduction":      GX + "MilitaryInduction",
    "MilitaryService":        GX + "MilitaryService",
    "Mission":                GX + "Mission",
    "Ordination":             GX + "Ordination",
    "Retirement":             GX + "Retirement",

    # Adoption & guardianship (commonly a relationship fact)
    "Adoption":               GX + "Adoption",
}

# --- Inverse lookups --------------------------------------------------------
_EVENT_URIS_TO_LABEL: Dict[str, str] = {v: k for k, v in EVENT_TYPES.items()}
_REL_URIS_TO_LABEL: Dict[str, str] = {v: k for k, v in RELATIONSHIP_TYPES.items()}
_FACT_URIS_TO_LABEL: Dict[str, str] = {v: k for k, v in FACT_TYPES.items()}

_ALL_KNOWN_URIS: Set[str] = set(_EVENT_URIS_TO_LABEL) | set(_REL_URIS_TO_LABEL) | set(_FACT_URIS_TO_LABEL)

# --- Helpers ----------------------------------------------------------------
def normalize_type(value: str | None) -> str | None:
    """
    Return a canonical GedcomX URI for a given type `value`, which may be:
      * the full URI (http://gedcomx.org/Birth), returned unchanged,
      * a simple label ('Birth'), mapped to the canonical URI,
      * a 'data:,' pseudo-URI containing a label (e.g., 'data:,Birth'),
      * whitespace or empty -> None.
    """
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    if v.startswith("data:,"):
        v = v[6:]
    if v in _ALL_KNOWN_URIS:
        return v
    if v.startswith(GX):
        return v  
    if v in EVENT_TYPES:
        return EVENT_TYPES[v]
    if v in RELATIONSHIP_TYPES:
        return RELATIONSHIP_TYPES[v]
    if v in FACT_TYPES:
        return FACT_TYPES[v]
    return value  # preserve unknown strings

def label_for(uri_or_label: str | None) -> str:
    """
    Return the canonical short label ('Birth', 'Couple', etc.) for any known
    GedcomX URI or label. Unknown inputs are returned as-is.
    """
    if not uri_or_label:
        return ""
    u = uri_or_label.strip()
    if not u:
        return ""
    # Strip data:, wrapper if present
    if u.startswith("data:,"):
        u = u[6:]

    if u in EVENT_TYPES or u in RELATIONSHIP_TYPES or u in FACT_TYPES:
        return u

    # Normalize GX URIs to labels when known
    if u in _EVENT_URIS_TO_LABEL:
        return _EVENT_URIS_TO_LABEL[u]
    if u in _REL_URIS_TO_LABEL:
        return _REL_URIS_TO_LABEL[u]
    if u in _FACT_URIS_TO_LABEL:
        return _FACT_URIS_TO_LABEL[u]
    # Unknown: return the original, but don't crash callers
    return u

def is_event_type(value: str | None) -> bool:
    v = normalize_type(value)
    return v in _EVENT_URIS_TO_LABEL

def is_relationship_type(value: str | None) -> bool:
    v = normalize_type(value)
    return v in _REL_URIS_TO_LABEL
=======
# Copyright © 2024 Gabriel Rios

# License: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
#
# gedcomx_v1.vocab — GedcomX vocabularies and helpers
#
#
# Sources:
# - http://gedcomx.org/EventType
# - http://gedcomx.org/RelationshipType
# - http://gedcomx.org/FactType


from __future__ import annotations

from typing import Dict, Set

GX = "http://gedcomx.org/"


EVENT_TYPES: Dict[str, str] = {
    "Adoption":               GX + "Adoption",
    "AdultChristening":       GX + "AdultChristening",
    "Annulment":              GX + "Annulment",
    "Baptism":                GX + "Baptism",
    "BarMitzvah":             GX + "BarMitzvah",
    "BatMitzvah":             GX + "BatMitzvah",
    "Birth":                  GX + "Birth",
    "Blessing":               GX + "Blessing",
    "Burial":                 GX + "Burial",
    "Census":                 GX + "Census",
    "Christening":            GX + "Christening",
    "Circumcision":           GX + "Circumcision",
    "Confirmation":           GX + "Confirmation",
    "Cremation":              GX + "Cremation",
    "Death":                  GX + "Death",
    "Divorce":                GX + "Divorce",
    "DivorceFiling":          GX + "DivorceFiling",
    "Education":              GX + "Education",
    "Emigration":             GX + "Emigration",
    "Engagement":             GX + "Engagement",
    "FirstCommunion":         GX + "FirstCommunion",
    "Funeral":                GX + "Funeral",
    "Immigration":            GX + "Immigration",
    "LandTransaction":        GX + "LandTransaction",
    "Marriage":               GX + "Marriage",
    "MarriageBanns":          GX + "MarriageBanns",
    "MarriageContract":       GX + "MarriageContract",
    "MarriageLicense":        GX + "MarriageLicense",
    "MarriageNotice":         GX + "MarriageNotice",
    "MarriageSettlement":     GX + "MarriageSettlement",
    "MilitaryAward":          GX + "MilitaryAward",
    "MilitaryDraftRegistration": GX + "MilitaryDraftRegistration",
    "MilitaryInduction":      GX + "MilitaryInduction",
    "MilitaryService":        GX + "MilitaryService",
    "Mission":                GX + "Mission",
    "Naturalization":         GX + "Naturalization",
    "Ordination":             GX + "Ordination",
    "Pardon":                 GX + "Pardon",
    "Probate":                GX + "Probate",
    "Residence":              GX + "Residence",
    "Retirement":             GX + "Retirement",
    "Stillbirth":             GX + "Stillbirth",
    "Will":                   GX + "Will",
}

# --- RelationshipType (canonical GedcomX relationship types) ----------------
RELATIONSHIP_TYPES: Dict[str, str] = {
    # Core
    "Couple":             GX + "Couple",
    "ParentChild":        GX + "ParentChild",
    "AncestorDescendant": GX + "AncestorDescendant",
    # Social & historical (present in GedcomX vocab and used by FS records)
    "EnslavedOf":         GX + "EnslavedOf",
    "OwnerOf":            GX + "OwnerOf",
}


FACT_TYPES: Dict[str, str] = {
    # Vital / rites
    "Birth":                  GX + "Birth",
    "Christening":            GX + "Christening",
    "AdultChristening":       GX + "AdultChristening",
    "Baptism":                GX + "Baptism",
    "BarMitzvah":             GX + "BarMitzvah",
    "BatMitzvah":             GX + "BatMitzvah",
    "Confirmation":           GX + "Confirmation",
    "FirstCommunion":         GX + "FirstCommunion",
    "Circumcision":           GX + "Circumcision",
    "Blessing":               GX + "Blessing",
    "Death":                  GX + "Death",
    "Burial":                 GX + "Burial",
    "Cremation":              GX + "Cremation",
    "Stillbirth":             GX + "Stillbirth",
    "Funeral":                GX + "Funeral",

    # Marital / couple lifecycle
    "Engagement":             GX + "Engagement",
    "Marriage":               GX + "Marriage",
    "MarriageBanns":          GX + "MarriageBanns",
    "MarriageContract":       GX + "MarriageContract",
    "MarriageLicense":        GX + "MarriageLicense",
    "MarriageNotice":         GX + "MarriageNotice",
    "MarriageSettlement":     GX + "MarriageSettlement",
    "Annulment":              GX + "Annulment",
    "Divorce":                GX + "Divorce",
    "DivorceFiling":          GX + "DivorceFiling",

    # Migration / residence / civil
    "Residence":              GX + "Residence",
    "Census":                 GX + "Census",
    "Emigration":             GX + "Emigration",
    "Immigration":            GX + "Immigration",
    "Naturalization":         GX + "Naturalization",
    "LandTransaction":        GX + "LandTransaction",
    "Probate":                GX + "Probate",
    "Will":                   GX + "Will",
    "Pardon":                 GX + "Pardon",

    # Education / work / service / religion
    "Education":              GX + "Education",
    "Occupation":             GX + "Occupation",
    "MilitaryAward":          GX + "MilitaryAward",
    "MilitaryDraftRegistration": GX + "MilitaryDraftRegistration",
    "MilitaryInduction":      GX + "MilitaryInduction",
    "MilitaryService":        GX + "MilitaryService",
    "Mission":                GX + "Mission",
    "Ordination":             GX + "Ordination",
    "Retirement":             GX + "Retirement",

    # Adoption & guardianship (commonly a relationship fact)
    "Adoption":               GX + "Adoption",
}

# --- Inverse lookups --------------------------------------------------------
_EVENT_URIS_TO_LABEL: Dict[str, str] = {v: k for k, v in EVENT_TYPES.items()}
_REL_URIS_TO_LABEL: Dict[str, str] = {v: k for k, v in RELATIONSHIP_TYPES.items()}
_FACT_URIS_TO_LABEL: Dict[str, str] = {v: k for k, v in FACT_TYPES.items()}

_ALL_KNOWN_URIS: Set[str] = set(_EVENT_URIS_TO_LABEL) | set(_REL_URIS_TO_LABEL) | set(_FACT_URIS_TO_LABEL)

# --- Helpers ----------------------------------------------------------------
def normalize_type(value: str | None) -> str | None:
    """
    Return a canonical GedcomX URI for a given type `value`, which may be:
      * the full URI (http://gedcomx.org/Birth), returned unchanged,
      * a simple label ('Birth'), mapped to the canonical URI,
      * a 'data:,' pseudo-URI containing a label (e.g., 'data:,Birth'),
      * whitespace or empty -> None.
    """
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    if v.startswith("data:,"):
        v = v[6:]
    if v in _ALL_KNOWN_URIS:
        return v
    if v.startswith(GX):
        return v  
    if v in EVENT_TYPES:
        return EVENT_TYPES[v]
    if v in RELATIONSHIP_TYPES:
        return RELATIONSHIP_TYPES[v]
    if v in FACT_TYPES:
        return FACT_TYPES[v]
    return value  # preserve unknown strings

def label_for(uri_or_label: str | None) -> str:
    """
    Return the canonical short label ('Birth', 'Couple', etc.) for any known
    GedcomX URI or label. Unknown inputs are returned as-is.
    """
    if not uri_or_label:
        return ""
    u = uri_or_label.strip()
    if not u:
        return ""
    # Strip data:, wrapper if present
    if u.startswith("data:,"):
        u = u[6:]

    if u in EVENT_TYPES or u in RELATIONSHIP_TYPES or u in FACT_TYPES:
        return u

    # Normalize GX URIs to labels when known
    if u in _EVENT_URIS_TO_LABEL:
        return _EVENT_URIS_TO_LABEL[u]
    if u in _REL_URIS_TO_LABEL:
        return _REL_URIS_TO_LABEL[u]
    if u in _FACT_URIS_TO_LABEL:
        return _FACT_URIS_TO_LABEL[u]
    # Unknown: return the original, but don't crash callers
    return u

def is_event_type(value: str | None) -> bool:
    v = normalize_type(value)
    return v in _EVENT_URIS_TO_LABEL

def is_relationship_type(value: str | None) -> bool:
    v = normalize_type(value)
    return v in _REL_URIS_TO_LABEL
>>>>>>> 998dda87f76a3603882c9b319d12e1cea6318da5
