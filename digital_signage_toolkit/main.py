#!/usr/bin/env python3
"""Main entry point for Digital Signage Toolkit."""
import atexit
import os
import sys
from pathlib import Path

from .gui.main_window import MainWindow


def main():
    """Main application entry point."""
    import argparse
    import json

    # 1. Singleton Lock (File-based - Professional Standard)
    # Prevents Cron and GUI from colliding
    # Note: fcntl is Linux-only, use it only if available
    lock_file = None
    try:
        import fcntl
        lock_file_path = Path.home() / '.dst-toolkit' / 'app.lock'
        lock_file_path.parent.mkdir(parents=True, exist_ok=True)

        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Write PID to lock file for debugging
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        atexit.register(lambda: lock_file.close() if lock_file else None)
    except (ImportError, OSError):
        # On Windows or if lock fails
        if sys.platform == 'linux':
            print("Error: Another instance of Digital Signage Toolkit is already running.")
            sys.exit(1)

    # Initialize logging
    from .utils.logger import get_logger
    logger = get_logger()

    # CLI Argument Parsing
    parser = argparse.ArgumentParser(description="Digital Signage Toolkit (GUI & Remote Manager)")
    parser.add_argument('--status', action='store_true', help="Output system health status as JSON (Headless)")
    parser.add_argument('--heal', action='store_true', help="Run Emergency Heal routine (Headless)")
    parser.add_argument('--screenshot', type=str, help="Take a screenshot to the specified path (Headless)")
    parser.add_argument('--gui', action='store_true', help="Force GUI mode (Default if no args)")
    parser.add_argument('--config', type=str, help="Path to custom config.json file (for fleet deployment)")
    parser.add_argument('--no-health-server', action='store_true', help="Disable HTTP health check server")
    parser.add_argument('--health-port', type=int, default=8080, help="Port for health check server (default: 8080)")

    args = parser.parse_args()

    # Check for root/sudo (Strict enforcement on Linux)
    if sys.platform == 'linux' and os.geteuid() != 0:
        # Avoid creating the QtApp for headless commands
        if not args.status and not args.heal and not args.screenshot:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app_temp = QApplication.instance()
            if not app_temp:
                app_temp = QApplication(sys.argv)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Fatal Error")
            msg.setText("This application must be run as root.\nPlease use the official desktop shortcut (pkexec) to launch.")
            msg.exec()
        else:
            print("Fatal Error: Must be run as root (uid 0)")
        sys.exit(1)

    # Apply custom config if provided (must happen before health server starts)
    if args.config:
        os.environ['DST_CONFIG_PATH'] = args.config
        logger.app_logger.info(f"Using custom config: {args.config}")

    # Start health check server (background, for monitoring)
    if not args.no_health_server and not args.status:
        try:
            from .core.health_server import start_health_server
            if start_health_server(args.health_port):
                logger.app_logger.info(f"Health server started on port {args.health_port}")
        except Exception as e:
            logger.app_logger.warning(f"Could not start health server: {e}")

    # -- Headless Mode: Status --
    if args.status:
        try:
            from .core.hardware_monitor import HardwareMonitor
            from .core.system_ops import SystemOperations
            from .utils.sudo_handler import SudoHandler

            sudo = SudoHandler()
            ops = SystemOperations(sudo)
            hw = HardwareMonitor()

            rise_status = ops.get_rise_player_status()

            status = {
                "hostname": ops.get_hostname(),
                "uptime": ops.get_uptime(),
                "internet": ops.check_internet(),
                "rise_player": rise_status,
                "disk_free_gb": hw.get_disk_usage().get("free", 0) / (1024**3),
                "cpu_temp": hw.get_cpu_temperature(),
                "memory_percent": hw.get_memory_usage().get("percent", 0)
            }
            print(json.dumps(status, indent=4))
            return
        except Exception as e:
            logger.log_error(e, "HEADLESS_STATUS")
            print(json.dumps({"error": str(e)}))
            sys.exit(1)

    # -- Headless Mode: Screenshot --
    if args.screenshot:
        try:
            from .core.system_ops import SystemOperations
            from .utils.sudo_handler import SudoHandler

            sudo = SudoHandler()
            ops = SystemOperations(sudo)

            if ops.take_screenshot(args.screenshot):
                print(f"{{\"success\": true, \"path\": \"{args.screenshot}\"}}")
            else:
                print("{\"success\": false, \"error\": \"Screenshot failed\"}")
                sys.exit(1)
            return
        except Exception as e:
            logger.log_error(e, "HEADLESS_SCREENSHOT")
            print(f"{{\"success\": false, \"error\": \"{str(e)}\"}}")
            sys.exit(1)

    # -- Headless Mode: Heal --
    if args.heal:
        print("Starting Emergency Heal (Headless)...")
        try:
            from .core.software_installer import SoftwareInstaller
            from .core.system_ops import SystemOperations
            from .utils.config import Config
            from .utils.sudo_handler import SudoHandler

            sudo = SudoHandler()
            config = Config()
            ops = SystemOperations(sudo)
            installer = SoftwareInstaller(sudo, config)

            # 1. Clear Cache
            print("1/3 Clearing Cache...")
            installer.clear_rise_cache(aggressive=True)

            # 2. Fix Permissions
            print("2/3 Fixing Permissions...")
            installer.fix_rise_permissions(config.expand_path('paths.player_dir'))

            # 3. Restart Player
            print("3/3 Restarting Player...")
            ops.toggle_rise_player('restart')

            print("{\"success\": true, \"message\": \"Emergency Heal Complete\"}")
            logger.log_operation("HEADLESS_HEAL", "root", "Completed Emergency Heal")
            return
        except Exception as e:
            logger.log_error(e, "HEADLESS_HEAL")
            print(f"{{\"success\": false, \"error\": \"{str(e)}\"}}")
            sys.exit(1)

    # -- GUI Mode --

    # Check if running on Linux (GUI only check)
    if sys.platform != 'linux':
        logger.app_logger.warning("Warning: This application is designed for Linux systems.")

    # Create application
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("Digital Signage Toolkit")
    app.setOrganizationName("Southwestern CC")
    QGuiApplication.setDesktopFileName("digital-signage-toolkit.desktop")

    # Set dark theme style
    app.setStyle('Fusion')

    # Import and apply modern theme
    from .gui.themes import ModernTheme
    app.setStyleSheet(ModernTheme.STYLESHEET)

    # Log application start
    logger.log_operation("APPLICATION_START", os.environ.get('USER', 'unknown'), "Application launched", True)

    # Create and show main window
    try:
        window = MainWindow()
        window.show()

        # Run application
        sys.exit(app.exec())
    except Exception as e:
        logger.log_error(e, "APPLICATION_START")
        raise


if __name__ == '__main__':
    main()
