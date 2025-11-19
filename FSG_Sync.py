# -*- coding: utf-8 -*-
from __future__ import annotations

# ---- Vendored gedcomx_v1 (runs when FSG_Sync.py is loaded) ----
from pathlib import Path
import sys
import importlib
import os

PLUGIN_DIR = Path(__file__).resolve().parent
VENDOR_DIR = PLUGIN_DIR / "fs_vendor"

# Always prefer our vendored gedcomx_v1 over any pre-imported copy
if "gedcomx_v1" in sys.modules:
    del sys.modules["gedcomx_v1"]

# Ensure our vendor dir is first on sys.path, then import & pin
if (VENDOR_DIR / "gedcomx_v1").exists():
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))

gx = importlib.import_module("gedcomx_v1")
sys.modules["gedcomx_v1"] = gx  # pin vendored copy

# Log where it came from (force flush so it shows in gdb output)
print(f"[FS Sync] gedcomx_v1 resolved to: {Path(gx.__file__).resolve()}", flush=True)
# -------------------------------------------------------------------------


# Keep the plugin dir importable when Gramps loads plugins flat
_PLUGIN_DIR = os.path.dirname(__file__)
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

# Load the refactored class
from fs_person import FSG_Sync

__all__ = ["FSG_Sync"]
