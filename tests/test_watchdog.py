"""Tests for watchdog management module."""
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from digital_signage_toolkit.core.watchdog import WatchdogManager
from digital_signage_toolkit.utils.config import Config
from digital_signage_toolkit.utils.sudo_handler import SudoHandler


@pytest.fixture
def mock_sudo_handler():
    """Create a mock sudo handler."""
    handler = Mock(spec=SudoHandler)
    handler.run_command = Mock(return_value=Mock(returncode=0, stdout="", stderr=""))
    return handler


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.get = Mock(side_effect=lambda key, default=None: {
        'watchdog.service_name': 'rise-vision-player',
        'watchdog.service_file': '/etc/systemd/system/rise-vision-player.service',
        'paths.log_path': '~/rise_log.txt',
        'paths.player_startup': '~/rvplayer/scripts/start.sh'
    }.get(key, default))
    config.expand_path = Mock(side_effect=lambda x: str(Path.home() / x.replace('~/', '')))
    return config


@pytest.fixture
def temp_player_script():
    """Create a temporary player startup script."""
    temp_dir = Path(tempfile.mkdtemp())
    script_path = temp_dir / "rvplayer" / "scripts" / "start.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("#!/bin/bash\necho 'Player started'")
    script_path.chmod(0o755)
    yield script_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def watchdog_manager(mock_sudo_handler, mock_config, temp_player_script):
    """Create a WatchdogManager instance with mocked dependencies."""
    # Update config to use temp script
    mock_config.expand_path = Mock(return_value=str(temp_player_script))
    manager = WatchdogManager(mock_sudo_handler, mock_config)
    return manager


class TestServiceStatus:
    """Test service status checking."""

    def test_is_enabled_service_exists_and_active(self, watchdog_manager, mock_sudo_handler):
        """Test checking if service is enabled when it exists and is active."""
        # Mock service file exists
        with patch('pathlib.Path.exists', return_value=True):
            mock_sudo_handler.run_command.return_value = Mock(returncode=0, stdout="enabled\nactive")

            result = watchdog_manager.is_enabled()

            assert result is True
            assert mock_sudo_handler.run_command.call_count == 2

    def test_is_enabled_service_not_exists(self, watchdog_manager):
        """Test checking if service is enabled when service file doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            result = watchdog_manager.is_enabled()

            assert result is False

    def test_is_enabled_service_not_active(self, watchdog_manager, mock_sudo_handler):
        """Test checking if service is enabled when service is not active."""
        with patch('pathlib.Path.exists', return_value=True):
            # First call (is-enabled) succeeds, second (is-active) fails
            mock_sudo_handler.run_command.side_effect = [
                Mock(returncode=0, stdout="enabled"),
                Mock(returncode=1, stdout="inactive")
            ]

            result = watchdog_manager.is_enabled()

            assert result is False

    def test_get_service_status(self, watchdog_manager, mock_sudo_handler):
        """Test getting service status information."""
        mock_sudo_handler.run_command.side_effect = [
            Mock(returncode=0, stdout="ActiveState=active\nUnitFileState=enabled"),
            Mock(returncode=0, stdout="Service status output")
        ]

        status = watchdog_manager.get_service_status()

        assert status['active'] is True
        assert status['enabled'] is True
        assert 'status_output' in status

    def test_get_service_status_failure(self, watchdog_manager, mock_sudo_handler):
        """Test getting service status when command fails."""
        mock_sudo_handler.run_command.return_value = Mock(returncode=1, stdout="")

        status = watchdog_manager.get_service_status()

        assert status['active'] is False
        assert status['enabled'] is False


class TestServiceCreation:
    """Test systemd service creation."""

    def test_create_systemd_service_success(self, watchdog_manager, mock_sudo_handler, temp_player_script):
        """Test successful systemd service creation."""
        mock_sudo_handler.run_command.side_effect = [
            Mock(returncode=0),  # cp command
            Mock(returncode=0)   # daemon-reload
        ]

        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_file = MagicMock()
            mock_file.name = '/tmp/test.service'
            mock_temp.return_value.__enter__.return_value = mock_file
            mock_temp.return_value.__exit__.return_value = None

            result = watchdog_manager.create_systemd_service()

            assert result is True
            assert mock_sudo_handler.run_command.call_count >= 2

    def test_create_systemd_service_invalid_path(self, watchdog_manager):
        """Test service creation with invalid player path."""
        # Mock invalid path validation
        with patch.object(watchdog_manager, '_validate_player_startup_path', return_value=(False, None)):
            result = watchdog_manager.create_systemd_service()

            assert result is False

    def test_create_systemd_service_copy_failure(self, watchdog_manager, mock_sudo_handler, temp_player_script):
        """Test service creation when file copy fails."""
        mock_sudo_handler.run_command.return_value = Mock(returncode=1, stderr="Permission denied")

        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_file = MagicMock()
            mock_file.name = '/tmp/test.service'
            mock_temp.return_value.__enter__.return_value = mock_file
            mock_temp.return_value.__exit__.return_value = None

            result = watchdog_manager.create_systemd_service()

            assert result is False


class TestServiceEnableDisable:
    """Test enabling and disabling services."""

    def test_enable_service_success(self, watchdog_manager, mock_sudo_handler):
        """Test successfully enabling service."""
        with patch('pathlib.Path.exists', return_value=True):
            mock_sudo_handler.run_command.side_effect = [
                Mock(returncode=0),  # enable
                Mock(returncode=0)   # start
            ]

            result = watchdog_manager.enable()

            assert result is True
            assert mock_sudo_handler.run_command.call_count == 2

    def test_enable_service_creates_if_missing(self, watchdog_manager, mock_sudo_handler):
        """Test that enable creates service file if it doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            with patch.object(watchdog_manager, 'create_systemd_service', return_value=True):
                mock_sudo_handler.run_command.side_effect = [
                    Mock(returncode=0),  # enable
                    Mock(returncode=0)   # start
                ]

                result = watchdog_manager.enable()

                assert result is True

    def test_disable_service_success(self, watchdog_manager, mock_sudo_handler):
        """Test successfully disabling service."""
        with patch.object(watchdog_manager, 'is_enabled', return_value=True):
            mock_sudo_handler.run_command.side_effect = [
                Mock(returncode=0),  # stop
                Mock(returncode=0)   # disable
            ]

            result = watchdog_manager.disable()

            assert result is True

    def test_disable_service_not_running(self, watchdog_manager, mock_sudo_handler):
        """Test disabling service that's not running."""
        with patch.object(watchdog_manager, 'is_enabled', return_value=False):
            mock_sudo_handler.run_command.return_value = Mock(returncode=0)

            result = watchdog_manager.disable()

            assert result is True


