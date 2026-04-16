"""Tests for SecretsManager."""

import pytest

from digital_signage_toolkit.utils.secrets_manager import SecretsManager


@pytest.fixture
def temp_secrets_path(tmp_path):
    """Provide a temporary path for secrets."""
    return tmp_path / "secrets.enc"

@pytest.fixture
def secrets_manager(temp_secrets_path):
    """Create a SecretsManager instance."""
    return SecretsManager(secrets_path=str(temp_secrets_path))


class TestSecretsManager:
    """Test SecretsManager functionality."""

    def test_init_creates_directory(self, tmp_path):
        """Test that init creates the parent directory."""
        path = tmp_path / "new_dir" / "secrets.enc"
        SecretsManager(secrets_path=str(path))
        assert path.parent.exists()

    def test_encryption_decryption(self, secrets_manager):
        """Test encrypting and decrypting secrets."""
        # Test setting a secret
        success = secrets_manager.set_secret('test_key', 'test_value')
        assert success is True

        # Test getting real value
        value = secrets_manager.get_secret('test_key')
        assert value == 'test_value'

        # Test getting default for missing real value
        default_value = secrets_manager.get_secret('missing_key', 'default')
        assert default_value == 'default'

    def test_delete_secret(self, secrets_manager):
        """Test deleting a secret."""
        secrets_manager.set_secret('key1', 'val1')
        secrets_manager.delete_secret('key1')
        assert secrets_manager.get_secret('key1') is None

    def test_load_empty_or_missing(self, secrets_manager):
        """Test loading from a missing or empty file."""
        assert secrets_manager._load_secrets() == {}

        # Create empty file
        secrets_manager.secrets_path.touch()
        assert secrets_manager._load_secrets() == {}
