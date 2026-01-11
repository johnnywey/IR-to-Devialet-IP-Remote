# Devialet Phantom IR Bridge

This service bridges IR signals from an Apple TV Siri Remote (or any IR remote) to control Devialet Phantom speakers over the network.

## Hardware Requirements
- Raspberry Pi 4 Model B (or similar)
- TSOP38238 IR Receiver connected to GPIO 17

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url> devialet-pi-remote
    cd devialet-pi-remote
    ```

2.  **Enable IR Overlay:**
    Add the following to `/boot/firmware/config.txt` and reboot:
    ```
    dtoverlay=gpio-ir,gpio_pin=17
    ```

3.  **Setup Environment:**
    ```bash
    ./setup_env.sh
    ```

4.  **Configure IR Codes:**
    Run the diagnostic tool to learn your remote's codes:
    ```bash
    source venv/bin/activate
    python diagnostics.py
    ```
    
    Copy the example configuration:
    ```bash
    cp config.yaml.example config.yaml
    ```
    Update `config.yaml` with the captured hex codes.

5.  **Install Service:**
    ```bash
    sudo cp service/phantom-bridge.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable phantom-bridge
    sudo systemctl start phantom-bridge
    ```

## Compatibility & Known Issues

### Firmware 3.x Support
- **Mute Functionality:** Devialet Firmware 3.x (DOS 3) no longer supports the standard Mute API endpoints. This bridge implements a "Soft Mute" workaround: 
  - **Mute:** Sets volume to 0.
  - **Unmute:** Restores the previous volume level.
- **Stereo Pairs:** You **must** control the "System Leader" (typically the Left speaker). 
  - The bridge automatically validates connection candidates and will reject "Follower" speakers.
  - If using a static IP in `config.yaml`, ensure it is the IP of the System Leader.
  - If discovery fails, try restarting the speakers to refresh mDNS announcements.

## Troubleshooting
- **Check logs:** `sudo journalctl -u phantom-bridge -f`
- **Verify IR:** 
  1. Stop service: `sudo systemctl stop phantom-bridge`
  2. Run python diagnostics: `python diagnostics.py`
  3. **No codes?** Run the advanced debugger: `./debug_ir.sh`
     - This will enable ALL protocols (NEC, RC-6, etc.) to ensure your remote is detected.
     - If `debug_ir.sh` shows codes but `diagnostics.py` doesn't, your remote uses a protocol not enabled by default. Add the protocol line to `/etc/rc.local` (e.g., `ir-keytable -p nec`).
- **Manual Control:** Run `python manual_control.py` to test network control without IR. 
  - Use `v` to check volume, `m` to mute, `u` to unmute.
  - This tool also enforces the System Leader check, helping you identify the correct IP.
- **SystemLeaderAbsent Error:** If you see this in logs, it means the bridge is trying to talk to a Follower speaker. 
  - Ensure `devialet_client.py` is using the auto-discovery or that your static IP is correct.

