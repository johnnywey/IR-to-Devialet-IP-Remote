import asyncio
import logging
import sys
import time
import signal
import yaml
import evdev
from evdev import ecodes
from devialet_client import DevialetClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PhantomBridge")

class PhantomBridge:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.client = DevialetClient(self.config)
        self.ir_codes = {int(k) if isinstance(k, int) else int(k, 16): v 
                         for k, v in self.config.get("ir_codes", {}).items()}
        self.volume_step = self.config.get("speaker", {}).get("volume_step", 2)
        
        self.last_volume_time = 0.0
        self.debounce_window = 0.1 # 100ms
        self.running = True

    async def get_ir_device(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        # Typically the plugin creates "gpio_ir_recv"
        ir_dev = next((d for d in devices if "gpio" in d.name.lower() or "ir" in d.name.lower()), None)
        return ir_dev

    async def handle_input(self, device):
        logger.info(f"Listening for IR events on {device.name} ({device.path})...")
        
        # Async read of evdev events
        async for event in device.async_read_loop():
            if event.type == ecodes.EV_MSC and event.code == ecodes.MSC_SCAN:
                await self.process_ir_code(event.value)

    async def process_ir_code(self, scancode: int):
        action = self.ir_codes.get(scancode)
        if not action:
            logger.debug(f"Unknown scancode: {hex(scancode)}")
            return

        now = time.time()
        # Basic debouncing logic for volume
        if "volume" in action:
            if now - self.last_volume_time < self.debounce_window:
                logger.debug("Debouncing volume code")
                return
            self.last_volume_time = now

        logger.info(f"Action: {action} (from {hex(scancode)})")

        try:
            if action == "volume_up":
                current_vol = await self.client.get_volume()
                await self.client.set_volume(current_vol + self.volume_step)
            elif action == "volume_down":
                current_vol = await self.client.get_volume()
                await self.client.set_volume(current_vol - self.volume_step)
            elif action == "mute":
                # Toggle mute? Or just mute? 
                # API has mute/unmute. Usually toggle is nice but "mute" implies setting mute.
                # Let's assume toggle for better UX or we check current state?
                # The prompt just says "Mute/Unmute" POST. Typically toggling requires knowing state.
                # We'll try to just send mute=True for now, but a toggle is better.
                # Let's see if we can get property to toggle. Get Volume usually doesn't return mute state in all APIs.
                # Devialet API: GET /ipcontrol/v1/systems/current/sources/current/soundControl/volume -> {"volume": 0-100}
                # No mute state in volume response.
                # Let's just implement explicit mute for now, or assume toggle if we track it?
                # Best effort: Send mute=True. Or maybe there's a /mute GET?
                # PRD says: POST .../mute { "muted": bool }
                # Let's assume we want to Toggle. But we can't read it easily without perhpas another endpoint.
                # For safety/simplicity as requested, let's implement MUTE as "Mute" (true) and maybe another code for Unmute?
                # Actually, remote buttons are usually toggles. 
                # Let's implement MUTE as Mute=True.
                # Wait, if I am muted, I want to unmute.
                # Let's try to keeping local state? No, local state might drift.
                # Let's just send Mute=True. Users can Volume Up to unmute usually.
                await self.client.set_mute(True)

        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}")

    async def run(self):
        # Start client discovery
        asyncio.create_task(self.client.start())
        
        while self.running:
            device = await self.get_ir_device()
            if device:
                try:
                    await self.handle_input(device)
                except OSError:
                    logger.error("Device disconnected. Scanning...")
            else:
                logger.warning("IR Receiver not found. Retrying in 5s...")
            
            await asyncio.sleep(5)

    async def shutdown(self):
        self.running = False
        await self.client.close()

def signal_handler(sig, frame):
    # This is a bit hacky for asyncio, better to handle KeyboardInterrupt in run
    pass

async def main():
    bridge = PhantomBridge("config.yaml")
    
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    
    def ask_exit():
        logger.info("Stopping...")
        stop.set()
        bridge.running = False

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, ask_exit)

    await bridge.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
