"""Simple HTTP health check server for kiosk monitoring."""
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint."""

    def do_GET(self):
        """Handle GET requests."""
        if not self._check_auth():
            return

        if self.path == '/health' or self.path == '/':
            self._handle_health_check()
        elif self.path == '/metrics':
            self._handle_metrics()
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())

    def _check_auth(self) -> bool:
        """Verify authentication token."""
        # Lazily import Config to avoid circular imports if any
        from ..utils.config import Config
        config = Config()

        # Check if auth is required (default to False for backward compatibility if missing)
        security = config.get('security', {})
        if not security.get('require_auth', False):
            return True

        # Get expected token (Env var overrides config)
        expected_token = os.environ.get('DST_API_TOKEN') or security.get('api_token')

        # If auth required but no token configured, deny access (Fail Secure)
        if not expected_token or expected_token == 'CHANGEME':
            print("Security Warning: Auth required but token not set/default.")
            self._send_unauthorized("Configuration Error: API Token not set")
            return False

        # Check header
        provided_token = self.headers.get('X-Auth-Token')
        if provided_token != expected_token:
            self._send_unauthorized()
            return False

        return True

    def _send_unauthorized(self, message: str = "Unauthorized"):
        """Send 401 Unauthorized response."""
        self.send_response(401)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode())

    def _handle_health_check(self):
        """Return health status."""
        health = get_health_status()
        status_code = 200 if health.get('healthy', False) else 503

        # Auto-trigger alert if unhealthy
        if not health.get('healthy', True):
            _trigger_alert(health)

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(health, indent=2).encode())

    def _handle_metrics(self):
        """Return Prometheus-compatible metrics."""
        health = get_health_status()
        lines = []
        lines.append('# HELP dst_healthy Whether the kiosk is healthy (1=yes, 0=no)')
        lines.append('# TYPE dst_healthy gauge')
        lines.append(f'dst_healthy {1 if health.get("healthy") else 0}')
        lines.append('')

        checks = health.get('checks', {})

        # Rise Vision
        rv = checks.get('rise_vision', {})
        lines.append('# HELP dst_rise_vision_running Whether Rise Vision is running')
        lines.append('# TYPE dst_rise_vision_running gauge')
        lines.append(f'dst_rise_vision_running {1 if rv.get("running") else 0}')
        lines.append('')

        # Disk
        disk = checks.get('disk', {})
        lines.append('# HELP dst_disk_usage_percent Disk usage percentage')
        lines.append('# TYPE dst_disk_usage_percent gauge')
        lines.append(f'dst_disk_usage_percent {disk.get("percent", 0)}')
        lines.append('# HELP dst_disk_free_bytes Free disk space in bytes')
        lines.append('# TYPE dst_disk_free_bytes gauge')
        lines.append(f'dst_disk_free_bytes {disk.get("free_gb", 0) * 1073741824:.0f}')
        lines.append('')

        # Memory
        mem = checks.get('memory', {})
        lines.append('# HELP dst_memory_usage_percent Memory usage percentage')
        lines.append('# TYPE dst_memory_usage_percent gauge')
        lines.append(f'dst_memory_usage_percent {mem.get("percent", 0)}')
        lines.append('# HELP dst_memory_available_bytes Available memory in bytes')
        lines.append('# TYPE dst_memory_available_bytes gauge')
        lines.append(f'dst_memory_available_bytes {mem.get("available_gb", 0) * 1073741824:.0f}')
        lines.append('')

        # CPU
        cpu = checks.get('cpu', {})
        lines.append('# HELP dst_cpu_usage_percent CPU usage percentage')
        lines.append('# TYPE dst_cpu_usage_percent gauge')
        lines.append(f'dst_cpu_usage_percent {cpu.get("percent", 0)}')
        lines.append('')

        # Uptime
        lines.append('# HELP dst_uptime_seconds System uptime in seconds')
        lines.append('# TYPE dst_uptime_seconds gauge')
        lines.append(f'dst_uptime_seconds {health.get("uptime_seconds", 0)}')
        lines.append('')

        output = '\n'.join(lines) + '\n'
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(output.encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def get_health_status() -> dict:
    """Get comprehensive health status of the kiosk."""
    status = {
        'healthy': True,
        'hostname': _get_hostname(),
        'version': _get_version(),
        'checks': {}
    }

    # Check Rise Vision status
    rise_status = _check_rise_vision()
    status['checks']['rise_vision'] = rise_status
    if not rise_status['running']:
        status['healthy'] = False

    # Check disk space
    disk_status = _check_disk_space()
    status['checks']['disk'] = disk_status
    if disk_status['critical']:
        status['healthy'] = False

    # Check memory
    memory_status = _check_memory()
    status['checks']['memory'] = memory_status
    if memory_status['critical']:
        status['healthy'] = False

    # Check CPU
    cpu_status = _check_cpu()
    status['checks']['cpu'] = cpu_status

    # System uptime
    status['uptime_seconds'] = _get_uptime()

    return status


# Alert integration --------------------------------------------------------
_last_alert_time = 0
_ALERT_COOLDOWN = 600  # 10 minutes between alerts

def _trigger_alert(health: dict) -> None:
    """Send alert email when health check is unhealthy (with cooldown)."""
    global _last_alert_time
    now = time.time()
    if now - _last_alert_time < _ALERT_COOLDOWN:
        return  # Still in cooldown

    try:
        from ..utils.config import Config
        from .alert_manager import AlertManager
        config = Config()
        alert_mgr = AlertManager(config)

        hostname = health.get('hostname', 'unknown')
        checks = health.get('checks', {})
        problems = []
        if not checks.get('rise_vision', {}).get('running', True):
            problems.append('Rise Vision is NOT running')
        if checks.get('disk', {}).get('critical', False):
            problems.append(f'Disk usage critical: {checks["disk"].get("percent", "?")}%')
        if checks.get('memory', {}).get('critical', False):
            problems.append(f'Memory usage critical: {checks["memory"].get("percent", "?")}%')

        if problems:
            subject = f'[DST Alert] {hostname} — Health Check Failed'
            body = f'Kiosk {hostname} is unhealthy:\n\n'
            body += '\n'.join(f'  • {p}' for p in problems)
            body += f'\n\nTimestamp: {time.strftime("%Y-%m-%d %H:%M:%S")}'
            alert_mgr.send_alert(subject, body)
            _last_alert_time = now
    except Exception:
        pass  # Alert failure should never crash the health server


def _get_hostname() -> str:
    """Get system hostname."""
    try:
        import socket
        return socket.gethostname()
    except Exception:
        return 'unknown'


def _get_version() -> str:
    """Get installed DST version."""
    version_file = '/opt/dst-toolkit/VERSION'
    try:
        if os.path.exists(version_file):
            with open(version_file) as f:
                return f.read().strip()
    except Exception:
        pass
    return 'unknown'


def _check_rise_vision() -> dict:
    """Check if Rise Vision Player is running."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'Rise Vision'],
            capture_output=True,
            timeout=5
        )
        running = result.returncode == 0
        return {'running': running, 'status': 'running' if running else 'stopped'}
    except Exception as e:
        return {'running': False, 'status': 'error', 'error': str(e)}


