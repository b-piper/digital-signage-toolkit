"""Pre-installation validation checks used at application startup.

These checks are designed to be:
- **Safe**: never crash the GUI
- **Informative**: provide clear, human-readable messages
- **Non-blocking**: warn rather than hard-fail in edge cases
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

import psutil

from .logger import get_logger


class PreflightChecker:
    """Performs pre-installation / pre-run validation checks.

    Results are exposed as a mapping:
        {
          "Disk Space": {"passed": bool, "severity": "info|warning|error", "message": str},
          ...
        }
    This format is easy to surface in the GUI and to assert against in tests.
    """

    def __init__(self, sudo_handler: object | None = None):
        # sudo_handler is optional and loosely typed to avoid circular imports
        self.logger = get_logger()
        self.sudo_handler = sudo_handler
        self.results: dict[str, dict[str, Any]] = {}

    # Internal helper -----------------------------------------------------
    def _record(
        self,
        name: str,
        passed: bool,
        message: str,
        severity: str = "warning",
    ) -> None:
        """Record the outcome of a single check."""
        self.results[name] = {
            "passed": passed,
            "severity": severity,
            "message": message,
        }

    # Individual checks ---------------------------------------------------
    def check_disk_space(self, required_gb: float = 5.0) -> bool:
        """Check if sufficient disk space is available on root filesystem."""
        try:
            disk = psutil.disk_usage("/")
            free_gb = disk.free / (1024**3)

            if free_gb < required_gb:
                self._record(
                    "Disk Space",
                    False,
                    f"{free_gb:.1f}GB free, {required_gb}GB required for safe operation",
                    "error",
                )
                return False
            elif free_gb < required_gb * 2:
                self._record(
                    "Disk Space",
                    True,
                    f"{free_gb:.1f}GB free (consider at least {required_gb * 2:.1f}GB)",
                    "warning",
                )
            else:
                self._record(
                    "Disk Space",
                    True,
                    f"{free_gb:.1f}GB free",
                    "info",
                )
            return True
        except Exception as e:
            # Don't block on check failure, just log a warning
            self.logger.log_error(e, "DISK_SPACE_CHECK")
            self._record(
                "Disk Space",
                True,
                "Could not check disk space (see logs for details)",
                "warning",
            )
            return True

    def check_internet(self) -> bool:
        """Check internet connectivity to Ubuntu archive."""
        try:
            result = subprocess.run(
                ["wget", "-q", "--spider", "--timeout=5", "http://archive.ubuntu.com/ubuntu"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                self._record(
                    "Internet Connectivity",
                    False,
                    "No internet connection detected (online installs and updates may fail)",
                    "warning",
                )
                return False

            self._record(
                "Internet Connectivity",
                True,
                "Successfully reached Ubuntu archive",
                "info",
            )
            return True
        except Exception:
            self._record(
                "Internet Connectivity",
                False,
                "Could not verify internet connection",
                "warning",
            )
            return False

    def check_python_version(self, min_version: tuple[int, int] = (3, 8)) -> bool:
        """Check that the running Python version meets minimum requirement."""
        try:
            import sys

            version = sys.version_info[:2]
            if version < min_version:
                self._record(
                    "Python Version",
                    False,
                    f"Python {min_version[0]}.{min_version[1]}+ required, "
                    f"found {version[0]}.{version[1]}",
                    "error",
                )
                return False

            self._record(
                "Python Version",
                True,
                f"Python {version[0]}.{version[1]} OK",
                "info",
            )
            return True
        except Exception:
            self._record(
                "Python Version",
                False,
                "Could not determine Python version",
                "error",
            )
            return False

    def check_required_commands(self, commands: list[str]) -> bool:
        """Check if required system commands are available in PATH."""
        missing = []
        for cmd in commands:
            if shutil.which(cmd) is None:
                missing.append(cmd)

        if missing:
            self._record(
                "Required Commands",
                False,
                f"Missing commands (will be installed if possible): {', '.join(missing)}",
                "warning",
            )
            return False

        self._record(
            "Required Commands",
            True,
            "All required base commands present",
            "info",
        )
        return True

    def check_sudo_access(self) -> bool:
        """Check if sudo access is available without blocking.

        We don't require password here; we just warn if password will be needed.
        """
        try:
            # Prefer injected sudo_handler when available
            has_sudo = False
            if self.sudo_handler is not None and hasattr(self.sudo_handler, "check_sudo"):
                try:
                    has_sudo = bool(self.sudo_handler.check_sudo())
                except Exception:
                    has_sudo = False
            else:
                result = subprocess.run(
                    ["sudo", "-n", "true"],
                    capture_output=True,
                    timeout=5,
                )
                has_sudo = result.returncode == 0

            if has_sudo:
                self._record(
                    "Sudo Access",
                    True,
                    "Sudo access available",
                    "info",
                )
            else:
                self._record(
                    "Sudo Access",
                    True,
                    "Sudo password will be requested when needed",
                    "warning",
                )
            return True
        except Exception:
            self._record(
                "Sudo Access",
                True,
                "Could not check sudo access (will prompt when needed)",
                "warning",
            )
            return True

    def check_system_resources(self) -> bool:
        """Check basic system resources (memory, CPU load)."""
        try:
            mem = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)

            passed = True
            messages = []
            severity = "info"

            if mem.total < 2 * (1024**3):  # Less than 2GB RAM
                passed = True  # Still allow, but warn
                severity = "warning"
                messages.append(f"Low system memory: {mem.total / (1024**3):.1f}GB")

            if cpu_percent > 90:
                passed = True
                severity = "warning"
                messages.append(f"High current CPU usage: {cpu_percent:.1f}%")

            if not messages:
                messages.append("Resources look OK")

            self._record(
                "System Resources",
                passed,
                "; ".join(messages),
                severity,
            )
            return True
        except Exception as e:
            self.logger.log_error(e, "RESOURCE_CHECK")
            self._record(
                "System Resources",
                True,
                "Could not check system resources",
                "warning",
            )
            return True

    # Orchestration -------------------------------------------------------
    def run_all_checks(self) -> dict[str, dict[str, Any]]:
        """Run all preflight checks and return structured results.

        Returns:
            Dict mapping check name -> result dict, e.g.:
            {
              "Disk Space": {"passed": True, "severity": "info", "message": "..."},
              ...
            }
        """
        self.results.clear()

        # Critical checks
        self.check_disk_space()
        self.check_python_version()

        # Non-critical checks
        self.check_internet()
        self.check_required_commands(["wget", "curl", "apt-get"])
        self.check_sudo_access()
        self.check_system_resources()

        return self.results
