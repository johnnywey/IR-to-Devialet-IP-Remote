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

## Troubleshooting
- **Check logs:** `sudo journalctl -u phantom-bridge -f`
- **Verify IR:** Run `diagnostics.py` (stop service first: `sudo systemctl stop phantom-bridge`).
