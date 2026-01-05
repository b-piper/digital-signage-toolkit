"""Configuration management module."""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Manages application configuration with system-wide and user-specific support."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Loads configuration in this order:
        1. CLI-specified config (via DST_CONFIG_PATH env var)
        2. User config: ~/.config/digital-signage-toolkit/config.json
        3. System config: /etc/digital-signage-toolkit/config.json
        4. Default config (if none exist)
        """
        self.system_config_path = Path("/etc/digital-signage-toolkit/config.json")
        self.user_config_path = Path.home() / ".config" / "digital-signage-toolkit" / "config.json"
        
        # Priority: explicit config_path > DST_CONFIG_PATH env var > default paths
        if config_path:
            self.config_path = Path(config_path)
        elif os.environ.get('DST_CONFIG_PATH'):
            self.config_path = Path(os.environ.get('DST_CONFIG_PATH'))
        else:
            self.config_path = self.user_config_path
        
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from JSON file with fallback hierarchy."""
        # If custom config_path provided, try it first and ONLY it (for testing isolation)
        custom_path_provided = hasattr(self, 'config_path') and self.config_path != self.user_config_path
        
        if custom_path_provided:
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r') as f:
                        loaded_config = json.load(f)
                        # Only use loaded config if it's not empty
                        if loaded_config:
                            self._config = loaded_config
                            return
                except Exception:
                    # If custom path exists but is invalid, fall through to defaults
                    pass
            # Custom path doesn't exist or is invalid - use defaults directly (don't check user/system)
            self._config = self._default_config()
            return
        
        # Try user config first
        if self.user_config_path.exists():
            try:
                with open(self.user_config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Only use loaded config if it's not empty
                    if loaded_config:
                        self._config = loaded_config
                        return
            except Exception:
                pass
        
        # Try system config
        if self.system_config_path.exists():
            try:
                with open(self.system_config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Only use loaded config if it's not empty
                    if loaded_config:
                        self._config = loaded_config
                        return
            except Exception:
                pass
        
        # Use default config (fallback when no valid config files exist)
        self._config = self._default_config()
        
        # Save to user config if it doesn't exist (unless custom path was provided)
        # When custom path is provided, don't auto-save to user config
        if not custom_path_provided and not self.user_config_path.exists():
            self.user_config_path.parent.mkdir(parents=True, exist_ok=True)
            # Temporarily switch to user config path for saving
            original_path = self.config_path
            self.config_path = self.user_config_path
            try:
                self.save()
            except Exception:
                pass  # Don't fail if save doesn't work
            finally:
                self.config_path = original_path
    
    def save(self) -> None:
        """Save configuration to JSON file."""
        # Create parent directories if they don't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)
        
        # Enforce strict permissions (Owner Read/Write only)
        try:
            os.chmod(self.config_path, 0o600)
        except Exception:
            pass  # Fallback if chmod fails on some filesystems
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "version": "2.0.0",
            "urls": {
                "teamviewer": "https://download.teamviewer.com/download/linux/teamviewer_amd64.deb",
                "rise_vision": "https://storage.googleapis.com/install-versions.risevision.com/installer-lnx-64.sh"
            },
            "checksums": {
                "teamviewer": "",
                "rise_vision": ""
            },
            "network": {
                "proxy": "",
                "proxy_user": "",
                "proxy_pass": "",
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 5,
                "bandwidth_limit": 0
            },
            "security": {
                "verify_checksums": True,
                "rate_limit_attempts": 5,
                "rate_limit_window": 300
            },
            "constants": {
                "apt_update_timeout": 300,
                "apt_upgrade_timeout": 1800,
                "snapshot_timeout": 3600,
                "download_timeout": 300,
                "sudo_keepalive_interval": 60
            },
            "paths": {
                "watchdog_script": "~/check_rise.sh",
                "log_path": "~/rise_log.txt",
                "player_dir": "~/rvplayer",
                "player_startup": "~/rvplayer/scripts/start.sh",
                "autostart_dir": "~/.config/autostart",
                "desktop_file": "~/Desktop/SCC_Manager.desktop",
                "error_log": "/tmp/scc_last_error.log"
            },
            "watchdog": {
                "service_name": "rise-vision-player",
                "service_file": "/etc/systemd/system/rise-vision-player.service",
                "use_systemd": True
            },
            "reboot": {
                "timer_name": "scc-reboot",
                "time": "3:00 AM"
            },
            "thermal": {
                "critical_threshold": 85.0,
                "monitoring_enabled": True
            },
            "display": {
                "auto_detect_resolution": True,
                "force_resolution": False
            },
            "timeshift": {
                "auto_snapshot_before_upgrade": True,
                "auto_snapshot_before_fix": True,
                "snapshot_type": "RSYNC",
                "snapshot_location": "/timeshift"
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'urls.teamviewer')."""
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key_path.split('.')
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def expand_path(self, path_key: str) -> str:
        """Expand a path from config with ~ and environment variables."""
        path = self.get(path_key, "")
        return os.path.expanduser(os.path.expandvars(path))

