"""System operations module."""
import os
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from digital_signage_toolkit.utils.error_handling import (
    log_operation_errors,
    log_operation_errors_with_message,
)
from digital_signage_toolkit.utils.logger import get_logger
from digital_signage_toolkit.utils.sudo_handler import SudoHandler


class SystemOperations:
    """Handles system-level operations."""

    def __init__(self, sudo_handler: SudoHandler):
        self.sudo = sudo_handler
        self.logger = get_logger()

    @log_operation_errors("CHECK_INTERNET")
    def check_internet(self, target: str = 'http://archive.ubuntu.com/ubuntu') -> bool:
        """Check internet connectivity."""
        result = subprocess.run(
            ['wget', '-q', '--spider', '--timeout=5',
             target],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0

    @log_operation_errors("CHECK_DISK_SPACE")
    def check_disk_space(self, path: str = "/", min_gb: float = 5.0) -> bool:
        """Check if sufficient disk space is available."""
        total, used, free = shutil.disk_usage(path)
        free_gb = free / (1024**3)
        if free_gb < min_gb:
            self.logger.log_error(
                RuntimeError(f"Insufficient disk space: {free_gb:.2f}GB free, {min_gb}GB required"),
                "CHECK_DISK_SPACE"
            )
            return False
        return True

    @log_operation_errors("UPDATE_HOSTS_FILE")
    def update_hosts_file(self, new_hostname: str) -> bool:
        """Update /etc/hosts to resolve new hostname to 127.0.1.1."""
        try:
             # Read current hosts file
            with open('/etc/hosts') as f:
                lines = f.readlines()

            new_lines = []
            found = False
            for line in lines:
                if line.strip().startswith('127.0.1.1'):
                    new_lines.append(f"127.0.1.1\t{new_hostname}\n")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f"127.0.1.1\t{new_hostname}\n")

            # Write temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
                tf.writelines(new_lines)
                temp_path = tf.name

            # Move into place using sudo
            result = self.sudo.run_command(
                ['cp', temp_path, '/etc/hosts'],
                timeout=5
            )
            os.unlink(temp_path)

            return result.returncode == 0
        except Exception as e:
            self.logger.log_error(e, "UPDATE_HOSTS_FILE")
            return False

    def get_hostname(self) -> str:
        """Get current hostname."""
        return socket.gethostname()

    @log_operation_errors("SET_HOSTNAME")
    def set_hostname(self, new_hostname: str) -> bool:
        """Set system hostname."""
        # Validate hostname before setting
        from digital_signage_toolkit.utils.validators import sanitize_hostname

        sanitized = sanitize_hostname(new_hostname)
        if not sanitized:
            self.logger.log_error(
                ValueError(f"Invalid hostname: {new_hostname}"),
                "SET_HOSTNAME"
            )
            return False

        result = self.sudo.run_command(
            ['hostnamectl', 'set-hostname', sanitized],
            timeout=10
        )
        if result.returncode != 0:
            self.logger.log_error(
                RuntimeError(f"Failed to set hostname: {result.stderr}"),
                "SET_HOSTNAME"
            )
            return False

        # Also update /etc/hosts
        self.update_hosts_file(sanitized)
        return True

    @log_operation_errors_with_message("APT_UPDATE", (False, "Update failed"))
    def apt_update(self) -> Tuple[bool, str]:
        """Run apt-get update."""
        try:
            result = self.sudo.run_command(
                ['apt-get', 'update', '-y'],
                timeout=300
            )
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self.logger.log_error(
                    RuntimeError(f"apt-get update failed: {error_msg}"),
                    "APT_UPDATE"
                )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            self.logger.log_error(
                TimeoutError("apt-get update timed out after 300 seconds"),
                "APT_UPDATE"
            )
            return False, "Update timed out"
        except Exception as e:
            self.logger.log_error(e, "APT_UPDATE")
            return False, str(e)

    @log_operation_errors_with_message("APT_UPGRADE", (False, "Upgrade failed"))
    def apt_upgrade(self) -> Tuple[bool, str]:
        """Run apt-get upgrade."""
        try:
            result = self.sudo.run_command(
                ['apt-get', 'upgrade', '-y'],
                timeout=1800  # 30 minutes
            )
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self.logger.log_error(
                    RuntimeError(f"apt-get upgrade failed: {error_msg}"),
                    "APT_UPGRADE"
                )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            self.logger.log_error(
                TimeoutError("apt-get upgrade timed out after 1800 seconds"),
                "APT_UPGRADE"
            )
            return False, "Upgrade timed out"
        except Exception as e:
            self.logger.log_error(e, "APT_UPGRADE")
            return False, str(e)

    @log_operation_errors_with_message("APT_DIST_UPGRADE", (False, "Dist-upgrade failed"))
    def apt_dist_upgrade(self) -> Tuple[bool, str]:
        """Run apt-get dist-upgrade."""
        try:
            result = self.sudo.run_command(
                ['apt-get', 'dist-upgrade', '-y'],
                timeout=1800
            )
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self.logger.log_error(
                    RuntimeError(f"apt-get dist-upgrade failed: {error_msg}"),
                    "APT_DIST_UPGRADE"
                )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            self.logger.log_error(
                TimeoutError("apt-get dist-upgrade timed out after 1800 seconds"),
                "APT_DIST_UPGRADE"
            )
            return False, "Dist-upgrade timed out"
        except Exception as e:
            self.logger.log_error(e, "APT_DIST_UPGRADE")
            return False, str(e)

    @log_operation_errors_with_message("APT_AUTOREMOVE", (False, "Autoremove failed"))
    def apt_autoremove(self) -> Tuple[bool, str]:
        """Run apt-get autoremove."""
        result = self.sudo.run_command(
            ['apt-get', 'autoremove', '-y', '--purge'],
            timeout=300
        )
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            self.logger.log_error(
                RuntimeError(f"apt-get autoremove failed: {error_msg}"),
                "APT_AUTOREMOVE"
            )
        return result.returncode == 0, result.stdout + result.stderr

    @log_operation_errors_with_message("INSTALL_PACKAGES", (False, "Package installation failed"))
    def install_packages(self, packages: list[str]) -> Tuple[bool, str]:
        """Install packages via apt."""
        result = self.sudo.run_command(
            ['apt-get', 'install', '-y'] + packages,
            timeout=600
        )
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            self.logger.log_error(
                RuntimeError(f"Package installation failed: {error_msg}"),
                "INSTALL_PACKAGES"
            )
        return result.returncode == 0, result.stdout + result.stderr

    @log_operation_errors_with_message("REMOVE_PACKAGES", (False, "Package removal failed"))
    def remove_packages(self, packages: list[str]) -> Tuple[bool, str]:
        """Remove packages via apt."""
        result = self.sudo.run_command(
            ['apt-get', 'remove', '-y'] + packages,
            timeout=300
        )
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            self.logger.log_error(
                RuntimeError(f"Package removal failed: {error_msg}"),
                "REMOVE_PACKAGES"
            )
        return result.returncode == 0, result.stdout + result.stderr

    @log_operation_errors("CONFIGURE_APT_AUTO_UPGRADES")
    def configure_apt_auto_upgrades(self) -> bool:
        """Configure automatic apt upgrades."""
        config_content = """APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
"""
        # Write config file using Python to avoid shell escaping issues
        import tempfile
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as f:
                f.write(config_content)
                temp_path = f.name

            result = self.sudo.run_command(
                ['cp', temp_path, '/etc/apt/apt.conf.d/20auto-upgrades'],
                timeout=10
            )
            if result.returncode != 0:
                self.logger.log_error(
                    RuntimeError(f"Failed to copy apt config: {result.stderr}"),
                    "CONFIGURE_APT_AUTO_UPGRADES"
                )
            return result.returncode == 0
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    self.logger.log_error(e, "CLEANUP_TEMP_FILE")

    @log_operation_errors("DISABLE_WAYLAND")
    def disable_wayland(self) -> bool:
        """Disable Wayland in GDM (GDM3 only, Ubuntu 18.04+)."""
        # Check if GDM3 exists (Ubuntu 18.04+)
        gdm3_conf = Path('/etc/gdm3/custom.conf')
        gdm_conf = Path('/etc/gdm/custom.conf')  # Older GDM

        # Try GDM3 first (Ubuntu 18.04+)
        if gdm3_conf.exists():
            # Backup custom.conf if it exists
            backup_result = self.sudo.run_command(
                ['cp', '/etc/gdm3/custom.conf', '/etc/gdm3/custom.conf.backup'],
                timeout=10
            )
            if backup_result.returncode != 0:
                self.logger.log_error(
                    RuntimeError(f"Failed to backup GDM config: {backup_result.stderr}"),
                    "DISABLE_WAYLAND"
                )

            # Modify custom.conf
            result = self.sudo.run_command(
                ['sed', '-i', 's/^#WaylandEnable=false/WaylandEnable=false/', '/etc/gdm3/custom.conf'],
                timeout=10
            )
            if result.returncode == 0:
                result = self.sudo.run_command(
                    ['sed', '-i', 's/^WaylandEnable=true/WaylandEnable=false/', '/etc/gdm3/custom.conf'],
                    timeout=10
                )
            if result.returncode != 0:
                self.logger.log_error(
                    RuntimeError(f"Failed to disable Wayland: {result.stderr}"),
                    "DISABLE_WAYLAND"
                )
            return result.returncode == 0
        # Try older GDM (Ubuntu 17.10 and earlier)
        elif gdm_conf.exists():
            # Older GDM doesn't have WaylandEnable option
            # Just return True (no-op for older systems)
            return True
        else:
            # No GDM found (server edition or different DM)
            self.logger.log_error(
                FileNotFoundError("GDM configuration not found"),
                "DISABLE_WAYLAND"
            )
            return False

    @log_operation_errors("CONFIGURE_TIMEDATECTL")
    def configure_timedatectl(self) -> bool:
        """Enable NTP synchronization."""
        result = self.sudo.run_command(['timedatectl', 'set-ntp', 'true'], timeout=10)
        if result.returncode != 0:
            self.logger.log_error(
                RuntimeError(f"Failed to configure NTP: {result.stderr}"),
                "CONFIGURE_TIMEDATECTL"
            )
        return result.returncode == 0

    @log_operation_errors("CONFIGURE_DISPLAY_POWER")
    def configure_display_power(self) -> bool:
        """Disable screen saver and power management."""
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        result = subprocess.run(
            ['xset', 's', 'off', '-dpms'],
            env=env,
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            self.logger.log_error(
                RuntimeError(f"Failed to configure display power: {error_msg}"),
                "CONFIGURE_DISPLAY_POWER"
            )
        return result.returncode == 0

    @log_operation_errors("GET_DISPLAY_RESOLUTION", None)
    def get_display_resolution(self) -> Optional[str]:
        """Get current display resolution. Supports both X11 and Wayland."""
        # Detect display server
        display_server = os.environ.get('XDG_SESSION_TYPE', '').lower()

        if display_server == 'wayland':
            # Try to get resolution via wayland-query or wlr-randr
            try:
                result = subprocess.run(
                    ['wlr-randr'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Parse wlr-randr output
                    for line in result.stdout.split('\n'):
                        if 'current' in line.lower() and 'x' in line:
                            parts = line.split()
                            for part in parts:
                                if 'x' in part and part[0].isdigit():
                                    return part
            except FileNotFoundError:
                # Fallback: try gsettings
                try:
                    result = subprocess.run(
                        ['gsettings', 'get', 'org.gnome.desktop.interface', 'scaling-factor'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    # Wayland resolution detection is complex, return None for now
                    pass
                except Exception:
                    pass
            return None
        else:
            # X11 - use xrandr
            env = os.environ.copy()
            env['DISPLAY'] = ':0'
            result = subprocess.run(
                ['xrandr'],
                env=env,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse xrandr output to find current resolution
                # Look for the line with '*' which indicates the current active resolution
                for line in result.stdout.split('\n'):
                    if '*' in line and 'connected' not in line:
                        parts = line.split()
                        for part in parts:
                            if 'x' in part and part[0].isdigit():
                                return part
            elif result.returncode != 0:
                error_msg = result.stderr or "X11 not available"
                self.logger.log_error(
                    RuntimeError(f"xrandr failed: {error_msg}"),
                    "GET_DISPLAY_RESOLUTION"
                )
        return None

    @log_operation_errors("GET_AVAILABLE_RESOLUTIONS", ["1920x1080", "1280x720", "1366x768", "1600x900", "2560x1440", "3840x2160"])
    def get_available_resolutions(self) -> list[str]:
        """Get list of available display resolutions for the primary display."""
        display_server = os.environ.get('XDG_SESSION_TYPE', '').lower()

        if display_server == 'wayland':
            # Wayland resolution detection using wlr-randr
            try:
                result = subprocess.run(
                    ['wlr-randr'], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    import re
                    resolutions = set()
                    resolution_pattern = re.compile(r'\b(\d+x\d+)\b')
                    for line in result.stdout.split('\n'):
                        if line.strip().startswith((' ', '\t')):
                            matches = resolution_pattern.findall(line)
                            for match in matches:
                                from digital_signage_toolkit.utils.validators import validate_resolution
                                if validate_resolution(match):
                                    resolutions.add(match)
                    if resolutions:
                        return sorted(list(resolutions), key=lambda x: int(x.split('x')[0]) * int(x.split('x')[1]), reverse=True)
            except FileNotFoundError:
                pass
            return ["1920x1080", "1280x720", "1366x768", "1600x900", "2560x1440", "3840x2160"]
        else:
            # X11 - use xrandr with regex for single-pass parsing (performance improvement)
            env = os.environ.copy()
            env['DISPLAY'] = ':0'
            result = subprocess.run(
                ['xrandr'],
                env=env,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                import re
                resolutions = set()  # Use set to avoid duplicates
                current_output = None

                # Use regex for more efficient parsing
                resolution_pattern = re.compile(r'\b(\d+x\d+)\b')

                for line in result.stdout.split('\n'):
                    # Find connected output
                    if 'connected' in line and 'disconnected' not in line:
                        parts = line.split()
                        if parts:
                            current_output = parts[0]
                        continue

                    # Parse mode lines - look for resolution patterns
                    if current_output and line.strip().startswith((' ', '\t')):
                        # Extract all resolution patterns from line
                        matches = resolution_pattern.findall(line)
                        for match in matches:
                            # Validate resolution
                            from digital_signage_toolkit.utils.validators import validate_resolution
                            if validate_resolution(match):
                                resolutions.add(match)
                    elif line.strip() and not line.strip().startswith((' ', '\t')):
                        # New output section, reset
                        current_output = None

                # Sort resolutions by width*height (largest first)
                if resolutions:
                    sorted_resolutions = sorted(
                        list(resolutions),
                        key=lambda x: int(x.split('x')[0]) * int(x.split('x')[1]),
                        reverse=True
                    )
                    return sorted_resolutions

                # Fallback to common resolutions if parsing failed
                return ["1920x1080", "1280x720", "1366x768", "1600x900", "2560x1440", "3840x2160"]
            elif result.returncode != 0:
                error_msg = result.stderr or "X11 not available"
                self.logger.log_error(
                    RuntimeError(f"xrandr failed: {error_msg}"),
                    "GET_AVAILABLE_RESOLUTIONS"
                )

        # Fallback to common resolutions
        return ["1920x1080", "1280x720", "1366x768", "1600x900", "2560x1440", "3840x2160"]

    @log_operation_errors("SET_DISPLAY_RESOLUTION")
    def set_display_resolution(self, resolution: Optional[str] = None, output_name: Optional[str] = None) -> bool:
        """Set display resolution. If resolution is None, uses native/current resolution. Supports X11 with multi-monitor."""
        # Detect display server
        display_server = os.environ.get('XDG_SESSION_TYPE', '').lower()

        if display_server == 'wayland':
            try:
                # Find connected outputs
                result = subprocess.run(['wlr-randr'], capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    self.logger.log_error(RuntimeError("wlr-randr failed"), "SET_DISPLAY_RESOLUTION")
                    return False

                connected_outputs = []
                for line in result.stdout.split('\n'):
                    if line and not line.startswith((' ', '\t')):
                        parts = line.split()
                        if parts:
                            connected_outputs.append(parts[0])

                if not connected_outputs:
                    return False

                target_output = output_name if output_name and output_name in connected_outputs else connected_outputs[0]

                if resolution is None:
                    current_res = self.get_display_resolution()
                    if current_res:
                        return True
                    return False

                from digital_signage_toolkit.utils.validators import validate_resolution
                if not validate_resolution(resolution):
                    return False

                result = subprocess.run(
                    ['wlr-randr', '--output', target_output, '--mode', resolution],
                    capture_output=True, timeout=5
                )
                return result.returncode == 0
            except FileNotFoundError:
                self.logger.log_error(RuntimeError("wlr-randr not found"), "SET_DISPLAY_RESOLUTION")
                return False
        else:
            # X11 - use xrandr
            env = os.environ.copy()
            env['DISPLAY'] = ':0'

            # Get available modes and outputs
            result = subprocess.run(
                ['xrandr'],
                env=env,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                error_msg = result.stderr or "X11 not available"
                self.logger.log_error(
                    RuntimeError(f"xrandr failed: {error_msg}"),
                    "SET_DISPLAY_RESOLUTION"
                )
                return False

            # Find connected outputs
            connected_outputs = []
            for line in result.stdout.split('\n'):
                if 'connected' in line and 'disconnected' not in line:
                    parts = line.split()
                    if parts:
                        connected_outputs.append(parts[0])

            if not connected_outputs:
                self.logger.log_error(
                    RuntimeError("No connected displays found"),
                    "SET_DISPLAY_RESOLUTION"
                )
                return False

            # Use specified output or first connected output
            target_output = output_name if output_name and output_name in connected_outputs else connected_outputs[0]

            # If no resolution specified, detect and use current/native resolution
            if resolution is None:
                current_res = self.get_display_resolution()
                if current_res:
                    # Resolution is already set correctly, no need to change
                    return True
                else:
                    # Couldn't detect, don't force anything
                    self.logger.log_error(
                        RuntimeError("Could not detect current resolution"),
                        "SET_DISPLAY_RESOLUTION"
                    )
                    return False

            # Validate resolution format if provided
            from digital_signage_toolkit.utils.validators import validate_resolution
            if not validate_resolution(resolution):
                self.logger.log_error(
                    ValueError(f"Invalid resolution format: {resolution}"),
                    "SET_DISPLAY_RESOLUTION"
                )
                return False

            # Set resolution (safe - resolution already validated)
            result = subprocess.run(
                ['xrandr', '--output', target_output, '--mode', resolution],
                env=env,
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self.logger.log_error(
                    RuntimeError(f"Failed to set resolution: {error_msg}"),
                    "SET_DISPLAY_RESOLUTION"
                )
            return result.returncode == 0

    @log_operation_errors("GET_PREFERRED_RESOLUTION", None)
    def get_preferred_resolution(self) -> Optional[str]:
        """Get preferred/native resolution for the primary display (X11 only).

        On X11, this inspects xrandr output and returns the mode marked with '+'
        (preferred) for the first connected output. On Wayland or failure, returns None.
        """
        display_server = os.environ.get('XDG_SESSION_TYPE', '').lower()
        if display_server == 'wayland':
            # On Wayland we rely on the compositor to choose the native mode.
            return None

        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        result = subprocess.run(
            ['xrandr'],
            env=env,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            error_msg = result.stderr or "X11 not available"
            self.logger.log_error(
                RuntimeError(f"xrandr failed: {error_msg}"),
                "GET_PREFERRED_RESOLUTION"
            )
            return None

        from digital_signage_toolkit.utils.validators import validate_resolution

        current_output = None
        preferred: Optional[str] = None

        for line in result.stdout.split('\n'):
            if 'connected' in line and 'disconnected' not in line:
                parts = line.split()
                if parts:
                    current_output = parts[0]
                continue

            if current_output and line.strip().startswith((' ', '\t')):
                parts = line.split()
                if not parts:
                    continue
                mode = parts[0]
                if not validate_resolution(mode):
                    continue
                # '+' in the mode line indicates the preferred/native mode.
                if '+' in line:
                    preferred = mode
                    break
            elif line.strip() and not line.strip().startswith((' ', '\t')):
                # New output section
                current_output = None

        return preferred

    @log_operation_errors("ENSURE_NATIVE_RESOLUTION", True)
    def ensure_native_resolution(self) -> bool:
        """Ensure the primary display is using its preferred/native resolution.

        - On X11: if the current resolution differs from the preferred mode, we
          attempt to switch to the preferred mode.
        - On Wayland: we do nothing and return True (compositor-controlled).
        """
        display_server = os.environ.get('XDG_SESSION_TYPE', '').lower()
        if display_server == 'wayland':
            return True

        preferred = self.get_preferred_resolution()
        current = self.get_display_resolution()

        # If we can't determine either value, don't treat this as fatal.
        if not preferred or not current:
            return True

        if preferred == current:
            return True

        return self.set_display_resolution(preferred)

    def reboot(self, clear_cache: bool = True) -> bool:
        """Reboot the system. Optionally clear cache before reboot."""
        try:
            # Clear cache before reboot if requested
            if clear_cache:
                from digital_signage_toolkit.core.software_installer import SoftwareInstaller
                from digital_signage_toolkit.utils.config import Config

                try:
                    installer = SoftwareInstaller(self.sudo, Config())
                    installer.clear_rise_cache(aggressive=True, log_callback=None)
                except Exception:
                    # Cache clearing failed, but continue with reboot
                    pass

            # Reboot system
            self.sudo.run_command(['reboot'], timeout=5)
            return True
        except Exception:
            return False

    @log_operation_errors("BACKUP_SOURCES_LIST", None)
    def backup_sources_list(self, timestamp: Optional[str] = None) -> Optional[str]:
        """Backup /etc/apt/sources.list."""
        if timestamp is None:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')

        backup_path = f"/etc/apt/sources.list.backup.{timestamp}"
        result = self.sudo.run_command(
            ['cp', '/etc/apt/sources.list', backup_path],
            timeout=10
        )
        if result.returncode == 0:
            return backup_path
        else:
            self.logger.log_error(
                RuntimeError(f"Failed to backup sources.list: {result.stderr}"),
                "BACKUP_SOURCES_LIST"
            )
        return None

    @log_operation_errors("RESTORE_SOURCES_LIST")
    def restore_sources_list(self, backup_path: str) -> bool:
        """Restore /etc/apt/sources.list from backup."""
        # Validate backup path
        from digital_signage_toolkit.utils.validators import validate_path
        if not validate_path(backup_path, must_exist=True):
            self.logger.log_error(
                ValueError(f"Invalid backup path: {backup_path}"),
                "RESTORE_SOURCES_LIST"
            )
            return False

        result = self.sudo.run_command(
            ['cp', backup_path, '/etc/apt/sources.list'],
            timeout=10
        )
        if result.returncode != 0:
            self.logger.log_error(
                RuntimeError(f"Failed to restore sources.list: {result.stderr}"),
                "RESTORE_SOURCES_LIST"
            )
        return result.returncode == 0

    @log_operation_errors("GET_SOURCES_BACKUPS", [])
    def get_sources_backups(self) -> list[str]:
        """Get list of sources.list backup files."""
        result = self.sudo.run_command(
            ['ls', '/etc/apt/sources.list.backup.*'],
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        return []

    @log_operation_errors("FIX_APT_LOCKS")
    def fix_apt_locks(self) -> bool:
        """Remove apt locks and fix dpkg."""
        # Kill apt processes (ignore errors if processes don't exist)
        self.sudo.run_command(['killall', 'apt', 'apt-get', 'dpkg'], timeout=5)
        # killall returns non-zero if no processes found, which is OK

        # Remove locks
        rm_result = self.sudo.run_command(['rm', '-f', '/var/lib/apt/lists/lock'], timeout=5)
        if rm_result.returncode != 0:
            self.logger.log_error(
                RuntimeError(f"Failed to remove apt lock: {rm_result.stderr}"),
                "FIX_APT_LOCKS"
            )

        # Configure dpkg
        result = self.sudo.run_command(['dpkg', '--configure', '-a'], timeout=300)
        if result.returncode != 0:
            self.logger.log_error(
                RuntimeError(f"Failed to configure dpkg: {result.stderr}"),
                "FIX_APT_LOCKS"
            )
        return result.returncode == 0

    @log_operation_errors("FORCE_MAIN_MIRROR")
    def force_main_mirror(self) -> bool:
        """Force apt to use main Ubuntu mirror."""
        result = self.sudo.run_command(
            ['sed', '-i', 's|https\\?://[^/ ]*/ubuntu|http://archive.ubuntu.com/ubuntu|g',
             '/etc/apt/sources.list'],
            timeout=10
        )
        if result.returncode != 0:
            self.logger.log_error(
                RuntimeError(f"Failed to update sources.list: {result.stderr}"),
                "FORCE_MAIN_MIRROR"
            )
        return result.returncode == 0

    @log_operation_errors("RESTART_NETWORKING")
    def restart_networking(self) -> bool:
        """Restart networking services."""
        # Try Netplan first (Ubuntu 18.04+)
        result = self.sudo.run_command(['netplan', 'apply'], timeout=30)
        if result.returncode == 0:
            return True

        # Fallback to NetworkManager
        result = self.sudo.run_command(['systemctl', 'restart', 'NetworkManager'], timeout=30)
        return result.returncode == 0

    @log_operation_errors("WAKE_SCREEN")
    def wake_screen(self) -> bool:
        """Force screen to wake up."""
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        result = subprocess.run(
            ['xset', 'dpms', 'force', 'on'],
            env=env,
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0

    @log_operation_errors("TAKE_SCREENSHOT", False)
    def take_screenshot(self, output_path: str) -> bool:
        """Take a screenshot of the main display (:0)."""
        # Ensure scrot is installed
        if shutil.which('scrot') is None:
            self.install_packages(['scrot'])

        env = os.environ.copy()

        # 1. Try to piggyback off existing X session
        # Find who is logged in on a display
        display = ":0" # Default
        try:
             # Run 'w -h' -> 'user   tty7   :0'
             w_cmd = subprocess.run(['w', '-h'], capture_output=True, text=True)
             if w_cmd.returncode == 0:
                 for line in w_cmd.stdout.splitlines():
                     parts = line.split()
                     # Look for a part starting with : (e.g. :0 or :1)
                     for part in parts:
                         if part.startswith(':'):
                             display = part
                             break
        except:
             pass

        env['DISPLAY'] = display
        env['XAUTHORITY'] = f"/home/{os.environ.get('SUDO_USER', 'rise')}/.Xauthority"

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ['scrot', '--overwrite', output_path],
            env=env,
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            self.logger.log_error(
                RuntimeError(f"Screenshot failed: {result.stderr}"),
                "TAKE_SCREENSHOT"
            )
        return result.returncode == 0

    @log_operation_errors("GET_RISE_STATUS")
    def get_rise_player_status(self) -> Dict[str, Any]:
        """Get detailed status of Rise Player and its renderer."""
        status = {
            "service_active": False,
            "renderer_running": False,
            "renderer_count": 0,
            "memory_usage_mb": 0.0
        }

        # Check Service
        svc_result = subprocess.run(
            ['systemctl', 'is-active', 'rise-vision-player'],
            capture_output=True, text=True
        )
        status["service_active"] = (svc_result.returncode == 0)

        # Check Renderer (Chrome/Chromium)
        # Rise Player usually spawns 'chrome' or 'chromium' processes
        try:
            # Using pgrep to find processes
            pgrep = subprocess.run(
                ['pgrep', '-f', '-l', 'chrome|chromium'],
                capture_output=True, text=True
            )
            if pgrep.returncode == 0:
                lines = pgrep.stdout.strip().split('\n')
                status["renderer_count"] = len(lines)
                status["renderer_running"] = status["renderer_count"] > 0

                # Get memory usage (RSS)
                ps = subprocess.run(
                    ['ps', '-o', 'rss=', '-p', ','.join([line.split()[0] for line in lines])],
                    capture_output=True, text=True
                )
                if ps.returncode == 0:
                    total_kb = sum(int(x) for x in ps.stdout.split() if x.strip().isdigit())
                    status["memory_usage_mb"] = total_kb / 1024

        except Exception as e:
            self.logger.log_error(e, "GET_RISE_STATUS_PROCESS")

        return status

    def get_uptime(self) -> str:
        """Get system uptime in human-readable format."""
        try:
            with open('/proc/uptime') as f:
                uptime_seconds = float(f.readline().split()[0])

            days = int(uptime_seconds // (24 * 3600))
            uptime_seconds %= (24 * 3600)
            hours = int(uptime_seconds // 3600)
            uptime_seconds %= 3600
            minutes = int(uptime_seconds // 60)

            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            parts.append(f"{minutes}m")

            return " ".join(parts)
        except Exception:
            return "Unknown"

    @log_operation_errors("GET_ACTIVE_INTERFACE")
    def get_active_interface(self) -> Dict[str, str]:
        """Get active network interface and IP."""
        try:
            import socket

            import psutil
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()

            for interface, stat in stats.items():
                if interface == 'lo':
                    continue
                if stat.isup:
                    if interface in addrs:
                        for addr in addrs[interface]:
                            if addr.family == socket.AF_INET:
                                return {"interface": interface, "ip": addr.address}
            return {"interface": "None", "ip": "Unknown"}
        except Exception:
            return {"interface": "Unknown", "ip": "Unknown"}

    @log_operation_errors("GET_PING_LATENCY")
    def get_ping_latency(self, target: str = "8.8.8.8") -> Optional[float]:
        """Get ping latency in ms."""
        try:
            # -c 1 (count), -W 2 (timeout 2s)
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', target],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                # Parse output: time=14.2 ms
                import re
                match = re.search(r'time=([\d.]+)', result.stdout)
                if match:
                    return float(match.group(1))
            return None
        except Exception:
            return None

    @log_operation_errors("TOGGLE_RISE_PLAYER")
    def toggle_rise_player(self, action: str) -> bool:
        """Start or Stop rise-vision-player service."""
        if action not in ['start', 'stop', 'restart']:
            return False

        result = self.sudo.run_command(
            ['systemctl', action, 'rise-vision-player'],
            timeout=30
        )
        return result.returncode == 0