class TestPathValidation:
    """Test player startup path validation."""

    def test_validate_player_startup_path_success(self, watchdog_manager, temp_player_script):
        """Test successful path validation."""
        watchdog_manager.player_startup = str(temp_player_script)

        is_valid, path = watchdog_manager._validate_player_startup_path()

        assert is_valid is True
        assert path is not None
        assert path.exists()

    def test_validate_player_startup_path_nonexistent(self, watchdog_manager):
        """Test path validation with nonexistent file."""
        watchdog_manager.player_startup = '/nonexistent/path/script.sh'

        is_valid, path = watchdog_manager._validate_player_startup_path()

        assert is_valid is False
        assert path is None

    def test_validate_player_startup_path_invalid_chars(self, watchdog_manager):
        """Test path validation with invalid characters."""
        watchdog_manager.player_startup = '/path/with;invalid&chars.sh'

        is_valid, path = watchdog_manager._validate_player_startup_path()

        assert is_valid is False


class TestCacheCleanupScript:
    """Test cache cleanup script generation."""

    def test_generate_cache_cleanup_script_success(self, watchdog_manager, temp_player_script):
        """Test successful cache cleanup script generation."""
        watchdog_manager.player_startup = str(temp_player_script)

        script = watchdog_manager._generate_cache_cleanup_script()

        assert script is not None
        assert 'SoftwareInstaller' in script
        assert 'clear_rise_cache' in script

    def test_generate_cache_cleanup_script_invalid_path(self, watchdog_manager):
        """Test script generation with invalid path."""
        watchdog_manager.player_startup = '/nonexistent/path'

        script = watchdog_manager._generate_cache_cleanup_script()

        assert script is None


class TestStopPlayer:
    """Test stopping the player."""

    def test_stop_player(self, watchdog_manager, mock_sudo_handler):
        """Test stopping the player process."""
        mock_sudo_handler.run_command.return_value = Mock(returncode=0)

        result = watchdog_manager.stop_player()

        assert result is True
        mock_sudo_handler.run_command.assert_called_once()
        # Check that pkill command was used
        call_args = mock_sudo_handler.run_command.call_args[0][0]
        assert 'pkill' in call_args


class TestRebootSchedule:
    """Test reboot schedule configuration."""

    @pytest.mark.skipif(sys.platform == 'win32', reason="Requires Linux systemd")
    def test_configure_reboot_schedule(self, watchdog_manager, mock_sudo_handler):
        """Test configuring reboot schedule."""
        mock_sudo_handler.run_command.return_value = Mock(returncode=0)

        watchdog_manager.configure_reboot_schedule(hour=3, minute=0)

        # Should create systemd timer
        assert mock_sudo_handler.run_command.called

    def test_configure_reboot_schedule_invalid_time(self, watchdog_manager):
        """Test reboot schedule with invalid time values."""
        result = watchdog_manager.configure_reboot_schedule(hour=25, minute=0)

        assert result is False

        result = watchdog_manager.configure_reboot_schedule(hour=3, minute=70)

        assert result is False

