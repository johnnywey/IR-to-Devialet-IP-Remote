"""
Diagnostic tool to identify IR remote codes.

This script scans for available input devices, identifies the likely IR receiver,
and then listens for input events, printing the hex and integer values of captured scancodes.
"""
import evdev
from evdev import ecodes
import sys

def main():
    """
    Main diagnostic loop.
    
    1. Lists input devices.
    2. Identifies IR receiver.
    3. Prints captured scancodes until interrupted.
    """
    print("Looking for IR receiver...")
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    
    # Try to find a device that looks like an IR receiver (usually has 'gpio' or 'ir' in name)
    # The default overlay usually creates a device named "gpio_ir_recv"
    ir_dev = next((d for d in devices if "gpio" in d.name.lower() or "ir" in d.name.lower()), None)
    
    if not ir_dev:
        print("\nERROR: IR receiver device not found.", file=sys.stderr)
        print("Please ensure you have configured the dtoverlay in /boot/firmware/config.txt:", file=sys.stderr)
        print("  dtoverlay=gpio-ir,gpio_pin=17", file=sys.stderr)
        print("\nAvailable devices:", file=sys.stderr)
        for d in devices:
            print(f"  - {d.path}: {d.name}", file=sys.stderr)
        return

    print(f"\nSUCCESS: Found IR device: {ir_dev.name} at {ir_dev.path}")
    print("----------------------------------------------------------------")
    print("Point your remote at the receiver and press buttons.")
    print("Press Ctrl+C to exit.")
    print("----------------------------------------------------------------")

    try:
        for event in ir_dev.read_loop():
            if event.type == ecodes.EV_MSC and event.code == ecodes.MSC_SCAN:
                # Value is the raw scancode
                scancode = event.value
                hex_code = hex(scancode)
                print(f"Captured Signal -> Hex: {hex_code} | Int: {scancode}")
    except KeyboardInterrupt:
        print("\nExiting.")
    except Exception as e:
        print(f"\nError reading device: {e}")

if __name__ == "__main__":
    main()
