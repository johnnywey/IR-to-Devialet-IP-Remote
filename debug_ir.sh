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
    echo "It is required to change IR protocols."
    echo ""
    echo -e "Install it with: ${GREEN}sudo apt-get install ir-keytable${NC}"
    echo " (On some systems, it might be part of v4l-utils, but usually it's a separate package)"
    exit 1
fi

echo -e "Current Protocol Configuration:"
ir-keytable

echo -e "\n${YELLOW}Attempting to enable ALL protocols...${NC}"
sudo ir-keytable -p all

echo -e "\n${YELLOW}Starting signal test...${NC}"
echo "Point your remote at the receiver and press buttons."
echo "If you see events below (EV_MSC, EV_KEY, etc.), your hardware is working!"
echo "Press Ctrl+C to exit."
echo "------------------------------------------------"

sudo ir-keytable -t
