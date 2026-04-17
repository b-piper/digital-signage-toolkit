"""Digital Signage Toolkit package.

This package exposes the main application entrypoint and also provides
namespaced access to the core, utils, and gui subpackages.

To keep the codebase layout flexible while maintaining clean imports like
``digital_signage_toolkit.utils.sudo_handler``, we alias the top-level
``core``, ``utils``, and ``gui`` packages into this namespace.
"""

from __future__ import annotations

__version__ = "2.4.7"


# Source directories have been moved physically into this package.
# Dynamic aliasing is no longer required.
