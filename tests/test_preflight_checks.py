"""Tests for preflight checks module."""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from digital_signage_toolkit.utils.preflight_checks import PreflightChecker


@pytest.fixture
def preflight_checker():
    """Create a PreflightChecker instance."""
    return PreflightChecker()


@pytest.fixture
def mock_sudo_handler():
    """Create a mock sudo handler."""
    handler = Mock()
    handler.check_sudo = Mock(return_value=True)
    return handler


class TestDiskSpaceCheck:
    """Test disk space checking."""
    
    @patch('psutil.disk_usage')
    def test_check_disk_space_sufficient(self, mock_disk, preflight_checker):
        """Test disk space check with sufficient space."""
        mock_disk.return_value = Mock(free=20 * (1024**3))  # 20GB free
        
        result = preflight_checker.check_disk_space(required_gb=5.0)
        
        assert result is True
        assert 'Disk Space' in preflight_checker.results
        assert preflight_checker.results['Disk Space']['passed'] is True
    
    @patch('psutil.disk_usage')
    def test_check_disk_space_low(self, mock_disk, preflight_checker):
        """Test disk space check with low space."""
        mock_disk.return_value = Mock(free=3 * (1024**3))  # 3GB free
        
        result = preflight_checker.check_disk_space(required_gb=5.0)
        
        assert result is False
        assert preflight_checker.results['Disk Space']['passed'] is False
        assert preflight_checker.results['Disk Space']['severity'] == 'error'
    
    @patch('psutil.disk_usage')
    def test_check_disk_space_warning(self, mock_disk, preflight_checker):
        """Test disk space check with warning level."""
        mock_disk.return_value = Mock(free=8 * (1024**3))  # 8GB free (between 5 and 10)
        
        result = preflight_checker.check_disk_space(required_gb=5.0)
        
        assert result is True
        assert preflight_checker.results['Disk Space']['severity'] == 'warning'
    
    @patch('psutil.disk_usage')
    def test_check_disk_space_exception(self, mock_disk, preflight_checker):
        """Test disk space check when exception occurs."""
        mock_disk.side_effect = Exception("Test error")
        
        result = preflight_checker.check_disk_space()
        
        # Should not block on error
        assert result is True
        assert preflight_checker.results['Disk Space']['severity'] == 'warning'


class TestInternetCheck:
    """Test internet connectivity checking."""
    
    @patch('subprocess.run')
    def test_check_internet_success(self, mock_run, preflight_checker):
        """Test internet check when connection is available."""
        mock_run.return_value = Mock(returncode=0)
        
        result = preflight_checker.check_internet()
        
        assert result is True
        assert preflight_checker.results['Internet Connectivity']['passed'] is True
    
    @patch('subprocess.run')
    def test_check_internet_failure(self, mock_run, preflight_checker):
        """Test internet check when connection is unavailable."""
        mock_run.return_value = Mock(returncode=1)
        
        result = preflight_checker.check_internet()
        
        assert result is False
        assert preflight_checker.results['Internet Connectivity']['passed'] is False
    
    @patch('subprocess.run')
    def test_check_internet_exception(self, mock_run, preflight_checker):
        """Test internet check when subprocess raises exception."""
        mock_run.side_effect = Exception("Test error")
        
        result = preflight_checker.check_internet()
        
        assert result is False
        assert preflight_checker.results['Internet Connectivity']['passed'] is False


class TestPythonVersionCheck:
    """Test Python version checking."""
    
    def test_check_python_version_sufficient(self, preflight_checker):
        """Test Python version check with sufficient version."""
        result = preflight_checker.check_python_version(min_version=(3, 8))
        
        # Should pass if Python 3.8+
        assert result is True
        assert preflight_checker.results['Python Version']['passed'] is True
    
    @patch('sys.version_info')
    def test_check_python_version_insufficient(self, mock_version, preflight_checker):
        """Test Python version check with insufficient version."""
        mock_version.__getitem__ = Mock(return_value=(3, 6))
        
        result = preflight_checker.check_python_version(min_version=(3, 8))
        
        assert result is False
        assert preflight_checker.results['Python Version']['passed'] is False
        assert preflight_checker.results['Python Version']['severity'] == 'error'


class TestRequiredCommandsCheck:
    """Test required commands checking."""
    
    @patch('shutil.which')
    def test_check_required_commands_all_present(self, mock_which, preflight_checker):
        """Test when all required commands are present."""
        mock_which.return_value = '/usr/bin/command'
        
        result = preflight_checker.check_required_commands(['wget', 'curl', 'apt-get'])
        
        assert result is True
        assert preflight_checker.results['Required Commands']['passed'] is True
    
    @patch('shutil.which')
    def test_check_required_commands_missing(self, mock_which, preflight_checker):
        """Test when some required commands are missing."""
        def which_side_effect(cmd):
            return '/usr/bin/wget' if cmd == 'wget' else None
        mock_which.side_effect = which_side_effect
        
        result = preflight_checker.check_required_commands(['wget', 'curl', 'apt-get'])
        
        assert result is False
        assert preflight_checker.results['Required Commands']['passed'] is False
        assert 'Missing commands' in preflight_checker.results['Required Commands']['message']


