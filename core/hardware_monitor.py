"""Hardware health monitoring module."""
import subprocess
from pathlib import Path
from typing import Dict, Optional

import psutil
from digital_signage_toolkit.utils.logger import get_logger


class HardwareMonitor:
    """Monitors hardware health metrics."""

    def __init__(self):
        self.logger = get_logger()

    @staticmethod
    def get_cpu_temperature() -> Optional[float]:
        """Get CPU temperature in Celsius."""
        try:
            # Try different methods to get CPU temp
            # Method 1: sensors command
            result = subprocess.run(
                ['sensors'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Core 0' in line or 'CPU Temperature' in line or 'Tdie' in line:
                        # Extract temperature value
                        parts = line.split()
                        for part in parts:
                            if '°C' in part or '+' in part:
                                temp_str = part.replace('°C', '').replace('+', '').replace('(', '').replace(')', '')
                                try:
                                    return float(temp_str)
                                except ValueError:
                                    continue

            # Method 2: thermal_zone files
            try:
                with open('/sys/class/thermal/thermal_zone0/temp') as f:
                    temp_millidegrees = int(f.read().strip())
                    return temp_millidegrees / 1000.0
            except Exception:
                pass

            return None
        except Exception:
            return None

    @staticmethod
    def check_thermal_critical(threshold: float = 85.0) -> tuple[bool, Optional[float], Optional[str]]:
        """Check if any thermal zone exceeds critical threshold.
        
        Args:
            threshold: Critical temperature threshold in Celsius (default: 85.0)
            
        Returns:
            Tuple of (is_critical, max_temp, zone_name)
        """
        max_temp = 0.0
        max_zone = None

        try:
            # Method 1: psutil.sensors_temperatures() (if available)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            if entry.current and entry.current > max_temp:
                                max_temp = entry.current
                                max_zone = f"{name}/{entry.label or 'default'}"
            except (AttributeError, NotImplementedError, Exception):
                # psutil.sensors_temperatures() not available or failed
                pass

            # Method 2: Fallback to existing get_cpu_temperature() method
            if max_temp == 0.0:
                cpu_temp = HardwareMonitor.get_cpu_temperature()
                if cpu_temp:
                    max_temp = cpu_temp
                    max_zone = "CPU/thermal_zone0"

            # Method 3: Check all thermal zones directly
            if max_temp == 0.0:
                try:
                    thermal_base = Path('/sys/class/thermal')
                    if thermal_base.exists():
                        for thermal_zone in thermal_base.glob('thermal_zone*'):
                            temp_file = thermal_zone / 'temp'
                            if temp_file.exists():
                                try:
                                    with open(temp_file) as f:
                                        temp_millidegrees = int(f.read().strip())
                                        temp_celsius = temp_millidegrees / 1000.0
                                        if temp_celsius > max_temp:
                                            max_temp = temp_celsius
                                            max_zone = thermal_zone.name
                                except Exception:
                                    continue
                except Exception:
                    pass

            # Check if critical
            is_critical = max_temp > threshold if max_temp > 0 else False
            return (is_critical, max_temp if max_temp > 0 else None, max_zone)

        except Exception:
            return (False, None, None)

    @staticmethod
    def get_all_thermal_zones() -> dict[str, float]:
        """Get temperatures from all thermal zones.
        
        Returns:
            Dictionary mapping zone names to temperatures in Celsius
        """
        zones = {}

        try:
            # Try psutil first
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            zone_name = f"{name}/{entry.label or 'default'}"
                            if entry.current:
                                zones[zone_name] = entry.current
            except (AttributeError, NotImplementedError):
                pass

            # Fallback: Read thermal zone files directly
            thermal_base = Path('/sys/class/thermal')
            if thermal_base.exists():
                for thermal_zone in thermal_base.glob('thermal_zone*'):
                    temp_file = thermal_zone / 'temp'
                    if temp_file.exists():
                        try:
                            with open(temp_file) as f:
                                temp_millidegrees = int(f.read().strip())
                                zones[thermal_zone.name] = temp_millidegrees / 1000.0
                        except Exception:
                            continue

            return zones
        except Exception:
            return {}

    @staticmethod
    def get_disk_usage() -> Dict[str, float]:
        """Get disk usage statistics."""
        try:
            disk = psutil.disk_usage('/')
            return {
                'total_gb': disk.total / (1024**3),
                'used_gb': disk.used / (1024**3),
                'free_gb': disk.free / (1024**3),
                'percent': disk.percent
            }
        except Exception:
            return {'total_gb': 0, 'used_gb': 0, 'free_gb': 0, 'percent': 0}

    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get memory usage statistics."""
        try:
            mem = psutil.virtual_memory()
            return {
                'total_gb': mem.total / (1024**3),
                'used_gb': mem.used / (1024**3),
                'available_gb': mem.available / (1024**3),
                'percent': mem.percent
            }
        except Exception:
            return {'total_gb': 0, 'used_gb': 0, 'available_gb': 0, 'percent': 0}

    @staticmethod
    def get_cpu_usage() -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=1)
        except Exception:
            return 0.0

    @staticmethod
    def check_teamviewer_status() -> Dict[str, bool]:
        """Check TeamViewer connectivity status."""
        try:
            # Check if TeamViewer is running
            result = subprocess.run(
                ['pgrep', '-f', 'teamviewer'],
                capture_output=True,
                timeout=5
            )
            is_running = result.returncode == 0

            # Try to get TeamViewer ID (requires teamviewer command)
            is_online = False
            try:
                result = subprocess.run(
                    ['teamviewer', '--info'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and 'ID' in result.stdout:
                    is_online = True
            except Exception:
                pass

            return {
                'installed': subprocess.run(['which', 'teamviewer'], capture_output=True).returncode == 0,
                'running': is_running,
                'online': is_online
            }
        except Exception:
            return {'installed': False, 'running': False, 'online': False}

    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """Get basic system information."""
        try:
            import platform
            return {
                'hostname': platform.node(),
                'os': platform.system(),
                'os_version': platform.release(),
                'architecture': platform.machine(),
                'processor': platform.processor()
            }
        except Exception:
            return {}

