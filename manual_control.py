import asyncio
import logging
import yaml
import sys
from devialet_client import DevialetClient

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ManualControl")

async def main():
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
    
    # Start discovery in background
    asyncio.create_task(client.start())
    
    print("Waiting for speaker connection...")
    if await client.check_connection() or await client.get_volume(): # This will block until discovered
         print(f"Connected to speaker at {client.speaker_ip}")
    
    print("\nControls:")
    print("  + : Volume Up")
    print("  - : Volume Down")
    print("  m : Toggle Mute (sends mute=True)")
    print("  v : Get Current Volume")
    print("  q : Quit")
    
    while True:
        try:
            cmd = await asyncio.get_event_loop().run_in_executor(None, input, "\nCommand: ")
            cmd = cmd.strip().lower()
            
            if cmd == 'q':
                break
            
            elif cmd == 'v':
                vol = await client.get_volume()
                print(f"Current Volume: {vol}")
            
            elif cmd == '+':
                curr = await client.get_volume()
                new_vol = curr + config.get('speaker', {}).get('volume_step', 2)
                print(f"Setting volume to {new_vol}...")
                await client.set_volume(new_vol)
                
            elif cmd == '-':
                curr = await client.get_volume()
                new_vol = curr - config.get('speaker', {}).get('volume_step', 2)
                print(f"Setting volume to {new_vol}...")
                await client.set_volume(new_vol)
                
            elif cmd == 'm':
                print("Sending Mute command...")
                await client.set_mute(True)
                
            else:
                print("Unknown command.")
                
        except Exception as e:
            print(f"Error: {e}")
            
    await client.close()
    print("Exiting.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
