#!/bin/bash
# robustly enable IR protocols for gpio_ir_recv

# Find the RC device for gpio_ir_recv
RC_DEV=""
# Loop through all rc devices in sysfs didn't work reliably.
# Using ir-keytable parsing which was proven to work.
RAW_LINE=$(/usr/bin/ir-keytable 2>&1 | grep -B 1 "Name: gpio_ir_recv" | head -n 1)
RC_DEV_PATH=$(echo "$RAW_LINE" | awk '{print $2}')
RC_DEV=$(basename "$RC_DEV_PATH")

if [ -n "$RC_DEV" ]; then
    echo "Found gpio_ir_recv at $RC_DEV. Enabling all protocols..."
    /usr/bin/ir-keytable -s "$RC_DEV" -p all
else
    echo "Could not find gpio_ir_recv. Trying default..."
    /usr/bin/ir-keytable -p all
fi
