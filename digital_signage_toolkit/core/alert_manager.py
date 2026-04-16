"""Alert Manager for Digital Signage Toolkit."""
import base64
import json
import os
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..utils.logger import get_logger


class AlertManager:
    """Handles sending email alerts and managing cool-down periods."""

    def __init__(self, config_manager=None):
        self.logger = get_logger()
        self.config = config_manager

        # State file for cool-down tracking
        self.state_file = os.path.expanduser("~/.config/digital_signage_toolkit/alert_state.json")

    def _get_config(self):
        """Retrieve SMTP settings from config."""
        # In a real impl, this would come from a secure store or the main config class
        # For now, we assume the config object has a specific structure or we read directly
        if self.config:
            return self.config.get("smtp", {})
        return {}

    def _load_state(self):
        if not os.path.exists(self.state_file):
            return {}
        try:
            with open(self.state_file) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_state(self, state):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f)

    def _get_secure_password(self, conf: dict) -> str:
        """Retrieve SMTP password with security priority.

        Priority order:
        1. Environment variable DST_SMTP_PASSWORD (best for automation/CI)
        2. OS Keyring via 'keyring' package (if available)
        3. Base64-encoded password from config (backward compatible fallback)

        Returns:
            str: The SMTP password, or empty string if not found
        """
        # Priority 1: Environment variable
        env_password = os.environ.get('DST_SMTP_PASSWORD', '')
        if env_password:
            self.logger.log_operation("CREDENTIAL_SOURCE", "system", "Using environment variable")
            return env_password

        # Priority 2: OS Keyring (optional dependency)
        try:
            import keyring
            kr_password = keyring.get_password('dst-toolkit', 'smtp')
            if kr_password:
                self.logger.log_operation("CREDENTIAL_SOURCE", "system", "Using OS keyring")
                return kr_password
        except ImportError:
            # keyring not installed, continue to fallback
            pass
        except Exception as e:
            # Keyring access failed, log and continue
            self.logger.log_error(e, "KEYRING_ACCESS")

        # Priority 3: Base64-encoded config (backward compatible)
        encoded_pass = conf.get("password", "")
        if encoded_pass:
            try:
                password = base64.b64decode(encoded_pass.encode()).decode()
                self.logger.log_operation("CREDENTIAL_SOURCE", "system", "Using config (base64)")
                return password
            except Exception:
                # Not valid base64, return as plain text
                return encoded_pass

        return ""


    def send_alert(self, subject: str, message: str, cooldown_minutes: int = 60) -> bool:
        """
        Send an email alert if cooldown has passed.

        Args:
            subject: Email subject
            message: Email body
            cooldown_minutes: Time to wait before sending identical alert type

        Returns:
            bool: True if sent, False if failed or suppressed by cooldown
        """
        conf = self._get_config()
        if not conf.get("enabled", False):
            self.logger.log_operation("ALERT_SKIP", "system", "Alerts disabled in config")
            return False

        # check cooldown
        state = self._load_state()
        last_sent = state.get("last_sent", 0)
        now_ts = datetime.now().timestamp()

        if (now_ts - last_sent) < (cooldown_minutes * 60):
            self.logger.log_operation("ALERT_SUPPRESSED", "system", "In cooldown period")
            return False

        try:
            smtp_server = conf.get("host")
            smtp_port = int(conf.get("port", 587))
            sender_email = conf.get("from_addr")
            receiver_email = conf.get("to_addr")

            # Retrieve password with security priority:
            # 1. Environment variable (most secure for automation)
            # 2. OS Keyring (if keyring package available)
            # 3. Base64-encoded config (fallback, backward compatible)
            password = self._get_secure_password(conf)

            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = receiver_email
            msg["Subject"] = f"[DST Alert] {subject}"

            msg.attach(MIMEText(message, "plain"))

            context = ssl.create_default_context()

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, msg.as_string())

            self.logger.log_operation("ALERT_SENT", "system", f"Sent: {subject}")

            # Update state
            state["last_sent"] = now_ts
            self._save_state(state)
            return True

        except Exception as e:
            self.logger.log_error(e, "ALERT_SEND_FAILED")
            return False

    def test_connection(self, host, port, user, password, from_addr, to_addr) -> tuple[bool, str]:
        """Test SMTP connection parameters."""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, int(port)) as server:
                server.starttls(context=context)
                server.login(user, password)
                # Verify we can send a test
                msg = MIMEText("This is a test alert from Digital Signage Toolkit.")
                msg["Subject"] = "DST Test Alert"
                msg["From"] = from_addr
                msg["To"] = to_addr
                server.sendmail(from_addr, to_addr, msg.as_string())
            return True, "Connection successful. Test email sent."
        except Exception as e:
            return False, str(e)
