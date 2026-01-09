import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Mock evdev before importing main
import sys
sys.modules['evdev'] = MagicMock()

from main import PhantomBridge
from devialet_client import DevialetClient

class TestDevialetClient(unittest.IsolatedAsyncioTestCase):
    async def test_clamp_volume(self):
        config = {"speaker": {"name": "Test"}}
        client = DevialetClient(config)
        client.speaker_ip = "1.2.3.4"
        client.client = AsyncMock()
        
        # Test > 100
        await client.set_volume(150)
        client.client.post.assert_called_with(
            "http://1.2.3.4/ipcontrol/v1/systems/current/sources/current/soundControl/volume",
            json={"volume": 100}
        )
        
        # Test < 0
        await client.set_volume(-10)
        client.client.post.assert_called_with(
            "http://1.2.3.4/ipcontrol/v1/systems/current/sources/current/soundControl/volume",
            json={"volume": 0}
        )

    async def test_reconnect_on_error(self):
        config = {"speaker": {"name": "Test"}}
        client = DevialetClient(config)
        client.speaker_ip = "1.2.3.4"
        client.client = AsyncMock()
        client.client.post.side_effect = Exception("Connection Failed")
        
        # Mock restart method
        client._restart_discovery = AsyncMock()
        
        await client.set_volume(50)
        client._restart_discovery.assert_called_once()


class TestPhantomBridge(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Create a dummy config
        with open("test_config.yaml", "w") as f:
            f.write("ir_codes:\n  0x01: volume_up\n  0x02: volume_down\nspeaker:\n  volume_step: 3\n")
            
    def tearDown(self):
        import os
        if os.path.exists("test_config.yaml"):
            os.remove("test_config.yaml")

    async def test_volume_actions(self):
        bridge = PhantomBridge("test_config.yaml")
        bridge.client = AsyncMock()
        bridge.client.get_volume.return_value = 50
        
        # Test Volume Up
        await bridge.process_ir_code(0x01)
        bridge.client.set_volume.assert_called_with(53)
        
        # Reset debounce timer for test
        bridge.last_volume_time = 0
        
        # Test Volume Down
        await bridge.process_ir_code(0x02)
        bridge.client.set_volume.assert_called_with(47) # 50 (mock return) - 3

    async def test_debouncing(self):
        bridge = PhantomBridge("test_config.yaml")
        bridge.client = AsyncMock()
        bridge.client.get_volume.return_value = 50
        
        # First call
        await bridge.process_ir_code(0x01)
        self.assertEqual(bridge.client.set_volume.call_count, 1)
        
        # Immediate second call (should be ignored)
        await bridge.process_ir_code(0x01)
        self.assertEqual(bridge.client.set_volume.call_count, 1)
        
        # Wait
        import time
        bridge.last_volume_time = time.time() - 0.2
        await bridge.process_ir_code(0x01)
        self.assertEqual(bridge.client.set_volume.call_count, 2)

if __name__ == '__main__':
    unittest.main()
