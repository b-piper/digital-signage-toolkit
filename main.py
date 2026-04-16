#!/usr/bin/env python3
"""Wrapper entry point for Digital Signage Toolkit."""
import sys
from pathlib import Path

# Add the project root to sys.path to ensure digital_signage_toolkit is importable
# when running from the root directory.
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from digital_signage_toolkit.main import main
except ImportError as e:
    print(f"Error: Could not import digital_signage_toolkit. {e}")
    sys.exit(1)

if __name__ == '__main__':
    main()
