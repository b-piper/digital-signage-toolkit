"""Watchdog management module."""
import os
import shlex
import threading
from pathlib import Path
from typing import Optional

from ..utils.config import Config
from ..utils.error_handling import log_operation_errors
from ..utils.logger import get_logger
from ..utils.sudo_handler import SudoHandler
from ..utils.validators import sanitize_for_python_string, validate_script_path


class WatchdogManager:
    """Manages the Rise Vision player via systemd service."""

    def __init__(self, sudo_handler: SudoHandler, config: Config):
        self.sudo = sudo_handler
        self.config = config
        self.log_path = Path(config.expand_path('paths.log_path'))
        self.player_startup = config.expand_path('paths.player_startup')
        self.service_name = config.get('watchdog.service_name', 'rise-vision-player')
        self.service_file = Path(config.get('watchdog.service_file', f'/etc/systemd/system/{self.service_name}.service'))
        # Use the real user, not root
        self.current_user = Config.get_real_user()
        self.current_home = config.get_real_user_home()
        self.logger = get_logger()
        self._service_creation_lock = threading.Lock()  # Prevent race conditions
        self.last_error = ""  # Human-readable error from last failed operation

    @log_operation_errors("CHECK_SERVICE_STATUS")
    def is_enabled(self) -> bool:
        """Check if systemd service is enabled and active."""
        # Check if service file exists
        if not self.service_file.exists():
            return False

        # Check if service is enabled
        result = self.sudo.run_command(
            ['systemctl', 'is-enabled', self.service_name],
            timeout=5,
            allowed_exit_codes=[0, 1] # 1 means disabled
        )
        if result.returncode != 0:
            return False

        # Check if service is active
        result = self.sudo.run_command(
            ['systemctl', 'is-active', self.service_name],
            timeout=5,
            allowed_exit_codes=[0, 3] # 3 means inactive
        )
        return result.returncode == 0

    def _validate_player_startup_path(self) -> tuple[bool, Optional[Path]]:
        """Validate and resolve player startup path.

        Returns:
            Tuple of (is_valid, resolved_path)
        """
        try:
            # Expand and resolve path using the real user's home directory if needed
            startup_path_str = self.player_startup
            if startup_path_str.startswith('~'):
                startup_path_str = startup_path_str.replace('~', self.current_home, 1)
            player_path = Path(startup_path_str).expanduser().resolve()

            # If the default path doesn't exist, check common fallback paths
            # (Rise Vision updates often change binary locations)
            if not player_path.exists():
                fallbacks = [
                    Path(self.current_home) / 'rvplayer' / 'rvplayer',
                    Path(self.current_home) / 'rvplayer' / 'rvplayer.sh',
                    Path(self.current_home) / 'rvplayer' / 'scripts' / 'start.sh',
                    Path(self.current_home) / 'RiseVisionPlayer' / 'RiseVisionPlayer'
                ]
                for fallback_path in fallbacks:
                    if fallback_path.exists() and fallback_path.is_file():
                        player_path = fallback_path
                        break

            # Validate path doesn't contain shell metacharacters
            if not validate_script_path(str(player_path)):
                self.logger.log_error(
                    ValueError(f"Player startup path contains invalid characters: {self.player_startup}"),
                    "VALIDATE_PLAYER_STARTUP"
                )
                return (False, None)

            # Check if file exists
            if not player_path.exists():
                self.logger.log_error(
                    FileNotFoundError(f"Player startup script not found: {player_path}"),
                    "VALIDATE_PLAYER_STARTUP"
                )
                return (False, None)

            # Check if it's a file (not directory)
            if not player_path.is_file():
                self.logger.log_error(
                    ValueError(f"Player startup path is not a file: {player_path}"),
                    "VALIDATE_PLAYER_STARTUP"
                )
                return (False, None)

            return (True, player_path)
        except Exception as e:
            self.logger.log_error(e, "VALIDATE_PLAYER_STARTUP")
            return (False, None)

    def create_systemd_service(self) -> bool:
        """Create systemd service file for Rise Vision player."""
        # Use lock to prevent race conditions
        with self._service_creation_lock:
            try:
                # Validate player startup path
                is_valid, player_path = self._validate_player_startup_path()
                if not is_valid or player_path is None:
                    return False

                # Get XAUTHORITY path (may not exist, but try to set it)
                xauth_path = Path(self.current_home) / '.Xauthority'
                xauth_str = str(xauth_path) if xauth_path.exists() else f'/home/{self.current_user}/.Xauthority'

                # Get player startup directory (use validated absolute path)
                player_dir = str(player_path.parent)
                # Use absolute path for ExecStart, properly escaped
                exec_start_path = shlex.quote(str(player_path))

                # Create systemd service file content
                exec_cmd = f"/bin/bash {exec_start_path}" if player_path.suffix == '.sh' else exec_start_path

                service_content = f"""[Unit]
Description=Rise Vision Player Service
After=graphical.target network-online.target
Wants=network-online.target
Requires=graphical.target

[Service]
Type=simple
User={self.current_user}
Group={self.current_user}
WorkingDirectory={shlex.quote(player_dir)}
Environment="DISPLAY=:0"
Environment="XAUTHORITY={shlex.quote(xauth_str)}"
Environment="HOME={shlex.quote(self.current_home)}"
ExecStart={exec_cmd}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=rise-vision-player

# Security settings
NoNewPrivileges=true
PrivateTmp=false

[Install]
WantedBy=graphical.target
"""

                # Write to temp file first, then move (atomic operation)
                import tempfile
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.service') as tmp_file:
                        tmp_file.write(service_content)
                        tmp_path = tmp_file.name

                    # Copy to systemd directory using sudo
                    result = self.sudo.run_command(
                        ['cp', tmp_path, str(self.service_file)],
                        timeout=10
                    )

                    if result.returncode != 0:
                        self.logger.log_error(
                            RuntimeError(f"Failed to copy service file: {result.stderr}"),
                            "CREATE_SYSTEMD_SERVICE"
                        )
                        return False

                    # Reload systemd daemon
                    reload_result = self.sudo.run_command(
                        ['systemctl', 'daemon-reload'],
                        timeout=10
                    )

                    if reload_result.returncode != 0:
                        self.logger.log_error(
                            RuntimeError(f"Failed to reload systemd: {reload_result.stderr}"),
                            "CREATE_SYSTEMD_SERVICE"
                        )
                        return False

                    return True
                finally:
                    # Always cleanup temp file
                    if tmp_path:
                        try:
                            os.unlink(tmp_path)
                        except Exception as e:
                            self.logger.log_error(e, "CLEANUP_TEMP_FILE")
            except Exception as e:
                self.logger.log_error(e, "CREATE_SYSTEMD_SERVICE")
                return False

    @log_operation_errors("ENABLE_SYSTEMD_SERVICE")
    def enable(self) -> bool:
        """Enable and start the systemd service."""
        self.last_error = ""

        # Check if Rise Vision Player is installed first (using validation with fallbacks)
        is_valid, player_path = self._validate_player_startup_path()
        if not is_valid or player_path is None:
            self.last_error = (
                "Rise Vision Player is not installed.\n"
                f"Expected startup script at or near: {self.player_startup}\n\n"
                "Please install Rise Vision Player first via Master Setup."
            )
            self.logger.log_error(
                FileNotFoundError("Player startup script not found in configured path or fallbacks."),
                "ENABLE_SYSTEMD_SERVICE"
            )
            return False

        # Create service file if it doesn't exist
        if not self.service_file.exists():
            if not self.create_systemd_service():
                self.last_error = (
                    "Failed to create systemd service file.\n"
                    "Check logs for details."
                )
                return False

        # Enable service (start on boot)
        enable_result = self.sudo.run_command(
            ['systemctl', 'enable', self.service_name],
            timeout=10
        )
        if enable_result.returncode != 0:
            self.last_error = f"Failed to enable service: {enable_result.stderr}"
            self.logger.log_error(
                RuntimeError(f"Failed to enable service: {enable_result.stderr}"),
                "ENABLE_SYSTEMD_SERVICE"
            )
            return False

        # Start service
        start_result = self.sudo.run_command(
            ['systemctl', 'start', self.service_name],
            timeout=10
        )

        if start_result.returncode == 0:
            self.logger.log_operation(
                "WATCHDOG_ENABLED",
                self.current_user,
                f"Systemd service {self.service_name} enabled and started",
                True
            )
        else:
            self.last_error = f"Service enabled but failed to start: {start_result.stderr}"
            self.logger.log_error(
                RuntimeError(f"Failed to start service: {start_result.stderr}"),
                "ENABLE_SYSTEMD_SERVICE"
            )

        return start_result.returncode == 0

    @log_operation_errors("DISABLE_SYSTEMD_SERVICE")
    def disable(self) -> bool:
        """Disable and stop the systemd service."""
        # Stop service first
        if self.is_enabled():
            stop_result = self.sudo.run_command(
                ['systemctl', 'stop', self.service_name],
                timeout=10
            )
            if stop_result.returncode != 0:
                self.logger.log_error(
                    RuntimeError(f"Failed to stop service: {stop_result.stderr}"),
                    "DISABLE_SYSTEMD_SERVICE"
                )

        # Disable service
        result = self.sudo.run_command(
            ['systemctl', 'disable', self.service_name],
            timeout=10
        )

        if result.returncode == 0:
            self.logger.log_operation(
                "WATCHDOG_DISABLED",
                self.current_user,
                f"Systemd service {self.service_name} disabled",
                True
            )
        else:
            self.logger.log_error(
                RuntimeError(f"Failed to disable service: {result.stderr}"),
                "DISABLE_SYSTEMD_SERVICE"
            )

        return result.returncode == 0

    @log_operation_errors("GET_SERVICE_STATUS", {'active': False, 'enabled': False, 'status_output': ''})
    def get_service_status(self) -> dict:
        """Get systemd service status information."""
        # Use single systemctl show command for efficiency
        result = self.sudo.run_command(
            ['systemctl', 'show', self.service_name,
             '--property=ActiveState,UnitFileState', '--no-pager'],
            timeout=10,
            allowed_exit_codes=[0, 3, 4]
        )

        if result.returncode == 0:
            active = 'active' in result.stdout.lower()
            enabled = 'enabled' in result.stdout.lower()

            # Get full status for output
            status_result = self.sudo.run_command(
                ['systemctl', 'status', self.service_name, '--no-pager', '-l'],
                timeout=10,
                allowed_exit_codes=[0, 3, 4]
            )

            return {
                'active': active,
                'enabled': enabled,
                'status_output': status_result.stdout if status_result.returncode == 0 else ''
            }

        return {'active': False, 'enabled': False, 'status_output': ''}

    @log_operation_errors("STOP_PLAYER")
    def stop_player(self) -> bool:
        """Stop the Rise Vision player."""
        self.sudo.run_command(
            ['pkill', '-f', 'rvplayer'],
            timeout=10,
            allowed_exit_codes=[0, 1]
        )
        # pkill returns non-zero if no process found, which is OK
        return True

    def _generate_cache_cleanup_script(self) -> Optional[str]:
        """Generate safe cache cleanup script with validated paths.

        Returns:
            Script content as string, or None if validation fails
        """
        # Validate player startup path
        is_valid, player_path = self._validate_player_startup_path()
        if not is_valid or player_path is None:
            return None

        # Get application root correctly based on the toolkit's own file location
        # __file__ = core/watchdog.py
        # parent = core
        # parent.parent = digital_signage_toolkit
        # parent.parent.parent = root directory
        try:
            app_root = Path(__file__).resolve().parent.parent.parent
            if not app_root.exists():
                self.logger.log_error(
                    ValueError(f"Application root not found: {app_root}"),
                    "GENERATE_CACHE_CLEANUP_SCRIPT"
                )
                return None

            # Sanitize path for Python string interpolation
            safe_path = sanitize_for_python_string(str(app_root))

            # Generate script with safe path
            cache_cleanup_script = f"""#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add application to path (safely interpolated)
sys.path.insert(0, {safe_path})

try:
    from digital_signage_toolkit.core.software_installer import SoftwareInstaller
    from digital_signage_toolkit.utils.config import Config
    from digital_signage_toolkit.utils.sudo_handler import SudoHandler

    installer = SoftwareInstaller(SudoHandler(), Config())
    installer.clear_rise_cache(aggressive=True, log_callback=None)
except Exception as e:
    # Log error but continue with reboot
    import sys
    sys.stderr.write(f"Cache cleanup failed: {{e}}\\n")
"""
            return cache_cleanup_script
        except Exception as e:
            self.logger.log_error(e, "GENERATE_CACHE_CLEANUP_SCRIPT")
            return None

    def configure_reboot_schedule(self, hour: int = 3, minute: int = 0) -> bool:
        """Configure automatic reboot schedule using systemd timer with cache cleanup."""
        # Validate inputs
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            self.logger.log_error(
                ValueError(f"Invalid schedule time: {hour:02d}:{minute:02d}"),
                "CONFIGURE_REBOOT_SCHEDULE"
            )
            return False

        timer_name = 'scc-reboot'
        timer_file = Path(f'/etc/systemd/system/{timer_name}.timer')
        service_file = Path(f'/etc/systemd/system/{timer_name}.service')

        try:
            # Generate cache cleanup script with validated paths
            cache_cleanup_script = self._generate_cache_cleanup_script()
            if not cache_cleanup_script:
                self.logger.log_error(
                    RuntimeError("Failed to generate cache cleanup script"),
                    "CONFIGURE_REBOOT_SCHEDULE"
                )
                return False

            # Write cache cleanup script
            cleanup_script_path = Path('/usr/local/bin/scc-cache-cleanup.py')
            import tempfile
            tmp_script_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as tmp_script:
                    tmp_script.write(cache_cleanup_script)
                    tmp_script_path = tmp_script.name

                # Copy script to /usr/local/bin
                cp_result = self.sudo.run_command(['cp', tmp_script_path, str(cleanup_script_path)], timeout=10)
                if cp_result.returncode != 0:
                    self.logger.log_error(
                        RuntimeError(f"Failed to copy cleanup script: {cp_result.stderr}"),
                        "CONFIGURE_REBOOT_SCHEDULE"
                    )
                    return False

                chmod_result = self.sudo.run_command(['chmod', '+x', str(cleanup_script_path)], timeout=10)
                if chmod_result.returncode != 0:
                    self.logger.log_error(
                        RuntimeError(f"Failed to make script executable: {chmod_result.stderr}"),
                        "CONFIGURE_REBOOT_SCHEDULE"
                    )
                    return False
            finally:
                # Always cleanup temp file
                if tmp_script_path:
                    try:
                        os.unlink(tmp_script_path)
                    except Exception as e:
                        self.logger.log_error(e, "CLEANUP_TEMP_SCRIPT")

            # Create service file (use shlex.quote for safety)
            service_content = f"""[Unit]
Description=Scheduled Reboot with Cache Cleanup
Before=shutdown.target reboot.target

[Service]
Type=oneshot
ExecStart={shlex.quote(str(cleanup_script_path))}
ExecStart=/sbin/shutdown -r now
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

            # Create timer file
            timer_content = f"""[Unit]
