"""File utilities for downloads, checksums, and verification."""
import hashlib
import subprocess
import time
import os
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def verify_checksum(file_path: Path, expected_checksum: str) -> bool:
    """Verify file checksum matches expected value."""
    if not expected_checksum:
        return True  # No checksum provided, skip verification
    
    try:
        actual_checksum = calculate_sha256(file_path)
        return actual_checksum.lower() == expected_checksum.lower()
    except Exception:
        return False


def download_with_retry(url: str, dest_path: str,
                       proxy: Optional[str] = None,
                       proxy_user: Optional[str] = None,
                       proxy_pass: Optional[str] = None,
                       timeout: int = 30,
                       max_retries: int = 3,
                       retry_delay: int = 5,
                       bandwidth_limit: int = 0,
                       log_callback: Optional[Callable[[str], None]] = None) -> bool:
    """Download file with retry logic, proxy support, and bandwidth limiting."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Build wget command
    wget_cmd = ['wget', '--tries=1', f'--timeout={timeout}', '-O', str(dest), url]
    
    # Add proxy support - use environment variables to avoid password in process args
    env = os.environ.copy()
    if proxy:
        parsed = urlparse(proxy)
        if proxy_user and proxy_pass:
            # Use environment variables instead of command-line args for security
            proxy_url = f"{parsed.scheme}://{proxy_user}:{proxy_pass}@{parsed.netloc}"
            env['http_proxy'] = proxy_url
            env['https_proxy'] = proxy_url
            env['HTTP_PROXY'] = proxy_url
            env['HTTPS_PROXY'] = proxy_url
        else:
            env['http_proxy'] = proxy
            env['https_proxy'] = proxy
            env['HTTP_PROXY'] = proxy
            env['HTTPS_PROXY'] = proxy
        wget_cmd.extend(['--proxy=on'])
    
    # Add bandwidth limiting
    if bandwidth_limit > 0:
        wget_cmd.append(f'--limit-rate={bandwidth_limit}K')
    
    # Retry loop with exponential backoff
    for attempt in range(1, max_retries + 1):
        try:
            if log_callback:
                if attempt > 1:
                    log_callback(f"Retry attempt {attempt}/{max_retries}...")
                else:
                    log_callback(f"Downloading from {url}...")
            
            result = subprocess.run(
                wget_cmd,
                capture_output=True,
                text=True,
                timeout=timeout * 2,  # Allow more time for slow connections
                env=env  # Use environment with proxy credentials
            )
            
            if result.returncode == 0 and dest.exists():
                # Verify file is not truncated by checking size
                # If Content-Length header was present, wget would have validated it
                # For now, check that file size > 0 and is reasonable
                file_size = dest.stat().st_size
                if file_size == 0:
                    if log_callback:
                        log_callback("Download failed: File is empty (truncated)")
                    if attempt < max_retries:
                        wait_time = retry_delay * (2 ** (attempt - 1))
                        if log_callback:
                            log_callback(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    return False
                
                if log_callback:
                    log_callback(f"Download complete: {dest} ({file_size} bytes)")
                return True
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                if log_callback:
                    log_callback(f"Download failed: {error_msg}")
                
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    if log_callback:
                        log_callback(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    return False
                    
        except subprocess.TimeoutExpired:
            if log_callback:
                log_callback(f"Download timed out (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))
                time.sleep(wait_time)
            else:
                return False
        except Exception as e:
            if log_callback:
                log_callback(f"Download error: {e}")
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))
                time.sleep(wait_time)
            else:
                return False
    
    return False

