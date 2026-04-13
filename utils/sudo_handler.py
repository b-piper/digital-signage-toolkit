"""Sudo privilege management module."""
import os
import subprocess
import threading
from typing import Callable, List, Optional

from digital_signage_toolkit.utils.logger import get_logger


class SudoHandler:
    """Manages sudo privileges and keeps them alive."""

    def __init__(self):
        self._current_user = os.environ.get('USER', 'root')
        self.logger = get_logger()


    def _sanitize_command_for_logging(self, command: List[str]) -> str:
        """Sanitize a command list before logging to avoid leaking secrets.

        This is defensive: today we don't pass passwords on the command-line,
        but this guards against future changes accidentally exposing them in logs.
        """
        sanitized: List[str] = []
        mask_next = False

        for arg in command:
            lower = arg.lower()
            if mask_next:
                sanitized.append("****")
                mask_next = False
                continue

            if any(keyword in lower for keyword in ("password", "passwd", "pass=", "secret", "token")):
                # Mask this argument and possibly the next one if it's a flag
                if lower in ("-p", "--password", "--pass", "--passwd"):
                    sanitized.append(arg)
                    mask_next = True
                else:
                    sanitized.append("****")
            else:
                sanitized.append(arg)

        return " ".join(sanitized)


    def run_command(self, command: list[str], capture_output: bool = True,
                   timeout: Optional[int] = None, env: Optional[dict] = None,
                   operation_name: Optional[str] = None,
                   allowed_exit_codes: Optional[list[int]] = None) -> subprocess.CompletedProcess:
        """Run a command as root."""
        sudo_cmd = command
        op_name = operation_name or ' '.join(command[:2])  # First 2 args for logging
        safe_command = self._sanitize_command_for_logging(command)
        
        allowed_codes = [0] if allowed_exit_codes is None else allowed_exit_codes

        self.logger.log_operation(
            f"SUDO_COMMAND: {op_name}",
            self._current_user,
            f"Command: {safe_command}",
            success=True  # Will update if fails
        )

        try:
            result = subprocess.run(
                sudo_cmd,
                capture_output=capture_output,
                timeout=timeout,
                text=True,
                env=env
            )

            if result.returncode not in allowed_codes:
                self.logger.log_operation(
                    f"SUDO_COMMAND: {op_name}",
                    self._current_user,
                    f"Command failed with exit code {result.returncode}",
                    success=False
                )

            return result
        except subprocess.TimeoutExpired:
            self.logger.log_operation(
                f"SUDO_COMMAND: {op_name}",
                self._current_user,
                f"Command timed out after {timeout}s",
                success=False
            )
            raise
        except Exception as e:
            self.logger.log_error(e, f"SUDO_COMMAND: {op_name}")
            raise

    def run_command_async(self, command: list[str],
                         callback: Optional[Callable] = None,
                         log_callback: Optional[Callable[[str], None]] = None) -> subprocess.Popen:
        """Run a command as root asynchronously."""
        sudo_cmd = command
        process = subprocess.Popen(
            sudo_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        if log_callback:
            threading.Thread(
                target=self._read_output,
                args=(process, log_callback, callback),
                daemon=True
            ).start()

        return process

    def _read_output(self, process: subprocess.Popen,
                    log_callback: Callable[[str], None],
                    completion_callback: Optional[Callable] = None) -> None:
        """Read output from process and call log callback."""
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    log_callback(line.rstrip())
            process.wait()
            if completion_callback:
                completion_callback(process.returncode)
        except Exception as e:
            log_callback(f"Error reading output: {e}")
            if completion_callback:
                completion_callback(-1)

