"""Tests for configuration management module."""
import json
import shutil
import tempfile
from pathlib import Path

import pytest
from digital_signage_toolkit.utils.config import Config


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_config_file(temp_config_dir):
    """Create a temporary config file."""
    config_file = temp_config_dir / "config.json"
    return config_file


class TestConfigLoading:
    """Test configuration loading."""

    def test_default_config(self, temp_config_file):
        """Test that default config is loaded when no file exists."""
        config = Config(config_path=str(temp_config_file))

        # Check some default values
        assert config.get('version') == '2.4.4'
        assert config.get('urls.teamviewer') is not None
        assert config.get('network.timeout') == 30
        assert config.get('security.verify_checksums') is True

    def test_load_from_file(self, temp_config_file):
        """Test loading config from JSON file."""
        test_config = {
            'version': '2.4.4',
            'network': {
                'timeout': 60,
                'proxy': 'http://proxy.example.com:8080'
            }
        }
        # Ensure parent directory exists
        temp_config_file.parent.mkdir(parents=True, exist_ok=True)
        temp_config_file.write_text(json.dumps(test_config))

        config = Config(config_path=str(temp_config_file))

        assert config.get('version') == '2.4.4'
        assert config.get('network.timeout') == 60
        assert config.get('network.proxy') == 'http://proxy.example.com:8080'

    def test_load_invalid_json(self, temp_config_file):
        """Test that invalid JSON falls back to defaults."""
        temp_config_file.write_text('{ invalid json }')

        config = Config(config_path=str(temp_config_file))

        # Should fall back to defaults
        assert config.get('version') == '2.4.4'

    def test_load_missing_file(self, temp_config_file):
        """Test loading when config file doesn't exist."""
        # Don't create the file
        config = Config(config_path=str(temp_config_file))

        # Should use defaults
        assert config.get('version') == '2.4.4'


class TestConfigGet:
    """Test configuration value retrieval."""

    def test_get_top_level(self, temp_config_file):
        """Test getting top-level config values."""
        config = Config(config_path=str(temp_config_file))

        assert config.get('version') == '2.4.4'

    def test_get_nested(self, temp_config_file):
        """Test getting nested config values using dot notation."""
        config = Config(config_path=str(temp_config_file))

        assert config.get('network.timeout') == 30
        assert config.get('urls.teamviewer') is not None
        assert config.get('security.verify_checksums') is True

    def test_get_default_value(self, temp_config_file):
        """Test getting default value when key doesn't exist."""
        config = Config(config_path=str(temp_config_file))

        assert config.get('nonexistent.key', 'default') == 'default'
        assert config.get('nonexistent.key') is None

    def test_get_partial_path(self, temp_config_file):
        """Test getting value with partial path."""
        config = Config(config_path=str(temp_config_file))

        # Should return None if path is incomplete
        assert config.get('network.nonexistent') is None


class TestConfigSet:
    """Test configuration value setting."""

    def test_set_top_level(self, temp_config_file):
        """Test setting top-level config values."""
        config = Config(config_path=str(temp_config_file))

        config.set('version', '2.1.0')
        assert config.get('version') == '2.1.0'

    def test_set_nested(self, temp_config_file):
        """Test setting nested config values."""
        config = Config(config_path=str(temp_config_file))

        config.set('network.timeout', 60)
        assert config.get('network.timeout') == 60

    def test_set_new_nested(self, temp_config_file):
        """Test setting new nested config values."""
        config = Config(config_path=str(temp_config_file))

        config.set('new.section.value', 'test')
        assert config.get('new.section.value') == 'test'

    def test_set_overwrite(self, temp_config_file):
        """Test overwriting existing values."""
        config = Config(config_path=str(temp_config_file))

        config.set('network.timeout', 30)
        assert config.get('network.timeout') == 30

        config.set('network.timeout', 60)
        assert config.get('network.timeout') == 60


class TestConfigSave:
    """Test configuration saving."""

    def test_save_config(self, temp_config_file):
        """Test saving configuration to file."""
        # Ensure parent directory exists
        temp_config_file.parent.mkdir(parents=True, exist_ok=True)
        config = Config(config_path=str(temp_config_file))

        config.set('network.timeout', 60)
        config.save()

        # Reload and verify - need to ensure we're loading from the same file
        Config(config_path=str(temp_config_file))
        # The config should merge with defaults, so we need to check the actual saved value
        saved_data = json.loads(temp_config_file.read_text())
        assert saved_data['network']['timeout'] == 60

    def test_save_creates_directory(self, temp_config_dir):
        """Test that save creates parent directories if needed."""
        config_file = temp_config_dir / "subdir" / "config.json"
        config = Config(config_path=str(config_file))

        config.set('test', 'value')
        config.save()

        assert config_file.exists()
        assert config_file.read_text()


class TestConfigExpandPath:
    """Test path expansion."""

    def test_expand_user_home(self, temp_config_file):
        """Test expanding ~ in paths."""
        config = Config(config_path=str(temp_config_file))

        config.set('paths.test', '~/test/path')
        expanded = config.expand_path('paths.test')

        assert '~' not in expanded
        assert expanded.startswith('/') or expanded.startswith('C:')  # Unix or Windows

    def test_expand_env_vars(self, temp_config_file, monkeypatch):
        """Test expanding environment variables."""
        config = Config(config_path=str(temp_config_file))

        monkeypatch.setenv('TEST_VAR', '/test/path')
        config.set('paths.test', '$TEST_VAR/subdir')
        expanded = config.expand_path('paths.test')

        assert '/test/path/subdir' in expanded or '\\test\\path\\subdir' in expanded

    def test_expand_nonexistent_path(self, temp_config_file):
        """Test expanding path that doesn't exist in config."""
        config = Config(config_path=str(temp_config_file))

        expanded = config.expand_path('paths.nonexistent')
        assert expanded == ''


class TestConfigHierarchy:
    """Test configuration hierarchy (user vs system)."""

    def test_user_config_takes_precedence(self, temp_config_dir, monkeypatch):
        """Test that user config overrides system config."""
        # Mock system config path
        system_config = temp_config_dir / "system_config.json"
        user_config = temp_config_dir / "user_config.json"

        # Create system config
        system_config.write_text(json.dumps({'network': {'timeout': 30}}))

        # Create user config
        user_config.write_text(json.dumps({'network': {'timeout': 60}}))

        # Mock paths
        def mock_init(self, config_path=None):
            self.system_config_path = system_config
            self.user_config_path = user_config
            self.config_path = user_config
            self._config = {}
            self.load()

        with pytest.MonkeyPatch().context() as m:
            m.setattr(Config, '__init__', mock_init)
            config = Config()
            assert config.get('network.timeout') == 60

