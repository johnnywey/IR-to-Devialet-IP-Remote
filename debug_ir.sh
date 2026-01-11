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

# Find the RC device for gpio_ir_recv
# Output format: "Found /sys/class/rc/rc2/ with:"
RC_DEV_PATH=$(ir-keytable 2>/dev/null | grep -B 1 "gpio_ir_recv" | head -n 1 | awk '{print $2}')
RC_DEV=$(basename "$RC_DEV_PATH")

if [ -z "$RC_DEV" ] || [ "$RC_DEV" == "/" ]; then
    echo -e "${RED}Error: Could not automatically find gpio_ir_recv device.${NC}"
    echo "Trying default 'all'..."
    sudo ir-keytable -p all
else
    echo -e "\n${YELLOW}Detected IR device at $RC_DEV. Enabling ALL protocols on it...${NC}"
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
