"""Tests for hardware monitoring module."""
import sys
from unittest.mock import Mock, patch

import pytest
from digital_signage_toolkit.core.hardware_monitor import HardwareMonitor


@pytest.fixture
def hardware_monitor():
    """Create a HardwareMonitor instance."""
    return HardwareMonitor()


class TestCPUTemperature:
    """Test CPU temperature monitoring."""

    @patch('subprocess.run')
    def test_get_cpu_temperature_from_sensors(self, mock_run, hardware_monitor):
        """Test getting CPU temperature from sensors command."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Core 0: +45.0°C\nCPU Temperature: +50.0°C"
        )

        temp = HardwareMonitor.get_cpu_temperature()

        assert temp is not None
        assert isinstance(temp, float)
        assert temp > 0

    @patch('subprocess.run')
    @patch('builtins.open', create=True)
    def test_get_cpu_temperature_from_thermal_zone(self, mock_open, mock_run, hardware_monitor):
        """Test getting CPU temperature from thermal zone file."""
        mock_run.return_value = Mock(returncode=1)  # sensors fails
        mock_open.return_value.__enter__.return_value.read.return_value = "45000"

        temp = HardwareMonitor.get_cpu_temperature()

        # May return None on Windows, but should work on Linux
        if sys.platform != 'win32':
            assert temp is not None

    @patch('subprocess.run')
    def test_get_cpu_temperature_failure(self, mock_run, hardware_monitor):
        """Test getting CPU temperature when all methods fail."""
        mock_run.side_effect = Exception("Test error")

        temp = HardwareMonitor.get_cpu_temperature()

        assert temp is None


class TestThermalCritical:
    """Test thermal critical detection."""

    @patch('psutil.sensors_temperatures', create=True)
    def test_check_thermal_critical_psutil(self, mock_sensors, hardware_monitor):
        """Test thermal critical check using psutil."""
        mock_sensors.return_value = {
            'cpu': [
                Mock(current=90.0, label='CPU')
            ]
        }

        is_critical, max_temp, zone = HardwareMonitor.check_thermal_critical(threshold=85.0)

        assert is_critical is True
        assert max_temp == 90.0
        assert zone is not None

    @patch('psutil.sensors_temperatures', create=True)
    def test_check_thermal_critical_safe(self, mock_sensors, hardware_monitor):
        """Test thermal critical check when temperature is safe."""
        mock_sensors.return_value = {
            'cpu': [
                Mock(current=60.0, label='CPU')
            ]
        }

        is_critical, max_temp, zone = HardwareMonitor.check_thermal_critical(threshold=85.0)

        assert is_critical is False
        assert max_temp == 60.0

    @patch('psutil.sensors_temperatures', create=True)
    @patch.object(HardwareMonitor, 'get_cpu_temperature')
    def test_check_thermal_critical_fallback(self, mock_cpu_temp, mock_sensors, hardware_monitor):
        """Test thermal critical check with fallback to get_cpu_temperature."""
        mock_sensors.side_effect = AttributeError("Not available")
        mock_cpu_temp.return_value = 90.0

        is_critical, max_temp, zone = HardwareMonitor.check_thermal_critical(threshold=85.0)

        assert is_critical is True
        assert max_temp == 90.0

    @pytest.mark.skipif(sys.platform == 'win32', reason="Requires Linux thermal zones")
    @pytest.mark.skipif(sys.platform == 'win32', reason="Requires Linux thermal zones")
    @patch('builtins.open', create=True)
    @patch('pathlib.Path')
    def test_check_thermal_critical_thermal_zones(self, mock_path_class, mock_open, hardware_monitor):
        """Test thermal critical check using thermal zone files."""
        # Mock thermal zone structure
        mock_zone = Mock()
        mock_zone.name = 'thermal_zone0'
        mock_temp_file = Mock()
        mock_temp_file.exists.return_value = True
        # Support Path division operator
        mock_zone.__truediv__ = Mock(return_value=mock_temp_file)

        mock_base = Mock()
        mock_base.exists.return_value = True
        mock_base.glob.return_value = [mock_zone]

        # Mock Path constructor to return our mock for thermal_base
        def path_side_effect(path_str):
            if path_str == '/sys/class/thermal':
                return mock_base
            return Mock(exists=Mock(return_value=False))

        mock_path_class.side_effect = path_side_effect
        mock_open.return_value.__enter__.return_value.read.return_value = "90000"  # 90°C

        is_critical, max_temp, zone = HardwareMonitor.check_thermal_critical(threshold=85.0)

        # Should detect critical temperature (90°C > 85°C threshold)
        assert is_critical is True
        assert max_temp is not None
        assert max_temp > 85.0


class TestThermalZones:
    """Test thermal zone monitoring."""

    @patch('psutil.sensors_temperatures', create=True)
    def test_get_all_thermal_zones_psutil(self, mock_sensors, hardware_monitor):
        """Test getting all thermal zones using psutil."""
        mock_sensors.return_value = {
            'cpu': [
                Mock(current=45.0, label='CPU'),
                Mock(current=50.0, label='GPU')
            ]
        }

        zones = HardwareMonitor.get_all_thermal_zones()

        assert isinstance(zones, dict)
        assert len(zones) > 0

    @pytest.mark.skipif(sys.platform == 'win32', reason="Requires Linux thermal zones")
    @patch('builtins.open', create=True)
    @patch('pathlib.Path')
    def test_get_all_thermal_zones_files(self, mock_path_class, mock_open, hardware_monitor):
        """Test getting thermal zones from files."""
        # Mock thermal zone structure
        mock_zone = Mock()
        mock_zone.name = 'thermal_zone0'
        mock_temp_file = Mock()
        mock_temp_file.exists.return_value = True
        # Support Path division operator properly
        def zone_div(other):
            if str(other) == 'temp':
                return mock_temp_file
            return Mock()
        mock_zone.__truediv__ = Mock(side_effect=zone_div)

        mock_base = Mock()
        mock_base.exists.return_value = True
        mock_base.glob.return_value = [mock_zone]

        # Mock Path constructor to return our mock for thermal_base
        def path_side_effect(path_str):
            if path_str == '/sys/class/thermal':
                return mock_base
            return Mock(exists=Mock(return_value=False))

        mock_path_class.side_effect = path_side_effect
        mock_open.return_value.__enter__.return_value.read.return_value = "45000"

        zones = HardwareMonitor.get_all_thermal_zones()

        assert isinstance(zones, dict)
        assert len(zones) > 0


class TestDiskUsage:
    """Test disk usage monitoring."""

    @patch('psutil.disk_usage')
    def test_get_disk_usage(self, mock_disk, hardware_monitor):
        """Test getting disk usage statistics."""
        mock_disk.return_value = Mock(
            total=100 * (1024**3),  # 100GB
            used=50 * (1024**3),    # 50GB
            free=50 * (1024**3),    # 50GB
            percent=50.0
        )

        usage = HardwareMonitor.get_disk_usage()

        assert usage['total_gb'] == 100.0
        assert usage['used_gb'] == 50.0
        assert usage['free_gb'] == 50.0
        assert usage['percent'] == 50.0

    @patch('psutil.disk_usage')
    def test_get_disk_usage_exception(self, mock_disk, hardware_monitor):
        """Test disk usage when exception occurs."""
        mock_disk.side_effect = Exception("Test error")

        usage = HardwareMonitor.get_disk_usage()

        assert usage['total_gb'] == 0
        assert usage['used_gb'] == 0


class TestMemoryUsage:
    """Test memory usage monitoring."""

    @patch('psutil.virtual_memory')
    def test_get_memory_usage(self, mock_mem, hardware_monitor):
        """Test getting memory usage statistics."""
        mock_mem.return_value = Mock(
            total=8 * (1024**3),      # 8GB
            used=4 * (1024**3),        # 4GB
            available=4 * (1024**3),   # 4GB
            percent=50.0
        )

        usage = HardwareMonitor.get_memory_usage()

        assert usage['total_gb'] == 8.0
        assert usage['used_gb'] == 4.0
        assert usage['available_gb'] == 4.0
        assert usage['percent'] == 50.0

    @patch('psutil.virtual_memory')
    def test_get_memory_usage_exception(self, mock_mem, hardware_monitor):
        """Test memory usage when exception occurs."""
        mock_mem.side_effect = Exception("Test error")

        usage = HardwareMonitor.get_memory_usage()

        assert usage['total_gb'] == 0


class TestCPUUsage:
    """Test CPU usage monitoring."""

    @patch('psutil.cpu_percent')
    def test_get_cpu_usage(self, mock_cpu, hardware_monitor):
        """Test getting CPU usage percentage."""
        mock_cpu.return_value = 75.5

        usage = HardwareMonitor.get_cpu_usage()

        assert usage == 75.5

    @patch('psutil.cpu_percent')
    def test_get_cpu_usage_exception(self, mock_cpu, hardware_monitor):
        """Test CPU usage when exception occurs."""
        mock_cpu.side_effect = Exception("Test error")

        usage = HardwareMonitor.get_cpu_usage()

        assert usage == 0.0


class TestTeamViewerStatus:
    """Test TeamViewer status checking."""

    @patch('subprocess.run')
    def test_check_teamviewer_status_running(self, mock_run, hardware_monitor):
        """Test checking TeamViewer status when running."""
        # The code calls subprocess.run in this order:
        # 1. pgrep -f teamviewer (for running check)
        # 2. teamviewer --info (for online check)
        # 3. which teamviewer (for installed check, at the end)
        mock_run.side_effect = [
            Mock(returncode=0),  # pgrep succeeds (process running)
            Mock(returncode=0, stdout="ID: 12345678"),  # teamviewer --info succeeds
            Mock(returncode=0)  # which teamviewer succeeds
        ]

        status = HardwareMonitor.check_teamviewer_status()

        assert status['installed'] is True
        assert status['running'] is True
        assert status['online'] is True

    @patch('subprocess.run')
    def test_check_teamviewer_status_not_running(self, mock_run, hardware_monitor):
        """Test checking TeamViewer status when not running."""
        mock_run.side_effect = [
            Mock(returncode=1),  # pgrep fails
            Mock(returncode=1)   # teamviewer --info fails
        ]

        status = HardwareMonitor.check_teamviewer_status()

        assert status['running'] is False
        assert status['online'] is False

    @patch('subprocess.run')
    def test_check_teamviewer_status_exception(self, mock_run, hardware_monitor):
        """Test TeamViewer status when exception occurs."""
        mock_run.side_effect = Exception("Test error")

        status = HardwareMonitor.check_teamviewer_status()

        assert status['installed'] is False
        assert status['running'] is False


class TestSystemInfo:
    """Test system information retrieval."""

    @patch('platform.node')
    @patch('platform.system')
    @patch('platform.release')
    @patch('platform.machine')
    @patch('platform.processor')
    def test_get_system_info(self, mock_processor, mock_machine, mock_release,
                             mock_system, mock_node, hardware_monitor):
        """Test getting system information."""
        mock_node.return_value = "test-host"
        mock_system.return_value = "Linux"
        mock_release.return_value = "5.4.0"
        mock_machine.return_value = "x86_64"
        mock_processor.return_value = "Intel"

        info = HardwareMonitor.get_system_info()

        assert info['hostname'] == "test-host"
        assert info['os'] == "Linux"
        assert info['os_version'] == "5.4.0"
        assert info['architecture'] == "x86_64"

    @patch('platform.node')
    def test_get_system_info_exception(self, mock_node, hardware_monitor):
        """Test system info when exception occurs."""
        mock_node.side_effect = Exception("Test error")

        info = HardwareMonitor.get_system_info()

        assert info == {}

