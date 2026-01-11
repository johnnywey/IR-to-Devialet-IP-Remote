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

# Check for ir-keytable
if ! command -v ir-keytable &> /dev/null; then
    echo -e "${RED}Error: ir-keytable not found.${NC}"
    echo "It is required to analyze IR signals and change protocols."
    echo ""
    echo -e "Install it with: ${GREEN}sudo apt-get install ir-keytable${NC}"
    echo " (On some systems, it might be part of v4l-utils)"
    exit 1
fi

echo -e "Scanning for IR receiver..."

# 1. Try to find the RC device for gpio_ir_recv by parsing ir-keytable output
# Expected: "Found /sys/class/rc/rcX/ with:" ... "Name: gpio_ir_recv"
RAW_LINE=$(ir-keytable 2>&1 | grep -B 1 "Name: gpio_ir_recv" | head -n 1)
RC_DEV_PATH=$(echo "$RAW_LINE" | awk '{print $2}')
RC_DEV=$(basename "$RC_DEV_PATH")

# 2. Fallback to SysFS if parsing failed
if [ -z "$RC_DEV" ] || [ "$RC_DEV" == "/" ]; then
    RC_NAME_FILE=$(grep -l "gpio_ir_recv" /sys/class/rc/rc*/name 2>/dev/null | head -n 1)
    if [ -n "$RC_NAME_FILE" ]; then
        RC_DIR=$(dirname "$RC_NAME_FILE")
        RC_DEV=$(basename "$RC_DIR")
    fi
fi

if [ -n "$RC_DEV" ] && [ "$RC_DEV" != "/" ]; then
    echo -e "${GREEN}Found 'gpio_ir_recv' on device: $RC_DEV${NC}"
    echo "Enabling all protocols to test reception..."
    sudo ir-keytable -s "$RC_DEV" -p all
else
    echo -e "${RED}Warning: Could not automatically detect 'gpio_ir_recv' device.${NC}"
    echo "Attempting to enable 'all' protocols on default device (this may fail if HDMI CEC is present)..."
    sudo ir-keytable -p all
fi

echo -e "\n${YELLOW}Starting signal test...${NC}"
echo "------------------------------------------------"
echo "1. Point your remote at the receiver."
echo "2. Press buttons."
echo -e "3. Look for ${GREEN}scancode${NC} lines below."
echo "------------------------------------------------"
echo "Press Ctrl+C to exit."

if [ -n "$RC_DEV" ] && [ "$RC_DEV" != "/" ]; then
    sudo ir-keytable -s "$RC_DEV" -t
else
    sudo ir-keytable -t
fi
