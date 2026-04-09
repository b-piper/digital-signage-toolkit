"""Tests for sudo handler module."""
import subprocess
import time
from unittest.mock import Mock, patch

import pytest
from digital_signage_toolkit.utils.sudo_handler import SudoHandler


@pytest.fixture
def sudo_handler():
    """Create a SudoHandler instance."""
    return SudoHandler()


class TestSudoRunCommand:
    """Test running commands with SudoHandler."""

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run, sudo_handler):
        """Test successful command execution."""
        mock_run.return_value = Mock(returncode=0, stdout="output", stderr="")

        result = sudo_handler.run_command(['ls', '/tmp'])

        assert result.returncode == 0
        mock_run.assert_called_once()
        # Ensure it doesn't try to append 'sudo' as it now assumes pkexec usage or runs directly
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == 'ls'

    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run, sudo_handler):
        """Test failed command execution."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="error")

        result = sudo_handler.run_command(['ls', '/nonexistent'])

        assert result.returncode == 1

    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_run, sudo_handler):
        """Test command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('ls', 5)

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
