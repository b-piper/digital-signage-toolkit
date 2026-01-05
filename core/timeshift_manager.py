"""Timeshift system restore management module."""
import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict, Callable
from datetime import datetime
from digital_signage_toolkit.utils.sudo_handler import SudoHandler
from digital_signage_toolkit.utils.config import Config
from digital_signage_toolkit.utils.logger import get_logger
from digital_signage_toolkit.utils.error_handling import log_operation_errors


class TimeshiftManager:
    """Manages Timeshift snapshots for system restore."""
    
    def __init__(self, sudo_handler: SudoHandler, config: Config):
        self.sudo = sudo_handler
        self.config = config
        self.logger = get_logger()
    
    def is_installed(self) -> bool:
        """Check if Timeshift is installed."""
        return subprocess.run(['which', 'timeshift'], capture_output=True).returncode == 0
    
    @log_operation_errors("INSTALL_TIMESHIFT")
    def install(self, log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Install Timeshift."""
        if self.is_installed():
            if log_callback:
                log_callback("Timeshift is already installed")
            return True
        
        if log_callback:
            log_callback("Installing Timeshift...")
        
        result = self.sudo.run_command(
            ['apt-get', 'install', '-y', 'timeshift'],
            timeout=300
        )
        
        if result.returncode == 0:
            if log_callback:
                log_callback("Timeshift installed successfully")
            return True
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            if log_callback:
                log_callback(f"Timeshift installation failed: {error_msg}")
            self.logger.log_error(
                RuntimeError(f"Timeshift installation failed: {error_msg}"),
                "INSTALL_TIMESHIFT"
            )
            return False
    
    @log_operation_errors("CONFIGURE_TIMESHIFT")
    def configure(self, snapshot_type: str = "RSYNC", 
                 snapshot_location: str = "/timeshift",
                 log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Configure Timeshift settings."""
        if not self.is_installed():
            if not self.install(log_callback):
                return False
        
        if log_callback:
            log_callback("Configuring Timeshift...")
        
        # Validate snapshot location path
        from digital_signage_toolkit.utils.validators import validate_path
        if not validate_path(snapshot_location, must_be_absolute=True):
            self.logger.log_error(
                ValueError(f"Invalid snapshot location: {snapshot_location}"),
                "CONFIGURE_TIMESHIFT"
            )
            return False
        
        # Set snapshot type
        result = self.sudo.run_command(
            ['timeshift', '--snapshot-device', snapshot_location],
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            self.logger.log_error(
                RuntimeError(f"Failed to configure Timeshift: {error_msg}"),
                "CONFIGURE_TIMESHIFT"
            )
        
        # Create snapshot location if it doesn't exist
        snapshot_path = Path(snapshot_location)
        if not snapshot_path.exists():
            mkdir_result = self.sudo.run_command(['mkdir', '-p', snapshot_location], timeout=10)
            if mkdir_result.returncode != 0:
                self.logger.log_error(
                    RuntimeError(f"Failed to create snapshot directory: {mkdir_result.stderr}"),
                    "CONFIGURE_TIMESHIFT"
                )
        
        if log_callback:
            log_callback("Timeshift configured")
        return True
    
    def create_snapshot(self, description: Optional[str] = None,
                       log_callback: Optional[Callable[[str], None]] = None,
                       completion_callback: Optional[Callable[[bool], None]] = None) -> None:
        """Create a system snapshot (async)."""
        if not self.is_installed():
            if log_callback:
                log_callback("Timeshift is not installed. Installing...")
            if not self.install(log_callback):
                if completion_callback:
                    completion_callback(False)
                return
        
        if description is None:
            description = f"Auto-snapshot {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if log_callback:
            log_callback(f"Creating snapshot: {description}")
            log_callback("This may take several minutes...")
        
        def run_snapshot():
            try:
                # Use --scripted mode for non-interactive operation
                result = self.sudo.run_command(
                    ['timeshift', '--create', '--comments', description, '--scripted'],
                    timeout=3600  # 1 hour timeout
                )
                
                if result.returncode == 0:
                    if log_callback:
                        log_callback("Snapshot created successfully")
                    if completion_callback:
                        completion_callback(True)
                else:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    if log_callback:
                        log_callback(f"Snapshot creation failed: {error_msg}")
                    self.logger.log_error(
                        RuntimeError(f"Snapshot creation failed: {error_msg}"),
                        "CREATE_SNAPSHOT"
                    )
                    if completion_callback:
                        completion_callback(False)
            except subprocess.TimeoutExpired:
                if log_callback:
                    log_callback("Snapshot creation timed out")
                self.logger.log_error(
                    TimeoutError("Snapshot creation timed out after 3600 seconds"),
                    "CREATE_SNAPSHOT"
                )
                if completion_callback:
                    completion_callback(False)
            except Exception as e:
                if log_callback:
                    log_callback(f"Snapshot creation error: {e}")
                self.logger.log_error(e, "CREATE_SNAPSHOT")
                if completion_callback:
                    completion_callback(False)
        
        import threading
        threading.Thread(target=run_snapshot, daemon=True).start()
    
    def list_snapshots(self) -> List[Dict[str, str]]:
        """List all available snapshots."""
        if not self.is_installed():
            return []
        
        try:
            result = self.sudo.run_command(
                ['timeshift', '--list'],
                timeout=30
            )
            
            if result.returncode != 0:
                return []
            
            snapshots = []
            lines = result.stdout.split('\n')
            current_snapshot = None
            
            for line in lines:
                line = line.strip()
                # Look for snapshot number/ID
                if line.startswith('Snapshot') or 'Snapshot' in line:
                    # Try to extract snapshot info
                    # Format varies, try multiple patterns
                    if '#' in line:
                        parts = line.split('#')
                        if len(parts) > 1:
                            snapshot_id = parts[1].split()[0] if parts[1].split() else None
                            if snapshot_id:
                                current_snapshot = {'id': snapshot_id, 'date': '', 'description': ''}
                                snapshots.append(current_snapshot)
                    elif line.split():
                        parts = line.split()
                        # Look for snapshot identifier
                        for i, part in enumerate(parts):
                            if part.isdigit() or 'snapshot' in part.lower():
                                snapshot_id = part
                                current_snapshot = {'id': snapshot_id, 'date': '', 'description': line}
                                snapshots.append(current_snapshot)
                                break
                elif current_snapshot and ('Date' in line or 'Created' in line):
                    # Extract date information
                    current_snapshot['date'] = line
                    current_snapshot['description'] = line
            
            # If parsing failed, try simpler approach - just get snapshot directories
            if not snapshots:
                # Try listing snapshot directories directly
                snapshot_location = self.config.get('timeshift.snapshot_location', '/timeshift/snapshots')
                result = self.sudo.run_command(['ls', '-1', snapshot_location], timeout=10)
                if result.returncode == 0 and result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            snapshots.append({
                                'id': line.strip(),
                                'date': '',
                                'description': f"Snapshot {line.strip()}"
                            })
            
            return snapshots
        except Exception:
            return []
    
    def restore_snapshot(self, snapshot_id: str,
                        log_callback: Optional[Callable[[str], None]] = None,
                        completion_callback: Optional[Callable[[bool], None]] = None) -> None:
        """Restore system from a snapshot (async, requires reboot)."""
        # Validate snapshot ID to prevent injection
        from digital_signage_toolkit.utils.validators import validate_snapshot_id
        
        if not validate_snapshot_id(snapshot_id):
            self.logger.log_error(
                ValueError(f"Invalid snapshot ID: {snapshot_id}"),
                "RESTORE_SNAPSHOT"
            )
            if log_callback:
                log_callback("Invalid snapshot ID")
            if completion_callback:
                completion_callback(False)
            return
        
        if not self.is_installed():
            if log_callback:
                log_callback("Timeshift is not installed")
            if completion_callback:
                completion_callback(False)
            return
        
        if log_callback:
            log_callback(f"Restoring snapshot: {snapshot_id}")
            log_callback("⚠️  WARNING: This will restore the entire system state!")
            log_callback("The system will reboot after restoration.")
        
        def run_restore():
            try:
                # Use --restore with snapshot ID
                result = self.sudo.run_command(
                    ['timeshift', '--restore', '--snapshot', snapshot_id, '--scripted'],
                    timeout=3600
                )
                
                if result.returncode == 0:
                    if log_callback:
                        log_callback("Restoration complete. Rebooting...")
                    # Reboot after successful restore
                    reboot_result = self.sudo.run_command(['reboot'], timeout=5)
                    if reboot_result.returncode != 0:
                        self.logger.log_error(
                            RuntimeError(f"Failed to reboot after restore: {reboot_result.stderr}"),
                            "RESTORE_SNAPSHOT"
                        )
                    if completion_callback:
                        completion_callback(True)
                else:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    if log_callback:
                        log_callback(f"Restoration failed: {error_msg}")
                    self.logger.log_error(
                        RuntimeError(f"Snapshot restoration failed: {error_msg}"),
                        "RESTORE_SNAPSHOT"
                    )
                    if completion_callback:
                        completion_callback(False)
            except subprocess.TimeoutExpired:
                if log_callback:
                    log_callback("Restoration timed out")
                self.logger.log_error(
                    TimeoutError("Snapshot restoration timed out after 3600 seconds"),
                    "RESTORE_SNAPSHOT"
                )
                if completion_callback:
                    completion_callback(False)
            except Exception as e:
                if log_callback:
                    log_callback(f"Restoration error: {e}")
                self.logger.log_error(e, "RESTORE_SNAPSHOT")
                if completion_callback:
                    completion_callback(False)
        
        import threading
        threading.Thread(target=run_restore, daemon=True).start()
    
    @log_operation_errors("DELETE_SNAPSHOT")
    def delete_snapshot(self, snapshot_id: str,
                       log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Delete a snapshot."""
        # Validate snapshot ID to prevent injection
        from digital_signage_toolkit.utils.validators import validate_snapshot_id
        
        if not validate_snapshot_id(snapshot_id):
            self.logger.log_error(
                ValueError(f"Invalid snapshot ID: {snapshot_id}"),
                "DELETE_SNAPSHOT"
            )
            return False
        
        if not self.is_installed():
            return False
        
        if log_callback:
            log_callback(f"Deleting snapshot: {snapshot_id}")
        
        try:
            result = self.sudo.run_command(
                ['timeshift', '--delete', '--snapshot', snapshot_id, '--scripted'],
                timeout=600
            )
            
            if result.returncode == 0:
                if log_callback:
                    log_callback("Snapshot deleted successfully")
                return True
            else:
                if log_callback:
                    log_callback(f"Failed to delete snapshot: {result.stderr}")
                return False
        except Exception as e:
            if log_callback:
                log_callback(f"Delete snapshot error: {e}")
            return False

