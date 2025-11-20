from __future__ import annotations

# Gramps
from gramps.gen.config import config
from gramps.gen.plug import Gramplet

# Mixins 
from .mixins.ui import UIMixin
from .mixins.auth import AuthMixin
from .mixins.compare_gtk import CompareGtkMixin
from .mixins.compare_web import CompareWebMixin
from .mixins.import_spouse import ImportSpouseMixin
from .mixins.import_children import ImportChildrenMixin
from .mixins.import_parents import ImportParentsMixin
from .mixins.sources_dialog import SourcesDialogMixin
from .mixins.source_import import SourceImportMixin
from .mixins.cache import CacheMixin
from .mixins.helpers import HelpersMixin


class FSG_Sync(
    UIMixin,
    AuthMixin,
    CompareGtkMixin,
    CompareWebMixin,
    ImportSpouseMixin,
    ImportChildrenMixin,
    ImportParentsMixin,
    SourcesDialogMixin,
    SourceImportMixin,
    CacheMixin,
    HelpersMixin,
    Gramplet,
):
    CONFIG = config.register_manager("FSG_Sync")
    CONFIG.register("preferences.fs_username", "")
    CONFIG.register("preferences.fs_pass", "")
    CONFIG.register("preferences.fs_client_id", "")
    CONFIG.register("preferences.fs_image_download_dir", "")
    CONFIG.register("preferences.fs_web_compare_url", "")
    CONFIG.load()

    fs_Tree = None
    fs_TreeSearch = None
    FSID = None
    _cache = None