Description=Scheduled Reboot Timer
Requires={timer_name}.service

[Timer]
OnCalendar=*-*-* {hour:02d}:{minute:02d}:00
Persistent=true

[Install]
WantedBy=timers.target
"""

            # Write service and timer files
            tmp_service_path = None
            tmp_timer_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.service') as tmp_file:
                    tmp_file.write(service_content)
                    tmp_service_path = tmp_file.name

                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.timer') as tmp_file:
                    tmp_file.write(timer_content)
                    tmp_timer_path = tmp_file.name

                # Copy files to systemd directory
                result1 = self.sudo.run_command(
                    ['cp', tmp_service_path, str(service_file)],
                    timeout=10
                )
                result2 = self.sudo.run_command(
                    ['cp', tmp_timer_path, str(timer_file)],
                    timeout=10
                )

                if result1.returncode != 0:
                    self.logger.log_error(
                        RuntimeError(f"Failed to copy service file: {result1.stderr}"),
                        "CONFIGURE_REBOOT_SCHEDULE"
                    )
                    return False

                if result2.returncode != 0:
                    self.logger.log_error(
                        RuntimeError(f"Failed to copy timer file: {result2.stderr}"),
                        "CONFIGURE_REBOOT_SCHEDULE"
                    )
                    return False

                # Reload systemd and enable timer
                reload_result = self.sudo.run_command(['systemctl', 'daemon-reload'], timeout=10)
                if reload_result.returncode != 0:
                    self.logger.log_error(
                        RuntimeError(f"Failed to reload systemd: {reload_result.stderr}"),
                        "CONFIGURE_REBOOT_SCHEDULE"
                    )
                    return False

                enable_result = self.sudo.run_command(
                    ['systemctl', 'enable', '--now', f'{timer_name}.timer'],
                    timeout=10
                )

                if enable_result.returncode == 0:
                    self.logger.log_operation(
                        "REBOOT_SCHEDULE_SET",
                        self.current_user,
                        f"Reboot scheduled for {hour:02d}:{minute:02d} with cache cleanup",
                        True
                    )
                else:
                    self.logger.log_error(
                        RuntimeError(f"Failed to enable timer: {enable_result.stderr}"),
                        "CONFIGURE_REBOOT_SCHEDULE"
                    )

                return enable_result.returncode == 0
            finally:
                # Always cleanup temp files
                for tmp_path in [tmp_service_path, tmp_timer_path]:
                    if tmp_path:
                        try:
                            os.unlink(tmp_path)
                        except Exception as e:
                            self.logger.log_error(e, "CLEANUP_TEMP_FILE")
        except Exception as e:
            self.logger.log_error(e, "CONFIGURE_REBOOT_SCHEDULE")
            return False

    @log_operation_errors("CONFIGURE_AUTOSTART")
    def configure_autostart(self) -> bool:
        """Configure Rise Vision autostart."""
        autostart_dir = Path(self.config.expand_path('paths.autostart_dir'))
        autostart_file = autostart_dir / 'rise-vision.desktop'

        # Validate player startup path
        is_valid, player_path = self._validate_player_startup_path()
        if not is_valid or player_path is None:
            return False

        autostart_dir.mkdir(parents=True, exist_ok=True)

        # Use validated absolute path, properly escaped. Check if it requires bash
        exec_cmd = f"bash {shlex.quote(str(player_path))}" if player_path.suffix == '.sh' else shlex.quote(str(player_path))

        desktop_content = f"""[Desktop Entry]
Type=Application
Name=Rise Vision Player
Exec={exec_cmd}
X-GNOME-Autostart-enabled=true
Comment=Start Rise Vision Player
"""

        with open(autostart_file, 'w') as f:
            f.write(desktop_content)

        os.chmod(autostart_file, 0o755)
        return True

