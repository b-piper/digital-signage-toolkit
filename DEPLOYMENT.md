# Deployment Guide

## Quick Install (After GitHub Setup)

```bash
curl -sSL https://raw.githubusercontent.com/b-piper/digital-signage-toolkit/main/install-remote.sh | sudo bash
```

## Manual Install

Download the latest `.deb` from [Releases](https://github.com/b-piper/digital-signage-toolkit/releases) and install:

```bash
sudo apt install ./dst-toolkit_X.X.X_amd64.deb
```

## Creating a Release

1. **Update version** in `utils/config.py` (in `_default_config`)
2. **Commit changes**: `git add . && git commit -m "Release v2.1.0"`
3. **Tag the release**: `git tag v2.1.0`
4. **Push with tags**: `git push origin main --tags`

GitHub Actions will automatically build and publish the `.deb` package.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DST_CONFIG_PATH` | Custom config file location |
| `DST_SMTP_PASSWORD` | SMTP password (avoid storing in config) |
| `DST_SYSLOG_ENABLED` | Enable syslog forwarding (`true`/`false`) |
| `DST_SYSLOG_ADDRESS` | Syslog address (default: `/dev/log`) |

## Updating Kiosks

```bash
# Pull latest and reinstall
curl -sSL https://raw.githubusercontent.com/b-piper/digital-signage-toolkit/main/install-remote.sh | sudo bash
```

Or if using apt repository:
```bash
sudo apt update && sudo apt upgrade dst-toolkit
```
