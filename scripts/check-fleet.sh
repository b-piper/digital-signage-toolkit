#!/bin/bash
# Digital Signage Toolkit - Fleet Status Check
# Queries the /health endpoint on all kiosks and prints a summary table.
#
# Usage:
#   ./scripts/check-fleet.sh
#   ./scripts/check-fleet.sh /path/to/hosts.txt
#
# Hosts file format (one IP per line, # for comments):
#   192.168.1.101
#   192.168.1.102
#   # offline kiosk
#   # 192.168.1.103

set -euo pipefail

# Default locations for host list
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_HOSTS_FILE="${SCRIPT_DIR}/../monitoring/ansible/inventory/hosts.ini"
HOSTS_FILE="${1:-$DEFAULT_HOSTS_FILE}"

# Config
TIMEOUT=5
API_TOKEN="${DST_API_TOKEN:-}"
AUTH_HEADER=""
if [ -n "$API_TOKEN" ]; then
    AUTH_HEADER="-H \"X-Auth-Token: ${API_TOKEN}\""
fi
HEALTH_PORT="${DST_HEALTH_PORT:-8080}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Parse IPs from hosts file (supports INI and plain text formats)
get_hosts() {
    if [ ! -f "$HOSTS_FILE" ]; then
        echo "ERROR: Hosts file not found: $HOSTS_FILE" >&2
        echo "Usage: $0 [hosts-file]" >&2
        exit 1
    fi

    # Extract IPs: skip comments, section headers, empty lines, and ansible vars
    grep -E '^\s*[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' "$HOSTS_FILE" | \
        awk '{print $1}' | \
        sort -t. -k1,1n -k2,2n -k3,3n -k4,4n
}

# Print table header
print_header() {
    printf "\n${BOLD}%-18s %-20s %-12s %-10s %-10s %-10s${NC}\n" \
        "IP ADDRESS" "HOSTNAME" "RISE VISION" "DISK" "MEMORY" "STATUS"
    printf '%.0s─' {1..82}
    printf '\n'
}

# Query a single kiosk
check_kiosk() {
    local ip="$1"
    local response

    # Build curl command
    local curl_cmd="curl -sSL --connect-timeout ${TIMEOUT} --max-time $((TIMEOUT * 2))"
    if [ -n "$API_TOKEN" ]; then
        curl_cmd="$curl_cmd -H 'X-Auth-Token: ${API_TOKEN}'"
    fi
    curl_cmd="$curl_cmd http://${ip}:${HEALTH_PORT}/health"

    response=$(eval "$curl_cmd" 2>/dev/null) || response=""

    if [ -z "$response" ]; then
        printf "${RED}%-18s %-20s %-12s %-10s %-10s %-10s${NC}\n" \
            "$ip" "UNREACHABLE" "-" "-" "-" "OFFLINE"
        return
    fi

    # Parse JSON with python (available on all target systems)
    local parsed
    parsed=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    hostname = d.get('hostname', 'unknown')
    healthy = d.get('healthy', False)
    checks = d.get('checks', {})
    rise = checks.get('rise_vision', {}).get('status', 'unknown')
    disk_pct = checks.get('disk', {}).get('percent', 0)
    mem_pct = checks.get('memory', {}).get('percent', 0)
    status = 'HEALTHY' if healthy else 'UNHEALTHY'
    print(f'{hostname}|{rise}|{disk_pct}|{mem_pct}|{status}')
except Exception as e:
    print(f'unknown|error|0|0|PARSE_ERROR')
" <<< "$response" 2>/dev/null) || parsed="unknown|error|0|0|PARSE_ERROR"

    IFS='|' read -r hostname rise disk mem status <<< "$parsed"

    # Color coding
    local status_color="${GREEN}"
    if [ "$status" = "UNHEALTHY" ]; then
        status_color="${RED}"
    elif [ "$status" = "PARSE_ERROR" ]; then
        status_color="${YELLOW}"
    fi

    local rise_color="${GREEN}"
    if [ "$rise" != "running" ]; then
        rise_color="${RED}"
    fi

    local disk_color="${GREEN}"
    if (( $(echo "$disk > 90" | bc -l 2>/dev/null || echo 0) )); then
        disk_color="${RED}"
    elif (( $(echo "$disk > 80" | bc -l 2>/dev/null || echo 0) )); then
        disk_color="${YELLOW}"
    fi

    printf "%-18s %-20s ${rise_color}%-12s${NC} ${disk_color}%-10s${NC} %-10s ${status_color}%-10s${NC}\n" \
        "$ip" "$hostname" "$rise" "${disk}%" "${mem}%" "$status"
}

# Main
echo ""
echo "${BOLD}Digital Signage Toolkit — Fleet Status${NC}"
echo "Hosts file: ${HOSTS_FILE}"
echo "Health port: ${HEALTH_PORT}"

HOSTS=$(get_hosts)
HOST_COUNT=$(echo "$HOSTS" | wc -l)
echo "Checking ${HOST_COUNT} kiosk(s)..."

print_header

HEALTHY=0
UNHEALTHY=0
OFFLINE=0

while IFS= read -r ip; do
    result=$(check_kiosk "$ip")
    echo "$result"

    if echo "$result" | grep -q "HEALTHY"; then
        ((HEALTHY++))
    elif echo "$result" | grep -q "OFFLINE"; then
        ((OFFLINE++))
    else
        ((UNHEALTHY++))
    fi
done <<< "$HOSTS"

# Summary
printf '%.0s─' {1..82}
printf '\n'
printf "${BOLD}Summary:${NC} ${GREEN}${HEALTHY} healthy${NC} | ${RED}${UNHEALTHY} unhealthy${NC} | ${YELLOW}${OFFLINE} offline${NC} | ${HOST_COUNT} total\n\n"
