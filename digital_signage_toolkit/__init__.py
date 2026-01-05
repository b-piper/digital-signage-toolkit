"""Digital Signage Toolkit package.

This package exposes the main application entrypoint and also provides
namespaced access to the core, utils, and gui subpackages.

To keep the codebase layout flexible while maintaining clean imports like
``digital_signage_toolkit.utils.sudo_handler``, we alias the top-level
``core``, ``utils``, and ``gui`` packages into this namespace.
"""

from __future__ import annotations

import importlib
import sys
from typing import Iterable

__version__ = "2.0.0"


def _alias_subpackages(package_names: Iterable[str]) -> None:
    """Alias top-level packages under the digital_signage_toolkit namespace.

    This allows imports such as:
        digital_signage_toolkit.utils.sudo_handler
        digital_signage_toolkit.core.system_ops
        digital_signage_toolkit.gui.main_window

    while the actual implementation packages live at the top level
    (``utils``, ``core``, ``gui``). This keeps packaging simple and avoids
    breaking existing imports.
    """
    base_name = __name__

    for name in package_names:
        full_name = f"{base_name}.{name}"
        if full_name in sys.modules:
            # Already aliased
            continue
        try:
            module = importlib.import_module(name)
        except ImportError:
            # If a given helper package isn't present, skip it gracefully.
            continue

        # Alias the module under the digital_signage_toolkit.* namespace
        sys.modules[full_name] = module


# Alias common subpackages on import
_alias_subpackages(["core", "utils", "gui"])

