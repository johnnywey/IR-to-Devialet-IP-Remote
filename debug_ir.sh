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

echo -e "\nChecking for /dev/lirc devices..."
ls -l /dev/lirc* 2>/dev/null || echo "Request: No /dev/lirc* devices found."

echo -e "\nChecking kernel logs for gpio-ir..."
dmesg | grep -i "gpio-ir" | tail -n 5 || echo "No kernel logs found."

# Check for ir-keytable
if ! command -v ir-keytable &> /dev/null; then
    echo -e "${RED}Error: ir-keytable not found.${NC}"
    echo "It is required to change IR protocols."
    echo ""
    echo -e "Install it with: ${GREEN}sudo apt-get install ir-keytable${NC}"
    echo " (On some systems, it might be part of v4l-utils, but usually it's a separate package)"
    exit 1
fi

echo -e "Current Protocol Configuration:"
ir-keytable

# Find the RC device for gpio_ir_recv using explicit loop
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
    echo -e "${RED}Error: Could not extract device name.${NC}"
else
    echo -e "\n${YELLOW}Targeting device: $RC_DEV${NC}"
fi

if [ -z "$RC_DEV" ]; then
    echo -e "${RED}Error: Could not automatically find gpio_ir_recv device.${NC}"
    echo "This is unexpected. Here are the available devices:"
    grep . /sys/class/rc/rc*/name 2>/dev/null
    
    echo "Trying default 'all'..."
    sudo ir-keytable -p all
else
    echo -e "\n${YELLOW}Detected IR device: $RC_DEV. Enabling ALL protocols on it...${NC}"
    sudo ir-keytable -s "$RC_DEV" -p all
fi


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
