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
