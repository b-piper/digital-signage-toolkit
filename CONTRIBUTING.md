# Contributing to Digital Signage Toolkit

Thank you for your interest in contributing! This document outlines the development workflow and code standards.

## Development Setup

```bash
# Clone and create virtual environment
git clone <repository>
cd "Digital Signage Toolkit"
python3 -m venv venv
source venv/bin/activate  # Linux

# Install dependencies
pip install -r requirements.txt
pip install -e .  # Editable install
```

## Running the Application

```bash
# GUI mode (requires sudo)
sudo python main.py

# Headless mode
sudo python main.py --status
sudo python main.py --heal
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=digital_signage_toolkit --cov-report=html
```

## Code Standards

### Style
- **Python 3.8+** compatibility required
- Follow **PEP 8** style guidelines
- Use **type hints** for function signatures
- Maximum line length: 100 characters

### Documentation
- All public methods must have docstrings
- Use Google-style docstrings format
- Update ARCHITECTURE.md for structural changes

### Security
- All user inputs must be validated (see `utils/validators.py`)
- Never execute shell commands with unsanitized input
- Log all privileged operations via `logger.log_operation()`

### Testing
- Add tests for new functionality in `tests/`
- Mock subprocess calls and system dependencies
- Test edge cases and error conditions

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Run `pytest` and ensure all tests pass
4. Update documentation if needed
5. Submit PR with clear description

## Project Structure

```
digital_signage_toolkit/
+-- core/           # Business logic (system ops, installers, watchdog)
+-- gui/            # PyQt6 GUI components & tabs
+-- utils/          # Utilities (config, logging, validation)
+-- monitoring/     # Ansible and Zabbix files
tests/              # Unit tests
scripts/            # Build and install scripts
debian/             # Debian packaging
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DEBUG=true` | Enable console debug logging |
| `DST_CONFIG_PATH` | Custom config file path |
| `DST_SMTP_PASSWORD` | SMTP password (avoid storing in config) |
| `DST_SYSLOG_ENABLED` | Enable syslog forwarding |
| `DST_SYSLOG_ADDRESS` | Syslog address (default: /dev/log) |
