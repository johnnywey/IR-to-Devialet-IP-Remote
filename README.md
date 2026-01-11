# Devialet Phantom IR Bridge

This service bridges IR signals from an Apple TV Siri Remote (or any IR remote) to control Devialet Phantom speakers over the network.

## Hardware Requirements
- Raspberry Pi 4 Model B (or similar)
- TSOP38238 IR Receiver connected to GPIO 17

## Installation Guide

### 1. Enable IR Support
You need to tell the Raspberry Pi kernel to use the GPIO pin for IR reception.

1.  Edit the boot configuration file:
    ```bash
    sudo nano /boot/firmware/config.txt
    ```
    *(Note: On older Raspberry Pi OS versions, this might be `/boot/config.txt`)*

2.  Add the following line to the end of the file:
    ```
    dtoverlay=gpio-ir,gpio_pin=17
    ```
    *(Ensure your IR receiver is connected to GPIO 17. Change the pin number if different.)*

3.  Reboot the Pi:
    ```bash
    sudo reboot
    ```

### 2. Install the Software

1.  **Clone the repository:**
    ```bash
    cd /home/pi
    git clone https://github.com/johnnywey/IR-to-Devialet-IP-Remote.git 
    cd devialet-pi-remote
    ```

2.  **Run the setup script:**
    This script creates a Python virtual environment and installs the required libraries.
    ```bash
    chmod +x setup_env.sh
    ./setup_env.sh
    ```
    *(Note: This script skips compiling `zeroconf` extensions to avoid hanging on Raspberry Pi. If installing manually, use `SKIP_CYTHON=y pip install zeroconf`)*

### 3. Configure the Application

1.  **Create the configuration file:**
    ```bash
    cp config.yaml.example config.yaml
    ```

2.  **Capture your remote codes:**
    Stop the service if it's already running.
    ```bash
    # Activate venv first
    source venv/bin/activate
    python diagnostics.py
    ```
    Press buttons on your remote and note the `scan_code` or `key_code` that appears. Update `config.yaml` with these codes using `nano config.yaml`.

    **Important:** If `diagnostics.py` shows nothing, run the advanced debugger:
    ```bash
    ./debug_ir.sh
    ```
    If `debug_ir.sh` works but `diagnostics.py` doesn't, see step 5 ("Persisting IR Protocol").

3.  **Advanced Configuration:**
    You can also configure `volume_step` (how much the volume changes) and `debounce_ms` (how long to ignore duplicate signals) in `config.yaml`.

### 4. Set up Auto-Start (Systemd Service)

1.  **Install the Service:**
    ```bash
    sudo cp service/phantom-bridge.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable phantom-bridge
    sudo systemctl start phantom-bridge
    ```

2.  **Check Status:**
    ```bash
    sudo systemctl status phantom-bridge
    # Live logs
    sudo journalctl -u phantom-bridge -f
    ```

### 5. Persisting IR Protocol (Reliable Method)

If your remote works with `debug_ir.sh` (which enables all protocols) but not by default (e.g., standard NEC remotes), you need to explicitly enable these protocols at boot. We provide a helper service for this.

1.  **Install the Protocol Service:**
    ```bash
    # Install helper script
    sudo cp service/enable_ir.sh /usr/local/bin/
    sudo chmod +x /usr/local/bin/enable_ir.sh

    # Install service
    sudo cp service/enable-ir-protocols.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable enable-ir-protocols
    sudo systemctl start enable-ir-protocols
    ```

    *This ensures that our robust detection script runs every time the Pi boots, finding the correct IR device and enabling all protocols.*

### 6. Troubleshooting Permissions

If the service fails with "Permission denied" errors related to accessing `/dev/input`, ensure the `pi` user is in the `input` group:

```bash
sudo usermod -a -G input pi
sudo systemctl restart phantom-bridge
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