def _check_disk_space() -> dict:
    """Check disk space usage."""
    if not psutil:
        return {'percent': 0, 'critical': False, 'error': 'psutil not available'}

    try:
        disk = psutil.disk_usage('/')
        critical = disk.percent >= 90
        warning = disk.percent >= 80
        return {
            'percent': disk.percent,
            'free_gb': round(disk.free / (1024**3), 2),
            'total_gb': round(disk.total / (1024**3), 2),
            'critical': critical,
            'warning': warning
        }
    except Exception as e:
        return {'percent': 0, 'critical': False, 'error': str(e)}


def _check_memory() -> dict:
    """Check memory usage."""
    if not psutil:
        return {'percent': 0, 'critical': False, 'error': 'psutil not available'}

    try:
        memory = psutil.virtual_memory()
        critical = memory.percent >= 95
        warning = memory.percent >= 85
        return {
            'percent': memory.percent,
            'available_gb': round(memory.available / (1024**3), 2),
            'total_gb': round(memory.total / (1024**3), 2),
            'critical': critical,
            'warning': warning
        }
    except Exception as e:
        return {'percent': 0, 'critical': False, 'error': str(e)}


def _check_cpu() -> dict:
    """Check CPU usage."""
    if not psutil:
        return {'percent': 0, 'error': 'psutil not available'}

    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        return {
            'percent': cpu_percent,
            'high': cpu_percent >= 90
        }
    except Exception as e:
        return {'percent': 0, 'error': str(e)}


def _get_uptime() -> int:
    """Get system uptime in seconds."""
    if not psutil:
        return 0

    try:
        import time
        boot_time = psutil.boot_time()
        return int(time.time() - boot_time)
    except Exception:
        return 0


class HealthServer:
    """Health check HTTP server."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start the health server in a background thread."""
        try:
            from ..utils.config import Config
            config = Config()
            bind_addr = config.get('network.health_server_bind_address', '127.0.0.1')
            self.server = HTTPServer((bind_addr, self.port), HealthCheckHandler)
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            print(f"Failed to start health server: {e}")
            return False

    def stop(self):
        """Stop the health server."""
        if self.server:
            self.server.shutdown()
            self.server = None


# Global server instance
_health_server: Optional[HealthServer] = None


def start_health_server(port: int = 8080) -> bool:
    """Start the global health server.

    Args:
        port: Port to listen on (default 8080)

    Returns:
        True if started successfully
    """
    global _health_server

    if _health_server is not None:
        return True  # Already running

    _health_server = HealthServer(port)
    return _health_server.start()


def stop_health_server():
    """Stop the global health server."""
    global _health_server

    if _health_server:
        _health_server.stop()
        _health_server = None


if __name__ == '__main__':
    # Run standalone for testing
    import time

    print("Starting health server on port 8080...")
    print("Test with: curl http://localhost:8080/health")

    if start_health_server(8080):
        print("Server started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping server...")
            stop_health_server()
    else:
        print("Failed to start server")
