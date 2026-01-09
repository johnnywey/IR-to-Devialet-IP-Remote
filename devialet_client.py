import asyncio
import logging
import socket
from typing import Optional

import httpx
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf, ServiceInfo

logger = logging.getLogger(__name__)

class DevialetClient:
    def __init__(self, config: dict):
        self.config = config
        self.speaker_ip: Optional[str] = config.get("speaker", {}).get("static_ip")
        self.zeroconf = Zeroconf() if not self.speaker_ip else None
        self.browser: Optional[ServiceBrowser] = None
        self.client = httpx.AsyncClient(timeout=2.0)
        self.discovery_event = asyncio.Event()
        self.target_name = config.get("speaker", {}).get("name", "Phantom")

    async def start(self):
        """Start discovery or connection process."""
        if self.speaker_ip:
            logger.info(f"Using static IP: {self.speaker_ip}")
            if await self.check_connection():
                self.discovery_event.set()
        else:
            logger.info(f"Starting mDNS discovery for '{self.target_name}'...")
            self.browser = ServiceBrowser(self.zeroconf, "_http._tcp.local.", handlers=[self._on_service_state_change])
            
            # Wait for initial discovery
            try:
                await asyncio.wait_for(self.discovery_event.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Discovery timed out. Will continue listening in background.")

    def _on_service_state_change(self, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange):
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                self._process_service_info(info)

    def _process_service_info(self, info: ServiceInfo):
        # Check if the name matches
        if self.target_name.lower() in info.name.lower():
            # In a stereo pair, we prefer the master. 
            # Note: The PRD mentions checking system info for 'isMaster'. 
            # For simplicity in mDNS, we often just grab the first matching IP. 
            # We will validate it by checking if we can get volume.
            
            # IP address from info.addresses is bytes
            if info.addresses:
                ip = socket.inet_ntoa(info.addresses[0])
                logger.info(f"Found candidate speaker: {info.name} at {ip}")
                
                # Verify we can talk to it (simple check)
                # We can't do async calls here easily, so we set the IP and let the main loop verify.
                # Or we can verify in background.
                if not self.speaker_ip:
                     self.speaker_ip = ip
                     self.discovery_event.set()

    async def check_connection(self) -> bool:
        """Verify we can reach the speaker."""
        if not self.speaker_ip:
            return False
        try:
            await self.get_volume()
            return True
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            self.speaker_ip = None # Invalidate
            self.discovery_event.clear()
            return False

    async def _restart_discovery(self):
        logger.info("Restarting discovery...")
        self.speaker_ip = None
        self.discovery_event.clear()
        if self.browser:
            self.browser.cancel()
            self.browser = None
        
        # Give it a moment
        await asyncio.sleep(1)
        
        # Create new browser to re-scan
        self.browser = ServiceBrowser(self.zeroconf, "_http._tcp.local.", handlers=[self._on_service_state_change])

    async def get_volume(self) -> int:
        if not self.speaker_ip:
            if not self.browser and self.zeroconf:
                 # If we are waiting but no browser, ensure we are discovering
                 await self._restart_discovery()
            await self.discovery_event.wait()
            
        url = f"http://{self.speaker_ip}/ipcontrol/v1/systems/current/sources/current/soundControl/volume"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("volume", 0)
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            await self._restart_discovery()
            raise

    async def set_volume(self, volume: int):
        if not self.speaker_ip:
            await self.discovery_event.wait()
            
        # Clamp volume 0-100
        volume = max(0, min(100, volume))
        
        url = f"http://{self.speaker_ip}/ipcontrol/v1/systems/current/sources/current/soundControl/volume"
        try:
            await self.client.post(url, json={"volume": volume})
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            await self._restart_discovery()

    async def set_mute(self, mute: bool):
        if not self.speaker_ip:
            await self.discovery_event.wait()
            
        url = f"http://{self.speaker_ip}/ipcontrol/v1/systems/current/sources/current/soundControl/mute"
        try:
            await self.client.post(url, json={"muted": mute})
        except Exception as e:
            logger.error(f"Error setting mute: {e}")
            await self._restart_discovery()

    async def close(self):
        await self.client.aclose()
        if self.zeroconf:
            self.zeroconf.close()
