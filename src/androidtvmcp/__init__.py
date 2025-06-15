"""AndroidTVMCP - Android TV Remote Control to MCP Bridge."""

__version__ = "0.1.0"
__author__ = "Pigeek"
__description__ = "Android TV Remote Control to MCP Bridge"

from .server import AndroidTVMCPServer
from .device_manager import DeviceManager
from .commands import CommandProcessor

__all__ = [
    "AndroidTVMCPServer",
    "DeviceManager", 
    "CommandProcessor",
]
