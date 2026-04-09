"""Unit tests for file utilities."""
import tempfile
from pathlib import Path

from digital_signage_toolkit.utils.file_utils import calculate_sha256, verify_checksum


class TestChecksum:
    """Test checksum calculation and verification."""

    def test_calculate_sha256(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = Path(f.name)

        try:
            checksum = calculate_sha256(temp_path)
            assert len(checksum) == 64  # SHA256 hex length
            assert isinstance(checksum, str)
        finally:
            temp_path.unlink()

    def test_verify_checksum_match(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = Path(f.name)

        try:
            expected = calculate_sha256(temp_path)
            assert verify_checksum(temp_path, expected)
        finally:
            temp_path.unlink()

    def test_verify_checksum_mismatch(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = Path(f.name)

        try:
            assert not verify_checksum(temp_path, "invalid_checksum")
        finally:
            temp_path.unlink()

    def test_verify_checksum_no_expected(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = Path(f.name)

        try:
            assert verify_checksum(temp_path, "")  # No checksum = skip verification
        finally:
            temp_path.unlink()




