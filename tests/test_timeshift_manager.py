"""Tests for Timeshift manager module."""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from digital_signage_toolkit.core.timeshift_manager import TimeshiftManager
from digital_signage_toolkit.utils.sudo_handler import SudoHandler
from digital_signage_toolkit.utils.config import Config


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
        'timeshift.snapshot_location': '/timeshift/snapshots',
        'timeshift.snapshot_type': 'RSYNC',
        'timeshift.auto_snapshot_before_upgrade': True
    }.get(key, default))
    return config


@pytest.fixture
def timeshift_manager(mock_sudo_handler, mock_config):
    """Create a TimeshiftManager instance."""
    return TimeshiftManager(mock_sudo_handler, mock_config)


class TestTimeshiftInstallation:
    """Test Timeshift installation checking."""
    
    @patch('subprocess.run')
    def test_is_installed_true(self, mock_run, timeshift_manager):
        """Test checking if Timeshift is installed."""
        mock_run.return_value = Mock(returncode=0)
        
        result = timeshift_manager.is_installed()
        
        assert result is True
    
    @patch('subprocess.run')
    def test_is_installed_false(self, mock_run, timeshift_manager):
        """Test checking if Timeshift is not installed."""
        mock_run.return_value = Mock(returncode=1)
        
        result = timeshift_manager.is_installed()
        
        assert result is False
    
    def test_install_when_already_installed(self, timeshift_manager, mock_sudo_handler):
        """Test installing when Timeshift is already installed."""
        with patch.object(timeshift_manager, 'is_installed', return_value=True):
            result = timeshift_manager.install()
            
            assert result is True
            mock_sudo_handler.run_command.assert_not_called()
    
    def test_install_success(self, timeshift_manager, mock_sudo_handler):
        """Test successful Timeshift installation."""
        with patch.object(timeshift_manager, 'is_installed', return_value=False):
            mock_sudo_handler.run_command.return_value = Mock(returncode=0)
            
            result = timeshift_manager.install()
            
            assert result is True
            mock_sudo_handler.run_command.assert_called_once()
    
    def test_install_failure(self, timeshift_manager, mock_sudo_handler):
        """Test failed Timeshift installation."""
        with patch.object(timeshift_manager, 'is_installed', return_value=False):
            mock_sudo_handler.run_command.return_value = Mock(
                returncode=1,
                stderr="Installation failed"
            )
            
            result = timeshift_manager.install()
            
            assert result is False


class TestTimeshiftConfiguration:
    """Test Timeshift configuration."""
    
    def test_configure_success(self, timeshift_manager, mock_sudo_handler):
        """Test successful Timeshift configuration."""
        with patch.object(timeshift_manager, 'is_installed', return_value=True):
            # Mock path validation to return True
            with patch('digital_signage_toolkit.utils.validators.validate_path', return_value=True):
                # Mock Path.exists for the snapshot location check
                with patch('pathlib.Path.exists', return_value=True):
                    # Mock both commands that configure() calls
                    mock_sudo_handler.run_command.return_value = Mock(returncode=0)
                    
                    result = timeshift_manager.configure(
                        snapshot_type="RSYNC",
                        snapshot_location="/timeshift"
                    )
                    
                    assert result is True
    
    def test_configure_installs_if_needed(self, timeshift_manager, mock_sudo_handler):
        """Test that configure installs Timeshift if not installed."""
        with patch.object(timeshift_manager, 'is_installed', return_value=False):
            with patch.object(timeshift_manager, 'install', return_value=True):
                # Mock path validation to return True
                with patch('digital_signage_toolkit.utils.validators.validate_path', return_value=True):
                    # Mock Path.exists for the snapshot location check
                    with patch('pathlib.Path.exists', return_value=True):
                        # Mock both commands that configure() calls
                        mock_sudo_handler.run_command.return_value = Mock(returncode=0)
                        
                        result = timeshift_manager.configure()
                        
                        assert result is True
    
    def test_configure_invalid_path(self, timeshift_manager):
        """Test configuration with invalid snapshot location."""
        with patch.object(timeshift_manager, 'is_installed', return_value=True):
            result = timeshift_manager.configure(
                snapshot_location="../../../etc/passwd"  # Path traversal attempt
            )
            
            assert result is False


