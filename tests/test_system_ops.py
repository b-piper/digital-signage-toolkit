"""Integration tests for system operations."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from digital_signage_toolkit.core.system_ops import SystemOperations
from digital_signage_toolkit.utils.sudo_handler import SudoHandler


@pytest.fixture
def mock_sudo_handler():
    """Create a mock sudo handler that doesn't actually run commands."""
    handler = Mock(spec=SudoHandler)
    handler.run_command = Mock()
    return handler


@pytest.fixture
def system_ops(mock_sudo_handler):
    """Create SystemOperations instance with mocked sudo handler."""
    return SystemOperations(mock_sudo_handler)


class TestHostnameOperations:
    """Test hostname get/set operations."""
    
    def test_get_hostname(self, system_ops):
        """Test getting current hostname."""
        hostname = system_ops.get_hostname()
        assert isinstance(hostname, str)
        assert len(hostname) > 0
    
    def test_set_valid_hostname(self, system_ops, mock_sudo_handler):
        """Test setting a valid hostname."""
        mock_sudo_handler.run_command.return_value = Mock(returncode=0, stderr="")
        
        result = system_ops.set_hostname("test-hostname")
        
        assert result is True
        mock_sudo_handler.run_command.assert_called_once()
        call_args = mock_sudo_handler.run_command.call_args[0][0]
        assert 'hostnamectl' in call_args
        assert 'set-hostname' in call_args
    
    def test_set_invalid_hostname(self, system_ops):
        """Test setting an invalid hostname."""
        result = system_ops.set_hostname("invalid hostname with spaces")
        assert result is False
    
    def test_set_hostname_with_special_chars(self, system_ops):
        """Test setting hostname with special characters."""
        result = system_ops.set_hostname("host@name#invalid")
        assert result is False
    
    def test_set_hostname_failure(self, system_ops, mock_sudo_handler):
        """Test hostname setting failure."""
        mock_sudo_handler.run_command.return_value = Mock(
            returncode=1,
            stderr="Permission denied"
        )
        
        result = system_ops.set_hostname("valid-hostname")
        assert result is False


