#!/bin/bash
set -e

# colorful output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}------------------------------------------------${NC}"
echo -e "${YELLOW}           IR Troubleshooting Tool              ${NC}"
echo -e "${YELLOW}------------------------------------------------${NC}"

# Enable verbose debugging to see exactly what happens
set -x

echo -e "\nChecking for /dev/lirc devices..."
ls -l /dev/lirc* 2>/dev/null || echo "Request: No /dev/lirc* devices found."

echo -e "\nChecking kernel logs for gpio-ir..."
dmesg | grep -i "gpio-ir" | tail -n 5 || echo "No kernel logs found."

# Check for ir-keytable
if ! command -v ir-keytable &> /dev/null; then
    set +x
    echo -e "${RED}Error: ir-keytable not found.${NC}"
    echo "It is required to change IR protocols."
    echo ""
    echo -e "Install it with: ${GREEN}sudo apt-get install ir-keytable${NC}"
    echo " (On some systems, it might be part of v4l-utils, but usually it's a separate package)"
    exit 1
fi

set +x
echo -e "Current Protocol Configuration:"
ir-keytable
set -x

# Find the RC device for gpio_ir_recv by parsing ir-keytable output
echo -e "\nScanning ir-keytable output for gpio_ir_recv..."

# Capture the raw line
# Expected: "Found /sys/class/rc/rcX/ with:"
# We grep for "Name: gpio_ir_recv" and get the line before it
RAW_LINE=$(ir-keytable 2>&1 | grep -B 1 "Name: gpio_ir_recv" | head -n 1)
echo "Debug: Raw line found -> '$RAW_LINE'"

# Extract the path (2nd word)
RC_DEV_PATH=$(echo "$RAW_LINE" | awk '{print $2}')
echo "Debug: Extracted path -> '$RC_DEV_PATH'"

# Extract basename rcX
RC_DEV=$(basename "$RC_DEV_PATH")
echo "Debug: Resolved device -> '$RC_DEV'"

if [ -z "$RC_DEV" ] || [ "$RC_DEV" == "/" ]; then
    set +x
    echo -e "${RED}Error: Could not extract device name.${NC}"
    # Fallback to trying to find it via sysfs manually if parsing failed
    echo "Attempting SysFS fallback..."
    RC_NAME_FILE=$(grep -l "gpio_ir_recv" /sys/class/rc/rc*/name 2>/dev/null | head -n 1)
    if [ -n "$RC_NAME_FILE" ]; then
        RC_DIR=$(dirname "$RC_NAME_FILE")
        RC_DEV=$(basename "$RC_DIR")
        echo "SysFS found: $RC_DEV"
    fi
    set -x
else
    set +x
    echo -e "\n${YELLOW}Targeting device: $RC_DEV${NC}"
    set -x
fi

if [ -z "$RC_DEV" ]; then
    echo "Could not find device. Trying 'all' (might fail on HDMI)..."
    sudo ir-keytable -p all
else
    echo "Enabling all protocols on $RC_DEV..."
    sudo ir-keytable -s "$RC_DEV" -p all
fi

set +x
echo -e "\n${YELLOW}Starting signal test...${NC}"
echo "Point your remote at the receiver and press buttons."
echo "If you see events below (EV_MSC, EV_KEY, etc.), your hardware is working!"
echo "Press Ctrl+C to exit."
echo "------------------------------------------------"

if [ -z "$RC_DEV" ]; then
    sudo ir-keytable -t
else
    sudo ir-keytable -s "$RC_DEV" -t
fi
