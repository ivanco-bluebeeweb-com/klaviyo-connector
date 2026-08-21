"""Entrypoint for the web-kernel and CLI tools (imperal validate/build).

Sets up sys.path, purges stale module cache, then imports ext/chat and all
handler modules so their decorators register on the same Extension instance
-- same pattern as DataForSEO Connector's main.py.
"""

import os
import sys

_EXT_DIR = os.path.dirname(os.path.abspath(__file__))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

_LOCAL = (
    "app", "models", "klaviyo_client", "accounts",
    "handlers_profiles", "handlers_events", "handlers_campaigns",
    "handlers_catalog", "panels",
)
for _mod in _LOCAL:
    sys.modules.pop(_mod, None)

from app import ext, chat  # noqa: E402,F401
import accounts  # noqa: E402,F401
import handlers_profiles  # noqa: E402,F401
import handlers_events  # noqa: E402,F401
import handlers_campaigns  # noqa: E402,F401
import handlers_catalog  # noqa: E402,F401
import panels  # noqa: E402,F401
