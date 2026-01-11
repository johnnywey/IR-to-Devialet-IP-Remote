"""
Manual verification tool for simple network testing.

Allows sending volume and mute commands to the speaker via the terminal
to verify that the DevialetClient logic and network connectivity are working
correctly, bypassing the IR hardware.
"""
import asyncio
import logging
import yaml
import sys
import tty
import termios
from devialet_client import DevialetClient

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ManualControl")

async def main():
    """
    Interactive command loop.
    
    Discovers the speaker and accepts keypress commands to control volume.
    """
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: config.yaml not found.")
        return

    client = DevialetClient(config)
    print("------------------------------------------------")
    print("Starting Devialet Discovery...")
    print("------------------------------------------------")
    
    volume_step = config.get("speaker", {}).get("volume_step", 2)
    
    # Start discovery in background
    asyncio.create_task(client.start())
    
    print("Waiting for speaker connection (System Leader)...")
    await client.discovery_event.wait()
    
    # We found the leader
    print(f"Connected to verified System Leader at {client.speaker_ip}")
    await client.get_volume()
    
    print("\nControls:")
    print("  + : Volume Up")
    print("  - : Volume Down")
    print("  m : Mute (set vol 0)")
    print("  u : Unmute (restore vol)")
    print("  v : Get Current Volume")
    print("  q : Quit")

    loop = asyncio.get_running_loop()
    # Set stdin to non-blocking
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        
        while True:
            # Simple async input reading
            key = await loop.run_in_executor(None, sys.stdin.read, 1)
            
            if key == 'q':
                break
            elif key == '+':
                print("\nVolume Up")
                current = await client.get_volume()
                await client.set_volume(current + volume_step)
                # Show new volume
                new_vol = await client.get_volume()
                print(f"Volume: {new_vol}")
            elif key == '-':
                print("\nVolume Down")
                current = await client.get_volume()
                await client.set_volume(current - volume_step)
                new_vol = await client.get_volume()
                print(f"Volume: {new_vol}")
            elif key == 'v':
                print("\ncheck volume...")
                vol = await client.get_volume()
                print(f"Current Volume: {vol}")
            elif key == 'm':
                print("\nMuting...")
                await client.set_mute(True)
            elif key == 'u':
                print("\nUnmuting...")
                await client.set_mute(False)
            else:
                print("\nUnknown command.")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        await client.close()
        print("\nExiting.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
