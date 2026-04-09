"""Secrets management module."""
import base64
import json
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging


class SecretsManager:
    """Manages secure storage of sensitive credentials."""

    def __init__(self, secrets_path: Optional[str] = None):
        self.logger = logging.getLogger("SecretsManager")
        self.secrets_path = Path(secrets_path or "/etc/digital-signage-toolkit/secrets.enc")

        # Fallback to user home directory if root path is not writable
        if not self.secrets_path.parent.exists():
            try:
                self.secrets_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                self.secrets_path = Path.home() / ".config" / "digital-signage-toolkit" / "secrets.enc"
                self.secrets_path.parent.mkdir(parents=True, exist_ok=True)

        self._fernet = self._initialize_fernet()

    def _get_machine_id(self) -> str:
        """Get machine ID to use as a stable salt/key base."""
        try:
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    return f.read().strip()
            # Windows fallback or missing
            import uuid
            return str(uuid.getnode())
        except Exception:
            return "default-insecure-machine-id"

    def _initialize_fernet(self) -> Fernet:
        """Create Fernet key derived from machine ID."""
        machine_id = self._get_machine_id()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"dst-toolkit-salt",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        return Fernet(key)

    def set_secret(self, key: str, value: str) -> bool:
        """Store a secret securely."""
        try:
            secrets = self._load_secrets()
            secrets[key] = value
            return self._save_secrets(secrets)
        except Exception as e:
            self.logger.error(f"SET_SECRET: {e}")
            return False

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a stored secret."""
        try:
            secrets = self._load_secrets()
            return secrets.get(key, default)
        except Exception as e:
            self.logger.error(f"GET_SECRET: {e}")
            return default

    def delete_secret(self, key: str) -> bool:
        """Remove a stored secret."""
        try:
            secrets = self._load_secrets()
            if key in secrets:
                del secrets[key]
                return self._save_secrets(secrets)
            return True
        except Exception as e:
            self.logger.error(f"DELETE_SECRET: {e}")
            return False

    def _load_secrets(self) -> dict:
        """Load and decrypt secrets file."""
        if not self.secrets_path.exists():
            return {}
        try:
            with open(self.secrets_path, 'rb') as f:
                encrypted_data = f.read()
            if not encrypted_data:
                return {}
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            self.logger.error(f"LOAD_SECRETS_FAIL: {e}")
            return {}

    def _save_secrets(self, secrets: dict) -> bool:
        """Encrypt and save secrets file."""
        try:
            data = json.dumps(secrets).encode()
            encrypted_data = self._fernet.encrypt(data)
            with open(self.secrets_path, 'wb') as f:
                f.write(encrypted_data)
            try:
                os.chmod(self.secrets_path, 0o600)
            except Exception:
                pass  # Fallback gracefully
            return True
        except Exception as e:
            self.logger.error(f"SAVE_SECRETS_FAIL: {e}")
            return False