class TestSudoAccessCheck:
    """Test sudo access checking."""
    
    @patch('subprocess.run')
    def test_check_sudo_access_available(self, mock_run, preflight_checker):
        """Test sudo check when access is available."""
        mock_run.return_value = Mock(returncode=0)
        
        result = preflight_checker.check_sudo_access()
        
        assert result is True
        assert preflight_checker.results['Sudo Access']['passed'] is True
    
    @patch('subprocess.run')
    def test_check_sudo_access_unavailable(self, mock_run, preflight_checker):
        """Test sudo check when access is unavailable."""
        mock_run.return_value = Mock(returncode=1)
        
        result = preflight_checker.check_sudo_access()
        
        assert result is True  # Should not block
        assert preflight_checker.results['Sudo Access']['severity'] == 'warning'
    
    def test_check_sudo_access_with_handler(self, mock_sudo_handler):
        """Test sudo check using injected sudo handler."""
        checker = PreflightChecker(sudo_handler=mock_sudo_handler)
        
        result = checker.check_sudo_access()
        
        assert result is True
        mock_sudo_handler.check_sudo.assert_called_once()
    
    @patch('subprocess.run')
    def test_check_sudo_access_exception(self, mock_run, preflight_checker):
        """Test sudo check when exception occurs."""
        mock_run.side_effect = Exception("Test error")
        
        result = preflight_checker.check_sudo_access()
        
        assert result is True  # Should not block
        assert preflight_checker.results['Sudo Access']['severity'] == 'warning'


class TestSystemResourcesCheck:
    """Test system resources checking."""
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_check_system_resources_ok(self, mock_cpu, mock_mem, preflight_checker):
        """Test system resources check with adequate resources."""
        mock_mem.return_value = Mock(total=4 * (1024**3))  # 4GB RAM
        mock_cpu.return_value = 50.0  # 50% CPU
        
        result = preflight_checker.check_system_resources()
        
        assert result is True
        assert preflight_checker.results['System Resources']['passed'] is True
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_check_system_resources_low_memory(self, mock_cpu, mock_mem, preflight_checker):
        """Test system resources check with low memory."""
        mock_mem.return_value = Mock(total=1 * (1024**3))  # 1GB RAM
        mock_cpu.return_value = 50.0
        
        result = preflight_checker.check_system_resources()
        
        assert result is True  # Should not block
        assert preflight_checker.results['System Resources']['severity'] == 'warning'
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_check_system_resources_high_cpu(self, mock_cpu, mock_mem, preflight_checker):
        """Test system resources check with high CPU."""
        mock_mem.return_value = Mock(total=4 * (1024**3))
        mock_cpu.return_value = 95.0  # 95% CPU
        
        result = preflight_checker.check_system_resources()
        
        assert result is True
        assert preflight_checker.results['System Resources']['severity'] == 'warning'
    
    @patch('psutil.virtual_memory')
    def test_check_system_resources_exception(self, mock_mem, preflight_checker):
        """Test system resources check when exception occurs."""
        mock_mem.side_effect = Exception("Test error")
        
        result = preflight_checker.check_system_resources()
        
        assert result is True  # Should not block
        assert preflight_checker.results['System Resources']['severity'] == 'warning'


class TestRunAllChecks:
    """Test running all preflight checks."""
    
    @patch.object(PreflightChecker, 'check_disk_space')
    @patch.object(PreflightChecker, 'check_python_version')
    @patch.object(PreflightChecker, 'check_internet')
    @patch.object(PreflightChecker, 'check_required_commands')
    @patch.object(PreflightChecker, 'check_sudo_access')
    @patch.object(PreflightChecker, 'check_system_resources')
    def test_run_all_checks(self, mock_resources, mock_sudo, mock_commands,
                           mock_internet, mock_python, mock_disk, preflight_checker):
        """Test running all checks."""
        # Mock methods to call _record to populate results
        def mock_check_with_record(check_name):
            def wrapper(*args, **kwargs):
                preflight_checker._record(check_name, True, f"{check_name} check passed", "info")
                return True
            return wrapper
        
        mock_disk.side_effect = mock_check_with_record("Disk Space")
        mock_python.side_effect = mock_check_with_record("Python Version")
        mock_internet.side_effect = mock_check_with_record("Internet Connectivity")
        mock_commands.side_effect = mock_check_with_record("Required Commands")
        mock_sudo.side_effect = mock_check_with_record("Sudo Access")
        mock_resources.side_effect = mock_check_with_record("System Resources")
        
        results = preflight_checker.run_all_checks()
        
        assert isinstance(results, dict)
        assert 'Disk Space' in results
        assert 'Python Version' in results
        assert 'Internet Connectivity' in results
        assert 'Required Commands' in results
        assert 'Sudo Access' in results
        assert 'System Resources' in results
        
        # Verify all checks were called
        mock_disk.assert_called_once()
        mock_python.assert_called_once()
        mock_internet.assert_called_once()
        mock_commands.assert_called_once()
        mock_sudo.assert_called_once()
        mock_resources.assert_called_once()

