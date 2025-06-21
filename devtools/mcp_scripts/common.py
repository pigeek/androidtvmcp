#!/usr/bin/env python3
"""
Common utilities for MCP-based Android TV client scripts.
"""

import argparse
import asyncio
import logging
import sys
import os
from typing import cast, Optional, Dict, Any, List

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

_LOGGER = logging.getLogger(__name__)


class MCPClient:
    """A wrapper for MCP client operations."""

    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self.session: Optional[ClientSession] = None
        self.devices: List[Dict[str, Any]] = []
        self.selected_device_id: Optional[str] = None

    async def __aenter__(self):
        try:
            _LOGGER.info("Connecting to MCP server...")
            self.stdio_context = stdio_client(self.server_params)
            read_stream, write_stream = await self.stdio_context.__aenter__()
            self.session_context = ClientSession(read_stream, write_stream)
            self.session = await self.session_context.__aenter__()
            await self.session.initialize()
            _LOGGER.info("Connected to MCP server.")
            await asyncio.sleep(2)  # Wait for the server to be ready
            return self
        except Exception as e:
            _LOGGER.error(f"Failed to connect to MCP server: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.session_context:
                await self.session_context.__aexit__(exc_type, exc_val, exc_tb)
            if self.stdio_context:
                await self.stdio_context.__aexit__(exc_type, exc_val, exc_tb)
            _LOGGER.info("Disconnected from MCP server.")
        except Exception as e:
            _LOGGER.warning(f"Error during disconnect: {e}")

    async def discover_devices(self) -> bool:
        """Discover Android TV devices using MCP."""
        try:
            _LOGGER.info("Discovering Android TV devices...")
            result = await self.session.call_tool("atv_get_devices", {})
            if result.content and hasattr(result.content[0], 'text'):
                result_text = result.content[0].text
                self.devices = self._parse_devices_from_result(result_text)
                if self.devices:
                    _LOGGER.info(f"Found {len(self.devices)} Android TV device(s).")
                    return True
            _LOGGER.warning("No Android TV devices found.")
            return False
        except Exception as e:
            _LOGGER.error(f"Error discovering devices: {e}")
            return False

    def _parse_devices_from_result(self, result_text: str) -> List[Dict[str, Any]]:
        """Parse device information from MCP result text."""
        import json
        try:
            # Try to parse as JSON first (new format)
            data = json.loads(result_text)
            if isinstance(data, dict) and 'devices' in data:
                return data['devices']
            else:
                _LOGGER.warning("Unexpected JSON structure in device result")
                return []
        except json.JSONDecodeError:
            # Fallback to regex parsing for backward compatibility
            _LOGGER.debug("Result is not JSON, falling back to regex parsing")
            import re
            devices = []
            device_pattern = r"AndroidTVDevice\(([^)]+)\)"
            device_matches = re.findall(device_pattern, result_text)
            for match in device_matches:
                device_info = {}
                field_patterns = {
                    'id': r"id='([^']+)'", 'name': r"name='([^']+)'",
                    'host': r"host='([^']+)'", 'port': r"port=(\d+)",
                    'model': r"model='([^']*)'", 'status': r"status=<DeviceStatus\.([^:]+):",
                    'pairing_status': r"pairing_status=<PairingStatus\.([^:]+):"
                }
                for field, pattern in field_patterns.items():
                    field_match = re.search(pattern, match)
                    if field_match:
                        value = field_match.group(1)
                        device_info[field] = int(value) if field == 'port' else value
                if device_info.get('id') and device_info.get('name'):
                    devices.append(device_info)
            return devices

    async def select_device(self, device_identifier: Optional[str] = None) -> bool:
        """Select a device to control."""
        if not self.devices:
            _LOGGER.error("No devices available. Run device discovery first.")
            return False

        if device_identifier:
            possible_matches = [d for d in self.devices if d['id'] == device_identifier or d['name'] == device_identifier]
            if not possible_matches:
                _LOGGER.error(f"Device '{device_identifier}' not found.")
                return False
            
            if len(possible_matches) == 1:
                selected = possible_matches[0]
            else:
                _LOGGER.info(f"Found multiple devices named '{device_identifier}'. Selecting the best one.")
                status_preferences = ['CONNECTED', 'CONNECTING', 'DISCONNECTED', 'PAIRING_REQUIRED']
                for status in status_preferences:
                    for device in possible_matches:
                        if device.get('status', '').upper() == status:
                            selected = device
                            break
                    if 'selected' in locals():
                        break
                if 'selected' not in locals():
                    selected = possible_matches[0]

            self.selected_device_id = selected['id']
            _LOGGER.info(f"Selected device: {selected['name']} ({selected['id']})")
            return True

        # Interactive selection
        print("\nAvailable Android TV devices:")
        for i, device in enumerate(self.devices, 1):
            print(f"  {i}. {device['name']} ({device['id']}) - {device.get('status', 'unknown')}, {device.get('pairing_status', 'unknown')}")
        
        while True:
            try:
                choice = input(f"Select device (1-{len(self.devices)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q': return False
                choice_num = int(choice)
                if 1 <= choice_num <= len(self.devices):
                    device = self.devices[choice_num - 1]
                    self.selected_device_id = device['id']
                    _LOGGER.info(f"Selected device: {device['name']} ({device['id']})")
                    return True
                else:
                    print(f"Please enter a number between 1 and {len(self.devices)}.")
            except (ValueError, KeyboardInterrupt):
                print("Invalid selection.")
                return False

    async def send_mcp_command(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Send a command to the Android TV via MCP."""
        if not self.session or not self.selected_device_id:
            _LOGGER.error("Not connected or no device selected.")
            return False
        
        arguments.setdefault('device_id', self.selected_device_id)
        _LOGGER.info(f"Sending {tool_name} with args: {arguments}")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            if result.content and hasattr(result.content[0], 'text'):
                result_text = result.content[0].text
                _LOGGER.info(f"Command result: {result_text}")
                if 'success=True' in result_text or 'successfully' in result_text.lower():
                    print("Command executed successfully.")
                    return True
                else:
                    _LOGGER.error(f"Command failed: {result_text}")
                    return False
            _LOGGER.error("No response from command.")
            return False
        except Exception as e:
            _LOGGER.error(f"Error sending command {tool_name}: {e}", exc_info=True)
            return False

def get_server_params(args: argparse.Namespace) -> StdioServerParameters:
    """Get MCP server parameters from command-line arguments."""
    server_args = ["-m", "androidtvmcp", "serve", "--transport", "stdio"]
    if args.verbose:
        server_args.extend(["--log-level", "DEBUG"])
    return StdioServerParameters(
        command=args.python,
        args=server_args,
        cwd=os.path.join(os.path.dirname(__file__), "..", "..")
    )

def setup_logging(verbose: bool):
    """Configure logging."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_common_parser() -> argparse.ArgumentParser:
    """Create a common argument parser for client scripts."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--device", help="Device ID or name to connect to.")
    parser.add_argument("--python", default=sys.executable, help="Python executable for the MCP server.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    return parser
