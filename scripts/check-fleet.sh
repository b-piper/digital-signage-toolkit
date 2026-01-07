#!/bin/bash
# Digital Signage Toolkit - Fleet Status Checker
# Run from any PC with network access to the kiosks
# Requires: curl, jq

set -e

# ============================================
# CONFIGURATION - Edit this section
# ============================================
# Add your kiosks here in format "name:ip"
KIOSKS=(
    "kiosk-library:192.168.1.101"
    "kiosk-cafeteria:192.168.1.102"
    "kiosk-gym:192.168.1.103"
    "kiosk-admin:192.168.1.104"
    "kiosk-main-entrance:192.168.1.105"
    # Add more kiosks as needed...
)

# Health check port (must match health_server.py)
HEALTH_PORT=8080

# Connection timeout in seconds
TIMEOUT=3

# ============================================
# Script Logic - Don't edit below this line
# ============================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "Warning: jq not installed. Install with: sudo apt install jq"
    echo "Falling back to basic output..."
    USE_JQ=false
else
    USE_JQ=true
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║           DIGITAL SIGNAGE TOOLKIT - FLEET STATUS                     ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  Time: $(date '+%Y-%m-%d %H:%M:%S')                                         ║"
echo "║  Kiosks: ${#KIOSKS[@]}                                                           ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Header
printf "%-25s %-10s %-12s %-10s %-10s %-10s\n" "KIOSK" "STATUS" "RISE VISION" "DISK" "MEMORY" "VERSION"
printf "%-25s %-10s %-12s %-10s %-10s %-10s\n" "-------------------------" "----------" "------------" "----------" "----------" "----------"

# Counters
ONLINE=0
OFFLINE=0
WARNINGS=0

for entry in "${KIOSKS[@]}"; do
    name="${entry%%:*}"
    ip="${entry##*:}"
    
    # Try to get health data
    response=$(curl -s --connect-timeout "$TIMEOUT" "http://${ip}:${HEALTH_PORT}/health" 2>/dev/null || echo "")
    
    if [ -z "$response" ]; then
        # Kiosk is offline
        printf "${RED}%-25s %-10s %-12s %-10s %-10s %-10s${NC}\n" "$name" "OFFLINE" "-" "-" "-" "-"
        ((OFFLINE++))
    else
        if [ "$USE_JQ" = true ]; then
            healthy=$(echo "$response" | jq -r '.healthy // false')
            rise=$(echo "$response" | jq -r '.checks.rise_vision.status // "unknown"')
            disk=$(echo "$response" | jq -r '.checks.disk.percent // 0')
            disk_warn=$(echo "$response" | jq -r '.checks.disk.warning // false')
            memory=$(echo "$response" | jq -r '.checks.memory.percent // 0')
            version=$(echo "$response" | jq -r '.version // "unknown"')
        else
            # Basic parsing without jq
            healthy="unknown"
            rise="unknown"
            disk="?"
            memory="?"
            version="?"
        fi
        
        # Determine status color
        if [ "$healthy" = "true" ]; then
            status="${GREEN}OK${NC}"
            ((ONLINE++))
        else
            status="${RED}WARNING${NC}"
            ((WARNINGS++))
            ((ONLINE++))
        fi
        
        # Disk warning
        if [ "$disk_warn" = "true" ]; then
            disk_display="${YELLOW}${disk}%${NC}"
        else
            disk_display="${disk}%"
        fi
        
        # Rise Vision status
        if [ "$rise" = "running" ]; then
            rise_display="${GREEN}running${NC}"
        else
            rise_display="${RED}${rise}${NC}"
        fi
        
        printf "%-25s %-10b %-12b %-10b %-10s %-10s\n" "$name" "$status" "$rise_display" "$disk_display" "${memory}%" "v$version"
    fi
done

echo ""
echo "────────────────────────────────────────────────────────────────────────"
printf "Summary: ${GREEN}Online: $ONLINE${NC} | ${RED}Offline: $OFFLINE${NC} | ${YELLOW}Warnings: $WARNINGS${NC}\n"
echo ""

# Exit with error if any offline
if [ $OFFLINE -gt 0 ]; then
    exit 1
fi