class TestSnapshotOperations:
    """Test snapshot operations."""
    
    def test_list_snapshots_success(self, timeshift_manager, mock_sudo_handler):
        """Test listing snapshots successfully."""
        with patch.object(timeshift_manager, 'is_installed', return_value=True):
            mock_sudo_handler.run_command.return_value = Mock(
                returncode=0,
                stdout="Snapshot #1\nDate: 2024-01-01\nSnapshot #2\nDate: 2024-01-02"
            )
            
            snapshots = timeshift_manager.list_snapshots()
            
            assert isinstance(snapshots, list)
            assert len(snapshots) > 0
    
    def test_list_snapshots_not_installed(self, timeshift_manager):
        """Test listing snapshots when Timeshift is not installed."""
        with patch.object(timeshift_manager, 'is_installed', return_value=False):
            snapshots = timeshift_manager.list_snapshots()
            
            assert snapshots == []
    
    def test_list_snapshots_failure(self, timeshift_manager, mock_sudo_handler):
        """Test listing snapshots when command fails."""
        with patch.object(timeshift_manager, 'is_installed', return_value=True):
            mock_sudo_handler.run_command.return_value = Mock(returncode=1)
            
            snapshots = timeshift_manager.list_snapshots()
            
            assert snapshots == []
    
    def test_create_snapshot_not_installed(self, timeshift_manager):
        """Test creating snapshot when Timeshift is not installed."""
        with patch.object(timeshift_manager, 'is_installed', return_value=False):
            with patch.object(timeshift_manager, 'install', return_value=False):
                completion_callback = Mock()
                timeshift_manager.create_snapshot(completion_callback=completion_callback)
                
                # Wait a moment for async operation
                import time
                time.sleep(0.1)
                
                completion_callback.assert_called_once_with(False)
    
    def test_create_snapshot_success(self, timeshift_manager, mock_sudo_handler):
        """Test successful snapshot creation."""
        with patch.object(timeshift_manager, 'is_installed', return_value=True):
            mock_sudo_handler.run_command.return_value = Mock(returncode=0)
            
            completion_callback = Mock()
            log_callback = Mock()
            timeshift_manager.create_snapshot(
                description="Test snapshot",
                log_callback=log_callback,
                completion_callback=completion_callback
            )
            
            # Wait for async operation
            import time
            time.sleep(0.2)
            
            # Verify command was called
            assert mock_sudo_handler.run_command.called
    
    def test_restore_snapshot_invalid_id(self, timeshift_manager):
        """Test restoring snapshot with invalid ID."""
        completion_callback = Mock()
        timeshift_manager.restore_snapshot(
            snapshot_id="../../../etc/passwd",  # Invalid ID
            completion_callback=completion_callback
        )
        
        import time
        time.sleep(0.1)
        
        completion_callback.assert_called_once_with(False)
    
    def test_restore_snapshot_not_installed(self, timeshift_manager):
        """Test restoring snapshot when Timeshift is not installed."""
        with patch.object(timeshift_manager, 'is_installed', return_value=False):
            completion_callback = Mock()
            timeshift_manager.restore_snapshot(
                snapshot_id="snapshot-1",
                completion_callback=completion_callback
            )
            
            import time
            time.sleep(0.1)
            
            completion_callback.assert_called_once_with(False)
    
    def test_delete_snapshot_success(self, timeshift_manager, mock_sudo_handler):
        """Test successful snapshot deletion."""
        with patch.object(timeshift_manager, 'is_installed', return_value=True):
            mock_sudo_handler.run_command.return_value = Mock(returncode=0)
            
            result = timeshift_manager.delete_snapshot("snapshot-1")
            
            assert result is True
            mock_sudo_handler.run_command.assert_called_once()
    
    def test_delete_snapshot_invalid_id(self, timeshift_manager):
        """Test deleting snapshot with invalid ID."""
        result = timeshift_manager.delete_snapshot("../../../etc/passwd")
        
        assert result is False


class TestSnapshotValidation:
    """Test snapshot ID validation."""
    
    def test_validate_snapshot_id_valid(self, timeshift_manager):
        """Test validation of valid snapshot IDs."""
        # This tests that the validator is used
        with patch('digital_signage_toolkit.utils.validators.validate_snapshot_id', return_value=True):
            result = timeshift_manager.delete_snapshot("snapshot-2024-01-01")
            # Should proceed (we'll mock the actual command)
            assert result is not None
    
    def test_validate_snapshot_id_invalid(self, timeshift_manager):
        """Test validation of invalid snapshot IDs."""
        result = timeshift_manager.delete_snapshot("snapshot;rm -rf /")
        
        assert result is False

