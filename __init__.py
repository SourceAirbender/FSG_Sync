<<<<<<< HEAD
from pathlib import Path
import sys
import importlib

VENDOR_DIR = Path(__file__).resolve().parent / "fs_vendor"

# ---------------------------------------------------------------------------
# Vendored gedcomx_v1
# ---------------------------------------------------------------------------
if (VENDOR_DIR / "gedcomx_v1").exists():
    sys.path.insert(0, str(VENDOR_DIR))

gx = importlib.import_module("gedcomx_v1")
sys.modules["gedcomx_v1"] = gx

gx_path = Path(getattr(gx, "__file__", "")).resolve()
print(f"[FS Sync] gedcomx_v1 resolved to: {gx_path}")

# ---------------------------------------------------------------------------
# WebKit2 4.0 logging (system GI, not vendored)
# ---------------------------------------------------------------------------
try:
    import gi
    gi.require_version("WebKit2", "4.0")

    # GIRepository lets us ask where the typelib is loaded from
    from gi.repository import GIRepository

    repo = GIRepository.Repository.get_default()
    webkit_typelib = repo.get_typelib_path("WebKit2")  # e.g. /usr/lib/.../WebKit2-4.0.typelib

    print(f"[FS Sync] WebKit2 4.0 typelib: {webkit_typelib}")
except Exception as e:
    # Don’t blow up plugin import if WebKit2 isn’t available;
    # just log the problem.
    print(f"[FS Sync] WebKit2 4.0 not available via GI: {e}")
=======
from pathlib import Path
import sys, importlib

VENDOR_DIR = Path(__file__).resolve().parent / "fs_vendor"

# Ensure we can find the vendored package
if (VENDOR_DIR / "gedcomx_v1").exists():
    sys.path.insert(0, str(VENDOR_DIR))

# Import and pin a single instance for the whole process
gx = importlib.import_module("gedcomx_v1")
sys.modules["gedcomx_v1"] = gx

# log from where
gx_path = Path(getattr(gx, "__file__", "")).resolve()
print(f"[FS Sync] gedcomx_v1 resolved to: {gx_path}")
>>>>>>> 998dda87f76a3603882c9b319d12e1cea6318da5
