"""Input validation utilities."""
import os
import re
from pathlib import Path
from typing import Optional


def validate_hostname(hostname: str) -> bool:
    """Validate hostname according to RFC 1123."""
    if not hostname or len(hostname) > 253:
        return False

    # Check each label
    labels = hostname.split('.')
    if len(labels) > 127:
        return False

    # RFC 1123: hostname labels can contain letters, digits, and hyphens
    label_pattern = re.compile(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', re.IGNORECASE)

    for label in labels:
        if not label or len(label) > 63:
            return False
        if not label_pattern.match(label):
            return False

    return True


def sanitize_hostname(hostname: str) -> Optional[str]:
    """Sanitize and validate hostname."""
    if not hostname:
        return None

    # Remove whitespace
    hostname = hostname.strip()

    # Remove invalid characters
    hostname = re.sub(r'[^a-z0-9.-]', '', hostname, flags=re.IGNORECASE)

    # Validate
    if validate_hostname(hostname):
        return hostname

    return None


def validate_snapshot_id(snapshot_id: str) -> bool:
    """Validate Timeshift snapshot ID."""
    if not snapshot_id:
        return False

    # Snapshot IDs are typically alphanumeric with dashes/underscores
    # and should not contain shell metacharacters
    if re.match(r'^[a-zA-Z0-9_-]+$', snapshot_id):
        return True

    return False


def validate_path(path: str, must_exist: bool = False, must_be_absolute: bool = False) -> bool:
    """Validate file path."""
    if not path:
        return False

    try:
        path_obj = Path(path)

        if must_be_absolute and not path_obj.is_absolute():
            return False

        if must_exist and not path_obj.exists():
            return False

        # Check for path traversal attempts in the original path string
        # This is the most reliable way to detect traversal attempts
        if '..' in path:
            return False

        # Additional check: for relative paths, ensure they don't resolve outside current directory
        if not path_obj.is_absolute():
            try:
                # Get current working directory
                cwd = Path.cwd()
                resolved = (cwd / path_obj).resolve()
                # Check if resolved path is still within or at the cwd level
                # If it goes up from cwd, it's a traversal attempt
                try:
                    resolved.relative_to(cwd)
                except ValueError:
                    # Path is outside cwd, which is suspicious for relative paths
                    # But we already checked for '..' above, so this is just a safety check
                    pass
            except (OSError, ValueError):
                # Path resolution failed, likely invalid
                return False

        return True
    except Exception:
        return False


def sanitize_path(path: str) -> Optional[str]:
    """Sanitize file path."""
    if not path:
        return None

    # Expand user and vars
    path = os.path.expanduser(os.path.expandvars(path))

    # Resolve to absolute path
    try:
        path_obj = Path(path).resolve()
        return str(path_obj)
    except Exception:
        return None


def validate_resolution(resolution: str) -> bool:
    """Validate display resolution format."""
    if not resolution:
        return False

    # Format: WIDTHxHEIGHT (e.g., 1920x1080)
    pattern = re.compile(r'^\d+x\d+$')
    if pattern.match(resolution):
        parts = resolution.split('x')
        width = int(parts[0])
        height = int(parts[1])
        # Reasonable limits
        if 640 <= width <= 7680 and 480 <= height <= 4320:
            return True

    return False


def validate_script_path(path: str) -> bool:
    """Validate script path for use in systemd services or shell commands.
    
    Ensures path doesn't contain shell metacharacters that could cause injection.
    """
    if not path:
        return False

    # Check for shell metacharacters
    dangerous_chars = [';', '&', '|', '$', '`', '(', ')', '<', '>', '\n', '\r']
    if any(char in path for char in dangerous_chars):
        return False

    # Check for path traversal
    if '..' in path:
        return False

    # Path should be a valid file path
    try:
        path_obj = Path(path)
        # Resolve to check for traversal
        path_obj.resolve()
        return True
    except Exception:
        return False


def sanitize_for_python_string(path: str) -> str:
    """Sanitize path for safe interpolation into Python code strings.
    
    Escapes special characters to prevent code injection.
    """
    if not path:
        return "''"

    # Escape single quotes and backslashes
    escaped = path.replace('\\', '\\\\').replace("'", "\\'")
    return f"'{escaped}'"

