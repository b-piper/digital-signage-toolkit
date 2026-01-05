#!/usr/bin/env python3
"""Main entry point for Digital Signage Toolkit."""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from digital_signage_toolkit.gui.main_window import MainWindow


def main():
    """Main application entry point."""
    import argparse
    import json
    import socket
    import sys
    
    # 0. Singleton Lock (File-based - Professional Standard)
    # Prevents Cron and GUI from colliding
    import fcntl
    lock_file_path = Path.home() / '.dst-toolkit' / 'app.lock'
    lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Write PID to lock file for debugging
        lock_file.write(str(os.getpid()))
        lock_file.flush()
    except (IOError, OSError):
        print("Error: Another instance of Digital Signage Toolkit is already running.")
        sys.exit(1)

    # Check for root/sudo
    if os.geteuid() != 0:
        print("Warning: Not running as root. Some features may fail.")

    # Initialize logging
    from digital_signage_toolkit.utils.logger import get_logger
    logger = get_logger()
    
    # CLI Argument Parsing
    parser = argparse.ArgumentParser(description="Digital Signage Toolkit (GUI & Remote Manager)")
    parser.add_argument('--status', action='store_true', help="Output system health status as JSON (Headless)")
    parser.add_argument('--heal', action='store_true', help="Run Emergency Heal routine (Headless)")
    parser.add_argument('--screenshot', type=str, help="Take a screenshot to the specified path (Headless)")
    parser.add_argument('--gui', action='store_true', help="Force GUI mode (Default if no args)")
    parser.add_argument('--config', type=str, help="Path to custom config.json file (for fleet deployment)")
    
    args = parser.parse_args()
    
    # Apply custom config if provided
    if args.config:
        os.environ['DST_CONFIG_PATH'] = args.config
        logger.app_logger.info(f"Using custom config: {args.config}")
    
    # -- Headless Mode: Status --
    if args.status:
        try:
            from digital_signage_toolkit.utils.sudo_handler import SudoHandler
            from digital_signage_toolkit.core.system_ops import SystemOperations
            from digital_signage_toolkit.core.hardware_monitor import HardwareMonitor
            
            sudo = SudoHandler()
            ops = SystemOperations(sudo)
            hw = HardwareMonitor(sudo)
            
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
            from digital_signage_toolkit.utils.sudo_handler import SudoHandler
            from digital_signage_toolkit.core.system_ops import SystemOperations
            
            sudo = SudoHandler()
            ops = SystemOperations(sudo)
            
            if ops.take_screenshot(args.screenshot):
                print(f"{{\"success\": true, \"path\": \"{args.screenshot}\"}}")
            else:
                print(f"{{\"success\": false, \"error\": \"Screenshot failed\"}}")
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
            from digital_signage_toolkit.utils.sudo_handler import SudoHandler
            from digital_signage_toolkit.core.system_ops import SystemOperations
            from digital_signage_toolkit.core.software_installer import SoftwareInstaller
            from digital_signage_toolkit.utils.config import Config
            
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
    app = QApplication(sys.argv)
    app.setApplicationName("Digital Signage Toolkit")
    app.setOrganizationName("Southwestern CC")
    
    # Set dark theme style
    app.setStyle('Fusion')
    
    # Import and apply modern theme
    from digital_signage_toolkit.gui.themes import ModernTheme
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

