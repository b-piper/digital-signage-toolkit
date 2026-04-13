"""Software installation module."""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from digital_signage_toolkit.utils.config import Config
from digital_signage_toolkit.utils.file_utils import download_with_retry, verify_checksum
from digital_signage_toolkit.utils.logger import get_logger
from digital_signage_toolkit.utils.sudo_handler import SudoHandler


class SoftwareInstaller:
    """Handles software installation (TeamViewer, Rise Vision)."""

    def __init__(self, sudo_handler: SudoHandler, config: Optional[Config] = None):
        self.sudo = sudo_handler
        self.config = config or Config()
        self.logger = get_logger()

    def is_installed(self, command: str) -> bool:
        """Check if a command/package is installed."""
        return shutil.which(command) is not None

    def download_file(self, url: str, dest_path: str,
                     expected_checksum: Optional[str] = None,
                     log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Download a file from URL with retry, proxy, and checksum verification."""
        # Get network settings from config
        proxy = self.config.get('network.proxy', '')
        proxy_user = self.config.get('network.proxy_user', '')
        proxy_pass = self.config.get('network.proxy_pass', '')
        timeout = self.config.get('network.timeout', 30)
        max_retries = self.config.get('network.retry_attempts', 3)
        retry_delay = self.config.get('network.retry_delay', 5)
        bandwidth_limit = self.config.get('network.bandwidth_limit', 0)
        verify_checksums = self.config.get('security.verify_checksums', True)

        # Download with retry
        try:
            success = download_with_retry(
                url, dest_path,
                proxy=proxy if proxy else None,
                proxy_user=proxy_user if proxy_user else None,
                proxy_pass=proxy_pass if proxy_pass else None,
                timeout=timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
                bandwidth_limit=bandwidth_limit,
                log_callback=log_callback
            )

            if not success:
                return False
        except Exception as e:
            self.logger.log_error(e, "DOWNLOAD_FILE")
            if log_callback:
                log_callback(f"Download error: {e}")
            return False

        # Verify checksum if provided and verification is enabled
        if verify_checksums and expected_checksum:
            if log_callback:
                log_callback("Verifying file integrity...")

            if not verify_checksum(Path(dest_path), expected_checksum):
                if log_callback:
                    log_callback("❌ ERROR: File checksum verification failed!")
                    log_callback("The downloaded file may be corrupted or tampered with.")
                self.logger.log_security_event(
                    "CHECKSUM_MISMATCH",
                    f"Downloaded file {dest_path} failed checksum verification"
                )
                # Remove corrupted file
                try:
                    Path(dest_path).unlink()
                except Exception:
                    pass
                return False

            if log_callback:
                log_callback("✅ File integrity verified")

        return True

    def install_deb_package(self, deb_path: str,
                           log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Install a .deb package."""
        # Validate deb path
        from digital_signage_toolkit.utils.validators import validate_path
        if not validate_path(deb_path, must_exist=True):
            self.logger.log_error(
                ValueError(f"Invalid .deb file path: {deb_path}"),
                "INSTALL_DEB_PACKAGE"
            )
            if log_callback:
                log_callback(f"Invalid .deb file path: {deb_path}")
            return False

        if log_callback:
            log_callback(f"Installing {deb_path}...")

        try:
            result = self.sudo.run_command(
                ['apt', '-o', 'Dpkg::Lock::Timeout=120', 'install', '-y', deb_path],
                timeout=600
            )

            if result.returncode == 0:
                if log_callback:
                    log_callback("Installation successful")
                return True
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                if log_callback:
                    log_callback(f"Installation failed: {error_msg}")
                self.logger.log_error(
                    RuntimeError(f"Package installation failed: {error_msg}"),
                    "INSTALL_DEB_PACKAGE"
                )
                return False
        except Exception as e:
            if log_callback:
                log_callback(f"Installation error: {e}")
            self.logger.log_error(e, "INSTALL_DEB_PACKAGE")
            return False

    def install_teamviewer(self, url: Optional[str] = None, local_path: Optional[str] = None,
                          log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Install TeamViewer."""
        if self.is_installed('teamviewer'):
            if log_callback:
                log_callback("TeamViewer is already installed")
            return True

        # Get URL and checksum from config if not provided
        if not url:
            url = self.config.get('urls.teamviewer', '')
        expected_checksum = self.config.get('checksums.teamviewer', '')

        # Try local file first
        if local_path and Path(local_path).exists():
            if log_callback:
                log_callback(f"Using local installer: {local_path}")
            # Verify checksum of local file if provided
            if expected_checksum:
                if not verify_checksum(Path(local_path), expected_checksum):
                    if log_callback:
                        log_callback("❌ ERROR: Local file checksum verification failed!")
                    return False
            return self.install_deb_package(local_path, log_callback)

        # Download and install
        temp_deb = '/tmp/teamviewer.deb'
        if self.download_file(url, temp_deb, expected_checksum=expected_checksum, log_callback=log_callback):
            success = self.install_deb_package(temp_deb, log_callback)
            # Cleanup
            if Path(temp_deb).exists():
                os.remove(temp_deb)
            return success

        return False

    def install_rise_vision(self, url: Optional[str] = None, local_path: Optional[str] = None,
                           startup_script_path: str = "~/rvplayer/scripts/start.sh",
                           log_callback: Optional[Callable[[str], None]] = None,
                           completion_callback: Optional[Callable[[bool], None]] = None) -> None:
        """Install Rise Vision Player (synchronous, with proper display env)."""
        # Resolve ~ to the REAL user's home, not /root
        real_home = self.config.get_real_user_home()
        resolved_startup = startup_script_path.replace('~', real_home, 1) if startup_script_path.startswith('~') else startup_script_path
        startup_path = Path(resolved_startup)

        if startup_path.exists() and startup_path.stat().st_size > 0:
            if log_callback:
                log_callback("Rise Vision is already installed")
            if completion_callback:
                completion_callback(True)
            return

        # Get URL and checksum from config if not provided
        if not url:
            url = self.config.get('urls.rise_vision', '')
        expected_checksum = self.config.get('checksums.rise_vision', '')

        installer_path = None

        # Try local file first
        if local_path and Path(local_path).exists():
            installer_path = local_path
            if log_callback:
                log_callback(f"Using local installer: {local_path}")
            # Verify checksum of local file if provided
            if expected_checksum:
                if not verify_checksum(Path(local_path), expected_checksum):
                    if log_callback:
                        log_callback("❌ ERROR: Local file checksum verification failed!")
                    if completion_callback:
                        completion_callback(False)
                    return
        else:
            # Download installer
            temp_installer = '/tmp/installer-lnx-64.sh'
            if log_callback:
                log_callback(f"Downloading Rise Vision installer from {url}...")
            if self.download_file(url, temp_installer, expected_checksum=expected_checksum, log_callback=log_callback):
                installer_path = temp_installer
                if log_callback:
                    log_callback("Download complete")
            else:
                if log_callback:
                    log_callback("❌ Failed to download Rise Vision installer")
                    log_callback("Check internet connectivity and URL configuration")
                self.logger.log_error(
                    RuntimeError(f"Rise Vision installer download failed from {url}"),
                    "INSTALL_RISE_VISION"
                )
                if completion_callback:
                    completion_callback(False)
                return

        # Make executable and launch
        if installer_path:
            os.chmod(installer_path, 0o755)

            # Ensure dbus-x11 is installed (provides dbus-launch needed by the installer)
            if log_callback:
                log_callback("Ensuring dbus-x11 is installed (required by Rise Vision installer)...")
            self.sudo.run_command(['apt-get', '-o', 'Dpkg::Lock::Timeout=120', 'install', '-y', 'dbus-x11'], timeout=120)

            if log_callback:
                log_callback("Launching Rise Vision installer...")

            # Determine the real user to run the installer as
            sudo_user = Config.get_real_user()

            # Set up environment with display access for the installer
            env = os.environ.copy()
            env['DISPLAY'] = os.environ.get('DISPLAY', ':0')
            if sudo_user:
                xauth = f"/home/{sudo_user}/.Xauthority"
                env['HOME'] = f"/home/{sudo_user}"
                env['USER'] = sudo_user
            else:
                xauth = os.path.expanduser("~/.Xauthority")
                env['HOME'] = os.path.expanduser('~')
            env['XAUTHORITY'] = os.environ.get('XAUTHORITY', xauth)

            try:
                # Build command — run as the actual user if possible
                if sudo_user and os.geteuid() == 0:
                    cmd = ['sudo', '-u', sudo_user, '-E', installer_path]
                else:
                    cmd = [installer_path]

                # Run the installer and wait for completion (synchronous)
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env
                )

                # Wait for completion with timeout
                try:
                    stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout
                    if process.returncode == 0:
                        if log_callback:
                            log_callback("✅ Rise Vision installer completed successfully")
                        # Verify installation by checking for startup script
                        if startup_path.exists():
                            if log_callback:
                                log_callback("✅ Rise Vision Player startup script found")
                        else:
                            if log_callback:
                                log_callback("⚠️ Installer completed but startup script not yet found")
                                log_callback(f"Expected at: {startup_path}")
                                log_callback("The player may need a reboot to complete setup")
                        if completion_callback:
                            completion_callback(True)
                    else:
                        error_detail = stderr.strip() if stderr else stdout.strip() if stdout else "Unknown error"
                        if log_callback:
                            log_callback(f"❌ Rise Vision installer failed (exit code {process.returncode})")
                            if error_detail:
                                log_callback(f"   Error: {error_detail[:200]}")
                        self.logger.log_error(
                            RuntimeError(f"Rise Vision installer exited with code {process.returncode}: {error_detail[:500]}"),
                            "INSTALL_RISE_VISION"
                        )
                        if completion_callback:
                            completion_callback(False)
                except subprocess.TimeoutExpired:
                    process.kill()
                    if log_callback:
                        log_callback("❌ Rise Vision installer timed out after 10 minutes")
                    self.logger.log_error(
                        TimeoutError("Rise Vision installer timed out after 600 seconds"),
                        "INSTALL_RISE_VISION"
                    )
                    if completion_callback:
                        completion_callback(False)
            except Exception as e:
                if log_callback:
                    log_callback(f"❌ Error running Rise Vision installer: {e}")
                self.logger.log_error(e, "INSTALL_RISE_VISION")
                if completion_callback:
                    completion_callback(False)

    def fix_rise_permissions(self, player_dir: str = "~/rvplayer",
                           log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Fix Rise Vision Player permissions (chrome-sandbox)."""
        player_path = Path(os.path.expanduser(player_dir))
        sandbox = None

        # Find chrome-sandbox
        for root, dirs, files in os.walk(player_path):
            if 'chrome-sandbox' in files:
                sandbox = Path(root) / 'chrome-sandbox'
                break

        if sandbox and sandbox.exists():
            try:
                if log_callback:
                    log_callback(f"Fixing permissions for {sandbox}")

                self.sudo.run_command(['chown', 'root:root', str(sandbox)], timeout=10)
                self.sudo.run_command(['chmod', '4755', str(sandbox)], timeout=10)

                if log_callback:
                    log_callback("Permissions fixed")
                return True
            except Exception as e:
                if log_callback:
                    log_callback(f"Failed to fix permissions: {e}")
                return False

        return True  # No sandbox found, not necessarily an error

    def clear_rise_cache(self, log_callback: Optional[Callable[[str], None]] = None, aggressive: bool = False) -> bool:
        """Clear Rise Vision Player cache. If aggressive=True, also clears Electron/Chromium caches."""
        cache_dirs = [
            Path.home() / '.config' / 'Rise Vision Player' / 'Cache',
            Path.home() / '.config' / 'Rise Vision Player' / 'GPUCache',
            Path.home() / '.cache' / 'Rise Vision Player',
        ]

        # Add aggressive cache clearing locations
        if aggressive:
            cache_dirs.extend([
                Path.home() / '.config' / 'chromium' / 'Cache',
                Path.home() / '.cache' / 'chromium',
                Path.home() / '.config' / 'electron' / 'Cache',
                Path.home() / '.cache' / 'electron',
            ])

        cleared_count = 0
        total_size_freed = 0

        for cache_dir in cache_dirs:
            if cache_dir.exists():
                try:
                    # Check disk space before deletion (Linux only)
                    try:
                        statvfs = os.statvfs(cache_dir.parent)
                        free_space = statvfs.f_bavail * statvfs.f_frsize
                    except AttributeError:
                        # Windows doesn't have statvfs, skip disk space check
                        free_space = None

                    # Calculate size before deletion (for logging) - use du for efficiency
                    dir_size = 0
                    try:
                        # Use du command for faster size calculation on large directories
                        import subprocess
                        result = subprocess.run(
                            ['du', '-sb', str(cache_dir)],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode == 0 and result.stdout:
                            dir_size = int(result.stdout.split()[0])
                    except Exception:
                        # Fallback to Python calculation if du fails
                        try:
                            dir_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                        except Exception:
                            pass

                    total_size_freed += dir_size

                    # Check if we have enough space (need at least 10% free after deletion)
                    if free_space < (dir_size * 1.1):
                        if log_callback:
                            log_callback(f"Warning: Low disk space, skipping {cache_dir}")
                        self.logger.log_error(
                            OSError(f"Insufficient disk space to safely delete {cache_dir}"),
                            "CLEAR_RISE_CACHE"
                        )
                        continue

                    # Force remove (aggressive mode kills processes if needed)
                    if aggressive:
                        # Try to kill any processes using the cache
                        try:
                            import subprocess
                            subprocess.run(['fuser', '-k', str(cache_dir)],
                                         capture_output=True, timeout=5, stderr=subprocess.DEVNULL)
                        except Exception:
                            pass

                    # Remove directory tree with proper error handling
                    try:
                        shutil.rmtree(cache_dir, ignore_errors=False)
                    except OSError as e:
                        if e.errno == 28:  # No space left on device
                            if log_callback:
                                log_callback(f"ERROR: Disk full while clearing {cache_dir}")
                            self.logger.log_error(e, "CLEAR_RISE_CACHE")
                            return False  # Critical error, stop cleanup
                        elif aggressive:
                            # In aggressive mode, try alternative methods
                            try:
                                import subprocess
                                subprocess.run(['rm', '-rf', str(cache_dir)],
                                             capture_output=True, timeout=30, stderr=subprocess.DEVNULL)
                            except Exception:
                                if log_callback:
                                    log_callback(f"Failed to clear {cache_dir}: {e}")
                                continue
                        else:
                            if log_callback:
                                log_callback(f"Failed to clear {cache_dir}: {e}")
                            self.logger.log_error(e, "CLEAR_RISE_CACHE")
                            continue

                    if log_callback:
                        size_mb = dir_size / (1024 * 1024)
                        log_callback(f"Cleared cache: {cache_dir} ({size_mb:.1f}MB)")
                    cleared_count += 1
                except Exception as e:
                    if log_callback:
                        log_callback(f"Failed to clear {cache_dir}: {e}")
                    self.logger.log_error(e, "CLEAR_RISE_CACHE")
                    # Continue with other directories even if one fails

        if cleared_count > 0 and log_callback:
            total_mb = total_size_freed / (1024 * 1024)
            log_callback(f"Cache cleanup complete: {cleared_count} directories, {total_mb:.1f}MB freed")
        elif cleared_count == 0 and log_callback:
            log_callback("No cache directories found")

        return True

