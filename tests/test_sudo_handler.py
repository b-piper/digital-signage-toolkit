"""Tests for sudo handler module."""
import pytest
import subprocess
import time
from unittest.mock import Mock, patch, MagicMock
from digital_signage_toolkit.utils.sudo_handler import SudoHandler


@pytest.fixture
def sudo_handler():
    """Create a SudoHandler instance."""
    return SudoHandler()


class TestSudoCheck:
    """Test sudo access checking."""
    
    @patch('subprocess.run')
    def test_check_sudo_available(self, mock_run, sudo_handler):
        """Test checking sudo when available."""
        mock_run.return_value = Mock(returncode=0)
        
        result = sudo_handler.check_sudo()
        
        assert result is True
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_check_sudo_unavailable(self, mock_run, sudo_handler):
        """Test checking sudo when unavailable."""
        mock_run.return_value = Mock(returncode=1)
        
        result = sudo_handler.check_sudo()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_check_sudo_exception(self, mock_run, sudo_handler):
        """Test checking sudo when subprocess raises exception."""
        mock_run.side_effect = Exception("Test error")
        
        result = sudo_handler.check_sudo()
        
        assert result is False


class TestSudoRequest:
    """Test sudo password requests."""
    
    @patch('subprocess.run')
    def test_request_sudo_success(self, mock_run, sudo_handler):
        """Test successful sudo request."""
        mock_run.return_value = Mock(returncode=0)
        
        with patch.object(sudo_handler, 'start_keep_alive'):
            result = sudo_handler.request_sudo()
        
        assert result is True
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_request_sudo_failure(self, mock_run, sudo_handler):
        """Test failed sudo request."""
        mock_run.return_value = Mock(returncode=1)
        
        result = sudo_handler.request_sudo()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_request_sudo_exception(self, mock_run, sudo_handler):
        """Test sudo request when subprocess raises exception."""
        mock_run.side_effect = Exception("Test error")
        
        result = sudo_handler.request_sudo()
        
        assert result is False


class TestSudoWithPassword:
    """Test sudo authentication with password."""
    
    @patch('subprocess.run')
    def test_request_sudo_with_password_success(self, mock_run, sudo_handler):
        """Test successful password authentication."""
        mock_run.return_value = Mock(returncode=0)
        
        with patch.object(sudo_handler, 'start_keep_alive'):
            with patch.object(sudo_handler, '_secure_clear_password'):
                result = sudo_handler.request_sudo_with_password('testpass')
        
        assert result is True
        mock_run.assert_called_once()
        # Check that password was passed via stdin
        call_args = mock_run.call_args
        assert 'input' in call_args.kwargs
    
    @patch('subprocess.run')
    def test_request_sudo_with_password_failure(self, mock_run, sudo_handler):
        """Test failed password authentication."""
        mock_run.return_value = Mock(returncode=1)
        
        with patch.object(sudo_handler, '_secure_clear_password'):
            result = sudo_handler.request_sudo_with_password('wrongpass')
        
        assert result is False
        assert sudo_handler._failed_attempts == 1
    
    @patch('subprocess.run')
    def test_request_sudo_rate_limiting(self, mock_run, sudo_handler):
        """Test rate limiting after multiple failed attempts."""
        mock_run.return_value = Mock(returncode=1)
        sudo_handler._failed_attempts = 5
        sudo_handler._last_attempt_time = time.time() - 10  # Recent attempt
        
        with patch.object(sudo_handler, '_secure_clear_password'):
            result = sudo_handler.request_sudo_with_password('wrongpass')
        
        assert result is False
    
    @patch('subprocess.run')
    def test_request_sudo_rate_limit_reset(self, mock_run, sudo_handler):
        """Test that rate limit resets after window."""
        mock_run.return_value = Mock(returncode=1)
        sudo_handler._failed_attempts = 5
        sudo_handler._last_attempt_time = time.time() - 400  # Old attempt (outside window)
        
        with patch.object(sudo_handler, '_secure_clear_password'):
            result = sudo_handler.request_sudo_with_password('wrongpass')
        
        # Rate limit should reset, then increment to 1
        assert sudo_handler._failed_attempts == 1  # Reset then incremented
    
    @patch('subprocess.run')
    def test_request_sudo_exception(self, mock_run, sudo_handler):
        """Test password authentication when subprocess raises exception."""
        mock_run.side_effect = Exception("Test error")
        
        with patch.object(sudo_handler, '_secure_clear_password'):
            result = sudo_handler.request_sudo_with_password('testpass')
        
        assert result is False


