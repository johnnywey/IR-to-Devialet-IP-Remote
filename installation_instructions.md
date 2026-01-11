# Devialet Pi Remote Installation Guide

Follow these instructions to install the bridge on your Raspberry Pi and configure it to start automatically on boot.

## 1. Prepare the Raspberry Pi

### Enable IR Support
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

## 2. Install the Software

1.  **Clone the repository** (if you haven't already extracted it there):
    ```bash
    cd /home/pi
    git clone https://github.com/johnnywey/IR-to-Devialet-IP-Remote.git 
    cd devialet-pi-remote
    ```
    *(If you copied the files manually, just `cd` into the directory)*

2.  **Run the setup script**:
    This script creates a Python virtual environment and installs the required libraries.
    ```bash
    chmod +x setup_env.sh
    ./setup_env.sh
    ```
    *(Note: This script now skips compiling `zeroconf` extensions to avoid hanging on Raspberry Pi. If you install manually, use `SKIP_CYTHON=y pip install zeroconf`)*

## 3. Configure the Application

1.  **Create the configuration file**:
    ```bash
    cp config.yaml.example config.yaml
    ```

2.  **Capture your remote codes**:
    Stop the service if it's already running, then run the diagnostic tool to see the codes your remote sends.
    ```bash
    # Activate venv first
    source venv/bin/activate
    python diagnostics.py
    ```
    Press buttons on your remote and note the `scan_code` or `key_code` that appears.
    Update `config.yaml` with these codes using `nano config.yaml`.

## 4. Set up Auto-Start (Systemd Service)

We will use `systemd` to keep the service running in the background and start it on boot.

1.  **Verify the Service File**:
    Check the `service/phantom-bridge.service` file. It assumes:
    - User is `pi`
    - Code is located at `/home/pi/devialet-pi-remote`

    If your setup is different, edit the file first:
    ```bash
    nano service/phantom-bridge.service
    ```
    Update `User`, `WorkingDirectory`, and `ExecStart` paths if needed.

2.  **Install the Service**:
    ```bash
    sudo cp service/phantom-bridge.service /etc/systemd/system/
    ```

3.  **Enable and Start**:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable phantom-bridge
    sudo systemctl start phantom-bridge
    ```

4.  **Check Status**:
    To manually check if it's running correctly:
    ```bash
    sudo systemctl status phantom-bridge
    ```

    To see live logs:
    ```bash
    sudo journalctl -u phantom-bridge -f
    ```

## 5. Troubleshooting Permissions

If the service fails with "Permission denied" errors related to accessing `/dev/input`, ensure the `pi` user is in the `input` group:

```bash
sudo usermod -a -G input pi
# formatting requires a logout/login or reboot to take effect for the current user session,
# but systemd services should pick it up on restart.
sudo systemctl restart phantom-bridge
```
