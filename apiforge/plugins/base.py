"""Common base class for every plugin.

Re-exported from :mod:`apiforge.plugins` for convenience; the canonical
home is the parent package.
"""

from __future__ import annotations

# Re-export to keep ``from apiforge.plugins.base import BasePlugin`` working.
from apiforge.plugins import BasePlugin

__all__ = ["BasePlugin"]