class TestSudoKeepAlive:
    """Test sudo keep-alive functionality."""
    
    def test_start_keep_alive(self, sudo_handler):
        """Test starting keep-alive thread."""
        sudo_handler.start_keep_alive()
        
        assert sudo_handler._keep_alive_thread is not None
        assert sudo_handler._keep_alive_thread.is_alive()
        
        # Cleanup
        sudo_handler.stop_keep_alive()
    
    def test_start_keep_alive_idempotent(self, sudo_handler):
        """Test that starting keep-alive multiple times doesn't create multiple threads."""
        sudo_handler.start_keep_alive()
        thread1 = sudo_handler._keep_alive_thread
        
        sudo_handler.start_keep_alive()
        thread2 = sudo_handler._keep_alive_thread
        
        assert thread1 is thread2
        
        # Cleanup
        sudo_handler.stop_keep_alive()
    
    def test_stop_keep_alive(self, sudo_handler):
        """Test stopping keep-alive thread."""
        sudo_handler.start_keep_alive()
        sudo_handler.stop_keep_alive()
        
        # Thread should be stopped (may take a moment)
        time.sleep(0.1)
        assert not sudo_handler._keep_alive_thread.is_alive() if sudo_handler._keep_alive_thread else True


class TestSudoRunCommand:
    """Test running commands with sudo."""
    
    @patch('subprocess.run')
    def test_run_command_success(self, mock_run, sudo_handler):
        """Test successful command execution."""
        mock_run.return_value = Mock(returncode=0, stdout="output", stderr="")
        
        result = sudo_handler.run_command(['ls', '/tmp'])
        
        assert result.returncode == 0
        mock_run.assert_called_once()
        # Check that sudo was prepended
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == 'sudo'
    
    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run, sudo_handler):
        """Test failed command execution."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="error")
        
        result = sudo_handler.run_command(['ls', '/nonexistent'])
        
        assert result.returncode == 1
    
    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_run, sudo_handler):
        """Test command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('sudo', 5)
        
        with pytest.raises(subprocess.TimeoutExpired):
            sudo_handler.run_command(['sleep', '10'], timeout=5)
    
    @patch('subprocess.run')
    def test_run_command_with_env(self, mock_run, sudo_handler):
        """Test running command with custom environment."""
        mock_run.return_value = Mock(returncode=0)
        test_env = {'TEST_VAR': 'test_value'}
        
        sudo_handler.run_command(['echo', 'test'], env=test_env)
        
        call_args = mock_run.call_args
        assert call_args.kwargs['env'] == test_env
    
    def test_sanitize_command_for_logging(self, sudo_handler):
        """Test command sanitization for logging."""
        # Test normal command
        cmd = ['ls', '-la', '/tmp']
        sanitized = sudo_handler._sanitize_command_for_logging(cmd)
        assert 'ls' in sanitized
        assert '****' not in sanitized
        
        # Test command with password-like arguments
        cmd = ['command', '--password', 'secret123']
        sanitized = sudo_handler._sanitize_command_for_logging(cmd)
        assert '****' in sanitized
        assert 'secret123' not in sanitized


class TestSudoAsyncCommand:
    """Test asynchronous command execution."""
    
    @patch('subprocess.Popen')
    def test_run_command_async(self, mock_popen, sudo_handler):
        """Test running command asynchronously."""
        mock_process = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        process = sudo_handler.run_command_async(['ls', '/tmp'])
        
        assert process is not None
        mock_popen.assert_called_once()
    
    @patch('subprocess.Popen')
    def test_run_command_async_with_callback(self, mock_popen, sudo_handler):
        """Test async command with log callback."""
        mock_process = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        log_callback = Mock()
        process = sudo_handler.run_command_async(
            ['ls', '/tmp'],
            log_callback=log_callback
        )
        
        assert process is not None
        # Give thread time to start
        time.sleep(0.1)

