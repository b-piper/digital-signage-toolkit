#!/bin/bash
# Health check script for Digital Signage Toolkit
# Returns 0 if healthy, non-zero if unhealthy

EXIT_CODE=0

# Check if application is installed
if ! command -v digital-signage-toolkit &> /dev/null; then
    echo "ERROR: digital-signage-toolkit not found in PATH"
    EXIT_CODE=1
fi

# Check if Python dependencies are available
python3 -c "import PyQt6" 2>/dev/null || {
    echo "ERROR: PyQt6 not available"
    EXIT_CODE=1
}

python3 -c "import psutil" 2>/dev/null || {
    echo "ERROR: psutil not available"
    EXIT_CODE=1
}

# Check if log directory exists and is writable
LOG_DIR="/var/log/digital-signage-toolkit"
if [ -d "$LOG_DIR" ]; then
    if [ ! -w "$LOG_DIR" ]; then
        echo "WARNING: Log directory not writable: $LOG_DIR"
    fi
else
    echo "WARNING: Log directory does not exist: $LOG_DIR"
fi

# Check disk space (warn if less than 1GB free)
FREE_SPACE=$(df / | tail -1 | awk '{print $4}')
if [ "$FREE_SPACE" -lt 1048576 ]; then  # Less than 1GB in KB
    echo "WARNING: Low disk space: $(($FREE_SPACE / 1024))MB free"
fi

exit $EXIT_CODE




