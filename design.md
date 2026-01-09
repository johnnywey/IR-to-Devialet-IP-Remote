# PRD: Siri Remote to Devialet Phantom IR-Network Bridge

## 1. Preamble for the Developer Agent

> **Developer Note:** You are tasked with building a robust, headless Python 3.11+ service for a Raspberry Pi 4B.
> * **Simplicity:** Favor clear, readable code using standard libraries (`asyncio`, `httpx`, `evdev`, `zeroconf`).
> * **Self-Documentation:** Provide meaningful comments for non-obvious logic, especially regarding IR signal debouncing and mDNS recovery.
> * **Resilience:** The service must be "set and forget." It must automatically handle network drops, speaker reboots, and IP re-assignments without human intervention.
> * **Verification:** Include a simple test suite or a mock class to verify the mapping of IR scancodes to HTTP requests.
> 
> 

---

## 2. Environment & Hardware Preparation

**Target Hardware:** Raspberry Pi 4 Model B

**OS:** Raspberry Pi OS Lite (64-bit)

### A. Initial Setup Steps

The user will follow these steps to prep the hardware:

1. **OS Flash:** Use Raspberry Pi Imager to install OS Lite. Enable SSH and WiFi in the customization menu.
2. **Hardware Connectivity:** Connect a **TSOP38238** IR receiver:
* **Pin 1 (Data/OUT):** GPIO 17 (Physical Pin 11)
* **Pin 2 (GND):** Ground (Physical Pin 6)
* **Pin 3 (VCC):** 3.3V Power (Physical Pin 1)


3. **Enable IR Driver:**
```bash
echo "dtoverlay=gpio-ir,gpio_pin=17" | sudo tee -a /boot/firmware/config.txt
sudo reboot

```



---

## 3. Technical Specifications

### A. Diagnostic Scancode Grabber

Provide a `diagnostics.py` script to identify the specific IR signatures of the user's Siri Remote:

```python
import evdev
from evdev import ecodes

def main():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    ir_dev = next((d for d in devices if "gpio" in d.name.lower()), None)
    if not ir_dev:
        return print("Error: IR receiver not found. Check /boot/firmware/config.txt")
    
    print(f"Listening on {ir_dev.path}. Press remote buttons...")
    for event in ir_dev.read_loop():
        if event.type == ecodes.EV_MSC and event.code == ecodes.MSC_SCAN:
            print(f"RAW SCANCODE: {hex(event.value)}")

if __name__ == "__main__":
    main()

```

### B. Devialet DOS2 API Reference

The bridge must target the **Master** speaker's IP on port 80.

| Feature | Method | Endpoint | Payload / Response |
| --- | --- | --- | --- |
| **Get Volume** | `GET` | `/ipcontrol/v1/systems/current/sources/current/soundControl/volume` | `{"volume": <0-100>}` |
| **Set Volume** | `POST` | `/ipcontrol/v1/systems/current/sources/current/soundControl/volume` | `{"volume": <int>}` |
| **Mute/Unmute** | `POST` | `/ipcontrol/v1/systems/current/sources/current/soundControl/mute` | `{"muted": bool}` |

### C. Logical Requirements

1. **State Initialization:** On startup, the service must perform a `GET` request to retrieve the current volume. If the speaker is unavailable, the service enters a "Discovery Mode."
2. **mDNS Discovery:** Use `zeroconf` to locate the speaker. In a stereo pair, the speaker that returns `isMaster: true` in its system info is the primary target.
3. **Debouncing:** Implement a **100ms debounce** window for volume repeats.
4. **Self-Healing:** If any HTTP request fails, the service must invalidate the current IP and restart mDNS discovery.

---

## 4. Configuration & Deployment

### `config.yaml` Template

```yaml
speaker:
  name: "Phantom" # mDNS search string
  volume_step: 2
  static_ip: null # Optional override

ir_codes:
  0x87ee01: "volume_up"
  0x87ee02: "volume_down"
  0x87ee03: "mute"

```

### `systemd` Service (`/etc/systemd/system/phantom-bridge.service`)

```ini
[Unit]
Description=Siri Remote to Devialet Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/python3 /home/pi/phantom-bridge/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

```
