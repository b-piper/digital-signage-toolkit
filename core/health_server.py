"""Simple HTTP health check server for kiosk monitoring."""
import json
import os
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health' or self.path == '/':
            self._handle_health_check()
        elif self.path == '/metrics':
            self._handle_metrics()
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def _handle_health_check(self):
        """Return health status."""
        health = get_health_status()
        status_code = 200 if health.get('healthy', False) else 503
        
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(health, indent=2).encode())
    
    def _handle_metrics(self):
        """Return Prometheus-compatible metrics."""
        metrics = get_prometheus_metrics()
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(metrics.encode())
    
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


def get_prometheus_metrics() -> str:
    """Generate Prometheus-compatible metrics."""
    lines = []
    
    # Rise Vision status
    rise_running = 1 if _check_rise_vision()['running'] else 0
    lines.append(f'dst_rise_vision_running {rise_running}')
    
    # Disk usage
    if psutil:
        disk = psutil.disk_usage('/')
        lines.append(f'dst_disk_usage_percent {disk.percent}')
        lines.append(f'dst_disk_free_bytes {disk.free}')
        lines.append(f'dst_disk_total_bytes {disk.total}')
    
    # Memory usage
    if psutil:
        memory = psutil.virtual_memory()
        lines.append(f'dst_memory_usage_percent {memory.percent}')
        lines.append(f'dst_memory_available_bytes {memory.available}')
        lines.append(f'dst_memory_total_bytes {memory.total}')
    
    # CPU usage
    if psutil:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        lines.append(f'dst_cpu_usage_percent {cpu_percent}')
    
    # Uptime
    uptime = _get_uptime()
    lines.append(f'dst_uptime_seconds {uptime}')
    
    return '\n'.join(lines) + '\n'


def _get_hostname() -> str:
    """Get system hostname."""
    try:
        return subprocess.getoutput('hostname').strip()
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
            self.server = HTTPServer(('0.0.0.0', self.port), HealthCheckHandler)
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
