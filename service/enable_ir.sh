#!/bin/bash
# robustly enable IR protocols for gpio_ir_recv

# Find the RC device for gpio_ir_recv
RC_DEV=""
# Loop through all rc devices in sysfs
for f in /sys/class/rc/rc*/name; do
    if [ -f "$f" ]; then
        if grep -q "gpio_ir_recv" "$f"; then
            RC_DIR=$(dirname "$f")
            RC_DEV=$(basename "$RC_DIR")
            break
        fi
    fi
done

if [ -n "$RC_DEV" ]; then
    echo "Found gpio_ir_recv at $RC_DEV. Enabling all protocols..."
    /usr/bin/ir-keytable -s "$RC_DEV" -p all
else
    echo "Could not find gpio_ir_recv. Trying default..."
    /usr/bin/ir-keytable -p all
fi
