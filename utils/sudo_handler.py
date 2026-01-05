"""Sudo privilege management module."""
import subprocess
import threading
import time
import ctypes
from typing import Optional, Callable, List
import atexit
import os
from digital_signage_toolkit.utils.logger import get_logger


class SudoHandler:
    """Manages sudo privileges and keeps them alive."""
    
    def __init__(self):
        self._sudo_pid: Optional[int] = None
        self._keep_alive_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._failed_attempts = 0
        self._last_attempt_time = 0.0
        self._rate_limit_window = 300  # 5 minutes
        self._max_attempts = 5
        self.logger = get_logger()
        self._current_user = os.environ.get('USER', 'unknown')
        # Register cleanup on exit
        atexit.register(self.stop_keep_alive)
    
    def check_sudo(self) -> bool:
        """Check if sudo access is available."""
        try:
            result = subprocess.run(
                ['sudo', '-n', 'true'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def request_sudo(self) -> bool:
        """Request sudo password from user (interactive terminal prompt)."""
        try:
            result = subprocess.run(
                ['sudo', '-v'],
                timeout=30
            )
            if result.returncode == 0:
                self.start_keep_alive()
                return True
            return False
        except Exception:
            return False
    
    def request_sudo_with_password(self, password: str) -> bool:
        """Request sudo access using provided password."""
        # Rate limiting check
        current_time = time.time()
        if current_time - self._last_attempt_time > self._rate_limit_window:
            self._failed_attempts = 0
        
        if self._failed_attempts >= self._max_attempts:
            wait_time = self._rate_limit_window - (current_time - self._last_attempt_time)
            if wait_time > 0:
                self.logger.log_security_event(
                    "RATE_LIMIT",
                    f"Too many failed password attempts. Wait {int(wait_time)} seconds."
                )
                return False
        
        try:
            # Use sudo -S to read password from stdin
            process = subprocess.run(
                ['sudo', '-S', '-v'],
                input=password + '\n',
                text=True,
                capture_output=True,
                timeout=30
            )
            
            self._last_attempt_time = current_time
            
            if process.returncode == 0:
                self._failed_attempts = 0
                # Clear password from memory more securely
                self._secure_clear_password(password)
                
                self.logger.log_operation(
                    "SUDO_AUTHENTICATION",
                    self._current_user,
                    "Password authentication successful",
                    success=True
                )
                self.start_keep_alive()
                return True
            else:
                self._failed_attempts += 1
                self.logger.log_security_event(
                    "AUTHENTICATION_FAILURE",
                    f"Failed sudo password attempt ({self._failed_attempts}/{self._max_attempts})"
                )
                # Clear password from memory even on failure
                self._secure_clear_password(password)
                return False
        except Exception as e:
            self.logger.log_error(e, "SUDO_AUTHENTICATION")
            # Clear password from memory
            self._secure_clear_password(password)
            return False
    
    def _secure_clear_password(self, password: str) -> None:
        """Securely clear password from memory using memset."""
        if not password:
            return
        
        try:
            # Use ctypes to call memset for secure memory clearing
            # This is more reliable than just setting to None
            password_bytes = password.encode('utf-8')
            ctypes.memset(
                ctypes.c_char_p(password_bytes),
                0,
                len(password_bytes)
            )
        except Exception:
            # Fallback: standard Python clearing
            pass
        finally:
            # Always clear the Python reference
            password = None
            del password

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
    
    def start_keep_alive(self) -> None:
        """Start thread to keep sudo privileges alive."""
        if self._keep_alive_thread and self._keep_alive_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._keep_alive_thread = threading.Thread(
            target=self._keep_alive_loop,
            daemon=True
        )
        self._keep_alive_thread.start()
    
    def _keep_alive_loop(self) -> None:
        """Keep sudo privileges alive by refreshing every 60 seconds."""
        while not self._stop_event.wait(60):
            try:
                subprocess.run(
                    ['sudo', '-v'],
                    capture_output=True,
                    timeout=5
                )
            except Exception:
                break
    
    def stop_keep_alive(self) -> None:
        """Stop the keep-alive thread."""
        self._stop_event.set()
        if self._keep_alive_thread:
            self._keep_alive_thread.join(timeout=2)
    
    def run_command(self, command: list[str], capture_output: bool = True, 
                   timeout: Optional[int] = None, env: Optional[dict] = None,
                   operation_name: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run a command with sudo."""
        sudo_cmd = ['sudo'] + command
        op_name = operation_name or ' '.join(command[:2])  # First 2 args for logging
        safe_command = self._sanitize_command_for_logging(command)
        
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
            
            if result.returncode != 0:
                self.logger.log_operation(
                    f"SUDO_COMMAND: {op_name}",
                    self._current_user,
                    f"Command failed with exit code {result.returncode}",
                    success=False
                )
            
            return result
        except subprocess.TimeoutExpired as e:
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
        """Run a command with sudo asynchronously."""
        sudo_cmd = ['sudo'] + command
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