class TestNetworkOperations:
    """Test network connectivity checks."""
    
    @patch('subprocess.run')
    def test_check_internet_success(self, mock_run, system_ops):
        """Test successful internet check."""
        mock_run.return_value = Mock(returncode=0)
        
        result = system_ops.check_internet()
        assert result is True
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_check_internet_failure(self, mock_run, system_ops):
        """Test failed internet check."""
        mock_run.return_value = Mock(returncode=1)
        
        result = system_ops.check_internet()
        assert result is False
    
    @patch('subprocess.run')
    def test_check_internet_timeout(self, mock_run, system_ops):
        """Test internet check timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('wget', 10)
        
        result = system_ops.check_internet()
        assert result is False


class TestAPTOperations:
    """Test APT package management operations."""
    
    def test_apt_update_success(self, system_ops, mock_sudo_handler):
        """Test successful apt update."""
        mock_sudo_handler.run_command.return_value = Mock(
            returncode=0,
            stdout="Update complete",
            stderr=""
        )
        
        success, output = system_ops.apt_update()
        
        assert success is True
        assert "Update complete" in output
        mock_sudo_handler.run_command.assert_called_once()
    
    def test_apt_update_failure(self, system_ops, mock_sudo_handler):
        """Test failed apt update."""
        mock_sudo_handler.run_command.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Failed to fetch"
        )
        
        success, output = system_ops.apt_update()
        
        assert success is False
        assert "Failed to fetch" in output
    
    def test_apt_update_timeout(self, system_ops, mock_sudo_handler):
        """Test apt update timeout."""
        import subprocess
        mock_sudo_handler.run_command.side_effect = subprocess.TimeoutExpired(
            ['apt-get', 'update'], 300
        )
        
        success, output = system_ops.apt_update()
        
        assert success is False
        assert "timed out" in output.lower()
    
    def test_apt_upgrade_success(self, system_ops, mock_sudo_handler):
        """Test successful apt upgrade."""
        mock_sudo_handler.run_command.return_value = Mock(
            returncode=0,
            stdout="Upgrade complete",
            stderr=""
        )
        
        success, output = system_ops.apt_upgrade()
        
        assert success is True
        assert "Upgrade complete" in output
    
    def test_install_packages(self, system_ops, mock_sudo_handler):
        """Test package installation."""
        mock_sudo_handler.run_command.return_value = Mock(
            returncode=0,
            stdout="Package installed",
            stderr=""
        )
        
        success, output = system_ops.install_packages(['curl', 'wget'])
        
        assert success is True
        mock_sudo_handler.run_command.assert_called_once()
        call_args = mock_sudo_handler.run_command.call_args[0][0]
        assert 'apt-get' in call_args
        assert 'install' in call_args


class TestDisplayOperations:
    """Test display resolution operations."""
    
    @patch('subprocess.run')
    @patch.dict('os.environ', {'XDG_SESSION_TYPE': 'x11'})
    def test_get_display_resolution_x11(self, mock_run, system_ops):
        """Test getting display resolution on X11."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Screen 0: minimum 640 x 480, current 1920 x 1080, maximum 3840 x 2160\n"
                   "   1920x1080     60.00*+  50.00"
        )
        
        resolution = system_ops.get_display_resolution()
        
        assert resolution == "1920x1080"
    
    @patch.dict('os.environ', {'XDG_SESSION_TYPE': 'wayland'})
    def test_get_display_resolution_wayland(self, system_ops):
        """Test getting display resolution on Wayland."""
        # Wayland resolution detection is complex, may return None
        resolution = system_ops.get_display_resolution()
        # Should not crash, may return None
        assert resolution is None or isinstance(resolution, str)
    
    @patch('subprocess.run')
    @patch.dict('os.environ', {'XDG_SESSION_TYPE': 'x11'})
    def test_get_available_resolutions(self, mock_run, system_ops):
        """Test getting available resolutions."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=(
                "Screen 0: minimum 640 x 480, current 1920 x 1080\n"
                "   1920x1080     60.00*+  50.00\n"
                "   1280x720      60.00    50.00\n"
                "   1366x768      60.00"
            )
        )
        
        resolutions = system_ops.get_available_resolutions()
        
        assert isinstance(resolutions, list)
        assert len(resolutions) > 0
        assert "1920x1080" in resolutions
    
    @patch('subprocess.run')
    @patch.dict('os.environ', {'XDG_SESSION_TYPE': 'x11'})
    def test_set_display_resolution_success(self, mock_run, system_ops):
        """Test setting display resolution."""
        # Mock xrandr query
        mock_run.side_effect = [
            Mock(returncode=0, stdout="HDMI-1 connected"),
            Mock(returncode=0, stdout="", stderr="")
        ]
        
        result = system_ops.set_display_resolution("1920x1080")
        
        # Should attempt to set resolution
        assert mock_run.call_count >= 1
    
    def test_set_display_resolution_invalid(self, system_ops):
        """Test setting invalid resolution."""
        result = system_ops.set_display_resolution("invalid")
        assert result is False
    
    def test_set_display_resolution_none(self, system_ops):
        """Test setting None resolution (auto-detect)."""
        import sys
        if sys.platform == 'win32':
            pytest.skip("xrandr not available on Windows")
        with patch.object(system_ops, 'get_display_resolution', return_value="1920x1080"):
            with patch('subprocess.run') as mock_run:
                # Mock subprocess.run to return a result with stdout attribute
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "Screen 0: minimum 320 x 200, current 1920 x 1080, maximum 8192 x 8192\nHDMI-1 connected 1920x1080+0+0"
                mock_result.stderr = ""
                mock_run.return_value = mock_result
                result = system_ops.set_display_resolution(None)
                # Should succeed if current resolution is detected
                assert result is True


class TestRebootOperations:
    """Test system reboot operations."""
    
    @patch('digital_signage_toolkit.core.software_installer.SoftwareInstaller')
    def test_reboot_with_cache_clear(self, mock_installer_class, system_ops, mock_sudo_handler):
        """Test reboot with cache clearing."""
        mock_sudo_handler.run_command.return_value = Mock(returncode=0)
        # Mock the installer instance
        mock_installer = Mock()
        mock_installer.clear_rise_cache = Mock(return_value=True)
        mock_installer_class.return_value = mock_installer
        
        result = system_ops.reboot(clear_cache=True)
        
        # Should attempt reboot
        assert mock_sudo_handler.run_command.called
        # Should attempt cache clearing
        mock_installer.clear_rise_cache.assert_called_once()
    
    def test_reboot_without_cache_clear(self, system_ops, mock_sudo_handler):
        """Test reboot without cache clearing."""
        mock_sudo_handler.run_command.return_value = Mock(returncode=0)
        
        result = system_ops.reboot(clear_cache=False)
        
        assert result is True
        mock_sudo_handler.run_command.assert_called_once()


class TestErrorHandling:
    """Test error handling in system operations."""
    
    def test_operation_with_exception(self, system_ops, mock_sudo_handler):
        """Test that exceptions are properly logged."""
        # check_internet uses subprocess.run directly, not sudo.run_command
        # Mock subprocess.run to raise an exception
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Test error")
            
            # Should not crash, should return False and log error
            result = system_ops.check_internet()
            assert result is False
    
    def test_operation_with_timeout(self, system_ops, mock_sudo_handler):
        """Test timeout handling."""
        import subprocess
        mock_sudo_handler.run_command.side_effect = subprocess.TimeoutExpired(
            ['command'], 10
        )
        
        result = system_ops.apt_update()
        assert result[0] is False  # Should return (False, error_message)




