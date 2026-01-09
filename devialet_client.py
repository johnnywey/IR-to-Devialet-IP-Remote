import asyncio
import logging
import socket
from typing import Optional

import httpx
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf, ServiceInfo

logger = logging.getLogger(__name__)

class DevialetClient:
    """
    Handles discovery and communication with Devialet Phantom speakers.
    
    Uses ZeroConf (mDNS) to locate speakers and HTTPX for API control.
    Supports self-healing by restarting discovery on connection failure.
    """
    def __init__(self, config: dict):
        self.config = config
        self.speaker_ip: Optional[str] = config.get("speaker", {}).get("static_ip")
        self.zeroconf = Zeroconf() if not self.speaker_ip else None
        self.browser: Optional[ServiceBrowser] = None
        self.client = httpx.AsyncClient(timeout=2.0)
        self.discovery_event = asyncio.Event()
        self.target_name = config.get("speaker", {}).get("name", "Phantom")

    async def start(self):
        """
        Start the discovery or connection process.
        
        If a static IP is configured, it attempts to verify connection immediately.
        Otherwise, it starts an mDNS ServiceBrowser to listen for `_http._tcp.local.` services.
        """
        # Capture the loop for thread-safe callbacks
        self.loop = asyncio.get_running_loop()
        
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
        """Callback for mDNS service changes."""
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                self._process_service_info(info)

    async def _validate_candidate(self, ip: str):
        """
        Verify if the candidate IP is the System Leader.
        
        If valid, set as speaker_ip and trigger event.
        If not, ignore it and continue scanning.
        """
        try:
             async with httpx.AsyncClient(timeout=2.0) as temp_client:
                # Check /devices/current
                resp = await temp_client.get(f"http://{ip}/ipcontrol/v1/devices/current")
                if resp.status_code == 200:
                    info = resp.json()
                    if info.get("isSystemLeader", False):
                        logger.info(f"Confirmed System Leader at {ip}")
                        self.speaker_ip = ip
                        self.discovery_event.set()
                    else:
                        logger.debug(f"Candidate {ip} is not System Leader. Ignoring.")
        except Exception as e:
            logger.debug(f"Failed to validate candidate {ip}: {e}")

    def _process_service_info(self, info: ServiceInfo):
        """
        Evaluate discovered service info to see if it matches our target speaker.
        """
        if self.target_name.lower() in info.name.lower():
            if info.addresses:
                ip = socket.inet_ntoa(info.addresses[0])
                logger.debug(f"Checking candidate: {info.name} at {ip}")
                
                # Check validation in background
                if not self.speaker_ip:
                     if hasattr(self, 'loop'):
                        asyncio.run_coroutine_threadsafe(self._validate_candidate(ip), self.loop)

    async def check_connection(self) -> bool:
        """
        Verify network connectivity and System Leader status.
        
        Returns:
            bool: True if connection is successful and we are on the Leader, False otherwise.
        """
        if not self.speaker_ip:
            return False
        try:
            # Check if we are the leader
            resp = await self.client.get(f"http://{self.speaker_ip}/ipcontrol/v1/devices/current")
            resp.raise_for_status()
            info = resp.json()
            if not info.get("isSystemLeader", False):
                logger.warning(f"Connected to {self.speaker_ip} but it is not the System Leader. Rejecting.")
                return False

            await self.get_volume()
            return True
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            self.speaker_ip = None # Invalidate
            self.discovery_event.clear()
            return False

    async def _resolve_ids(self) -> tuple[str, str]:
        """
        Resolve the systemId and sourceId.
        
        We default to 'current' which works on most firmware (including DOS 3.x)
        where the discovery endpoints (/systems, /groups) might return 404.
        """
        # Hardcode to defaults that are confirmed working
        return "/ipcontrol/v1/systems/current", "current"

    async def _restart_discovery(self):
        """
        Clear current connection state and restart mDNS discovery.
        
        This is called when API requests fail, assuming the IP might have changed
        or the speaker rebooted.
        """
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
        """Fetch current volume."""
        if not self.speaker_ip:
            if not self.browser and self.zeroconf:
                 await self._restart_discovery()
            await self.discovery_event.wait()
            
        base_path, source_id = await self._resolve_ids()
        url = f"http://{self.speaker_ip}{base_path}/sources/{source_id}/soundControl/volume"
        
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
        """Set speaker volume."""
        if not self.speaker_ip:
            await self.discovery_event.wait()
            
        volume = max(0, min(100, volume))
        
        base_path, source_id = await self._resolve_ids()
        url = f"http://{self.speaker_ip}{base_path}/sources/{source_id}/soundControl/volume"
        
        try:
            resp = await self.client.post(url, json={"volume": volume})
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            await self._restart_discovery()

    async def set_mute(self, mute: bool):
        """
        Set mute state using volume control.
        
        Since DOS 3.x firmware often lacks a working Mute endpoint, we emulate it
        by setting volume to 0 (Mute) and restoring the previous volume (Unmute).
        
        Args:
            mute (bool): True to mute (vol=0), False to unmute (restore vol).
        """
        if not self.speaker_ip:
            await self.discovery_event.wait()
            
        try:
            current_vol = await self.get_volume()
            
            if mute:
                if current_vol > 0:
                    self.last_volume = current_vol # Store for restore
                    logger.info(f"Muting: Saving volume {current_vol} and setting to 0")
                    await self.set_volume(0)
                else:
                    logger.debug("Already at volume 0 (muted)")
            else:
                # Unmute
                if current_vol == 0:
                    # Restore
                    restore_vol = getattr(self, 'last_volume', 20) # Default to 20 if no history
                    if restore_vol == 0: restore_vol = 20
                    logger.info(f"Unmuting: Restoring volume to {restore_vol}")
                    await self.set_volume(restore_vol)
                else:
                    logger.debug(f"Already unmuted (volume {current_vol})")
                    
        except Exception as e:
            logger.error(f"Error toggling mute: {e}")
            # If get_volume failed, we might need discovery
            if "SystemLeaderAbsent" in str(e) or "404" in str(e):
                 await self._restart_discovery()

    async def close(self):
        """Cleanup network resources."""
        await self.client.aclose()
        if self.zeroconf:
            self.zeroconf.close()
