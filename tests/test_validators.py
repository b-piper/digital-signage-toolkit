"""Unit tests for validators module."""
import pytest
from digital_signage_toolkit.utils.validators import (
    validate_hostname, sanitize_hostname,
    validate_snapshot_id, validate_resolution, validate_path,
    validate_script_path, sanitize_for_python_string
)


class TestHostnameValidation:
    """Test hostname validation."""
    
    def test_valid_hostname(self):
        assert validate_hostname("test-hostname")
        assert validate_hostname("test.example.com")
        assert validate_hostname("host123")
    
    def test_invalid_hostname(self):
        assert not validate_hostname("")
        assert not validate_hostname("host name")  # Space
        assert not validate_hostname("host@name")  # Invalid char
        assert not validate_hostname("a" * 64)  # Too long label
    
    def test_sanitize_hostname(self):
        assert sanitize_hostname("test-hostname") == "test-hostname"
        assert sanitize_hostname("test hostname") == "testhostname"
        assert sanitize_hostname("test@hostname") == "testhostname"
        assert sanitize_hostname("") is None


class TestSnapshotValidation:
    """Test snapshot ID validation."""
    
    def test_valid_snapshot_id(self):
        assert validate_snapshot_id("snapshot-123")
        assert validate_snapshot_id("2024-01-01_120000")
        assert validate_snapshot_id("snapshot_1")
    
    def test_invalid_snapshot_id(self):
        assert not validate_snapshot_id("")
        assert not validate_snapshot_id("snapshot; rm -rf /")  # Injection attempt
        assert not validate_snapshot_id("snapshot && ls")  # Command injection


class TestResolutionValidation:
    """Test resolution validation."""
    
    def test_valid_resolution(self):
        assert validate_resolution("1920x1080")
        assert validate_resolution("1280x720")
        assert validate_resolution("3840x2160")
    
    def test_invalid_resolution(self):
        assert not validate_resolution("")
        assert not validate_resolution("1920x")  # Incomplete
        assert not validate_resolution("1920 1080")  # Space instead of x
        assert not validate_resolution("100x100")  # Too small
        assert not validate_resolution("10000x10000")  # Too large


class TestPathValidation:
    """Test path validation."""
    
    def test_valid_path(self):
        assert validate_path("/etc/passwd", must_exist=False)
        assert validate_path("/tmp", must_exist=False)
    
    def test_path_traversal(self):
        assert not validate_path("../../../etc/passwd", must_exist=False)
        assert not validate_path("/etc/../etc/passwd", must_exist=False)


class TestScriptPathValidation:
    """Test script path validation for systemd services."""
    
    def test_valid_script_path(self):
        assert validate_script_path("/usr/local/bin/script.sh")
        assert validate_script_path("~/scripts/start.sh")
        assert validate_script_path("/opt/app/run.sh")
    
    def test_invalid_script_path_with_metacharacters(self):
        assert not validate_script_path("script.sh; rm -rf /")
        assert not validate_script_path("script.sh && ls")
        assert not validate_script_path("script.sh | cat")
        assert not validate_script_path("script.sh $(whoami)")
    
    def test_invalid_script_path_traversal(self):
        assert not validate_script_path("../../../etc/passwd")
        assert not validate_script_path("script.sh; ../../etc/passwd")
    
    def test_sanitize_for_python_string(self):
        """Test sanitizing paths for Python string interpolation."""
        # Normal path
        result = sanitize_for_python_string("/usr/local/bin/script.sh")
        assert result == "'/usr/local/bin/script.sh'"
        
        # Path with spaces
        result = sanitize_for_python_string("/path with spaces/script.sh")
        assert result == "'/path with spaces/script.sh'"
        
        # Path with single quotes (should be escaped)
        result = sanitize_for_python_string("/path'with'quotes/script.sh")
        assert "'path\\'with\\'quotes'" in result or "\\'" in result
        
        # Empty path
        result = sanitize_for_python_string("")
        assert result == "''"

