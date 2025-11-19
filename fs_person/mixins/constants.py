# -*- coding: utf-8 -*-
from __future__ import annotations

# FS OAuth
APP_KEY = 'a02j000000KTRjpAAH'
REDIRECT = 'https://misbach.github.io/fs-auth/index_raw.html'

# Tag sets
FS_DIRECT_TAGS = {
    "http://gedcomx.org/Birth",
    "http://gedcomx.org/Death",
    "http://gedcomx.org/Baptism",
    "http://gedcomx.org/Christening",
    "http://gedcomx.org/Burial",
    "http://gedcomx.org/Marriage",
    "http://gedcomx.org/Divorce",
}
FS_MENTION_ONLY = {"http://gedcomx.org/Name", "http://gedcomx.org/Gender"}

# auth helpers presence
has_minibrowser = False
try:
    import minibrowser  
    has_minibrowser = True
except Exception:
    pass
