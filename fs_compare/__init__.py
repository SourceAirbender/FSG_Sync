from __future__ import annotations

from .options import CompareOptions
from .window import FSCompareWindow
from .formatters import person_dates_str, fs_person_dates_str
from .comparators import (
    compare_gender,
    compare_fact,
    compare_names,
    compare_parents,
    compare_spouse_notes,
    compare_spouses,
    compare_other_facts,
)
from .aggregate import compare_fs_to_gramps

__all__ = [
    "CompareOptions",
    "FSCompareWindow",
    "person_dates_str",
    "fs_person_dates_str",
    "compare_gender",
    "compare_fact",
    "compare_names",
    "compare_parents",
    "compare_spouse_notes",
    "compare_spouses",
    "compare_other_facts",
    "compare_fs_to_gramps",
]
