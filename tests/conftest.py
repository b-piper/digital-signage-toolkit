"""Pytest configuration and shared fixtures."""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.get = Mock(return_value="default_value")
    config.expand_path = Mock(side_effect=lambda x: f"/home/user/{x.split('.')[-1]}")
    return config


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = Mock()
    logger.app_logger = Mock()
    logger.app_logger.info = Mock()
    logger.app_logger.warning = Mock()
    logger.app_logger.error = Mock()
    logger.log_operation = Mock()
    logger.log_error = Mock()
    logger.log_security_event = Mock()
    return logger




