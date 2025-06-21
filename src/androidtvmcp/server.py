"""MCP Server implementation for Android TV Remote Control."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import ServerCapabilities
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from pydantic import BaseModel

from .device_manager import DeviceManager
from .commands import CommandProcessor
from .models import (
    NavigationCommand,
    PlaybackCommand,
    VolumeCommand,
    AppCommand,
    DeviceCommand,
)

logger = logging.getLogger(__name__)


class AndroidTVMCPServer:
    """MCP Server for Android TV Remote Control functionality."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the AndroidTV MCP Server.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.server = Server("androidtvmcp")
        self.device_manager = DeviceManager(self.config.get("devices", {}))
        self.command_processor = CommandProcessor(self.device_manager)
        
        # Register MCP handlers
        self._register_tools()
        self._register_resources()
        
    def _register_tools(self) -> None:
        """Register MCP tools for Android TV control."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available Android TV control tools."""
            return [
                Tool(
                    name="atv_navigate",
                    description="Navigate Android TV interface. Requires device_id to specify which device to control.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID (required - specify which device to control)"
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["up", "down", "left", "right", "select", "menu", "back", "home"],
                                "description": "Navigation direction or action"
                            }
                        },
                        "required": ["device_id", "direction"]
                    }
                ),
                Tool(
                    name="atv_input_text",
                    description="Send text input to Android TV. Requires device_id to specify which device to control.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID (required - specify which device to control)"
                            },
                            "text": {
                                "type": "string",
                                "description": "Text to input"
                            }
                        },
                        "required": ["device_id", "text"]
                    }
                ),
                Tool(
                    name="atv_playback",
                    description="Control media playback on Android TV. Requires device_id to specify which device to control.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID (required - specify which device to control)"
                            },
                            "action": {
                                "type": "string",
                                "enum": ["play_pause", "next", "previous"],
                                "description": "Playback action"
                            }
                        },
                        "required": ["device_id", "action"]
                    }
                ),
                Tool(
                    name="atv_volume",
                    description="Control volume on Android TV. Requires device_id to specify which device to control.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID (required - specify which device to control)"
                            },
                            "action": {
                                "type": "string",
                                "enum": ["up", "down", "mute"],
                                "description": "Volume action"
                            }
                        },
                        "required": ["device_id", "action"]
                    }
                ),
                Tool(
                    name="atv_launch_app",
                    description="Launch an application on Android TV. Requires device_id to specify which device to control. Provide either app_id or app_name.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID (required - specify which device to control)"
                            },
                            "app_id": {
                                "type": "string",
                                "description": "Application package name or ID. Either app_id or app_name must be provided."
                            },
                            "app_name": {
                                "type": "string",
                                "description": "Application display name. Either app_id or app_name must be provided."
                            }
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="atv_get_apps",
                    description="Get list of available applications on Android TV",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID (optional, uses default if not specified)"
                            }
                        }
                    }
                ),
                Tool(
                    name="atv_get_devices",
                    description="Get list of discovered Android TV devices",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="atv_get_status",
                    description="Get current status of Android TV device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID (optional, uses default if not specified)"
                            }
                        }
                    }
                ),
                Tool(
                    name="atv_power",
                    description="Control power state of Android TV. Requires device_id to specify which device to control.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID (required - specify which device to control)"
                            }
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="atv_start_pairing",
                    description="Start pairing process with an Android TV device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID to pair with"
                            }
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="atv_complete_pairing",
                    description="Complete pairing process with PIN code",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID to complete pairing for"
                            },
                            "pin": {
                                "type": "string",
                                "description": "PIN code displayed on Android TV"
                            }
                        },
                        "required": ["device_id", "pin"]
                    }
                ),
                Tool(
                    name="atv_unpair_device",
                    description="Unpair an Android TV device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID to unpair"
                            }
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="atv_get_pairing_status",
                    description="Get pairing status for an Android TV device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID to check pairing status"
                            }
                        },
                        "required": ["device_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
            """Handle tool calls for Android TV control."""
            try:
                device_id = arguments.get("device_id")
                
                if name == "atv_navigate":
                    command = NavigationCommand(
                        device_id=device_id,
                        direction=arguments["direction"]
                    )
                    result = await self.command_processor.execute_navigation(command)
                    
                elif name == "atv_input_text":
                    result = await self.command_processor.input_text(
                        device_id=device_id,
                        text=arguments["text"]
                    )
                    
                elif name == "atv_playback":
                    command = PlaybackCommand(
                        device_id=device_id,
                        action=arguments["action"]
                    )
                    result = await self.command_processor.execute_playback(command)
                    
                elif name == "atv_volume":
                    command = VolumeCommand(
                        device_id=device_id,
                        action=arguments["action"],
                        level=arguments.get("level")
                    )
                    result = await self.command_processor.execute_volume(command)
                    
                elif name == "atv_launch_app":
                    app_id = arguments.get("app_id")
                    app_name = arguments.get("app_name")
                    
                    # Validate that either app_id or app_name is provided
                    if not app_id and not app_name:
                        return [TextContent(type="text", text="Error: Either app_id or app_name must be provided")]
                    
                    command = AppCommand(
                        device_id=device_id,
                        app_id=app_id,
                        app_name=app_name,
                        action="launch"
                    )
                    result = await self.command_processor.execute_app_command(command)
                    
                elif name == "atv_get_apps":
                    result = await self.command_processor.get_apps(device_id=device_id)
                    
                elif name == "atv_get_devices":
                    result = await self.command_processor.get_devices()
                    # Return JSON for better parsing
                    import json
                    devices_data = {
                        "devices": [
                            {
                                "id": device.id,
                                "name": device.name,
                                "host": device.host,
                                "port": device.port,
                                "model": device.model,
                                "version": device.version,
                                "status": device.status.value if hasattr(device.status, 'value') else str(device.status),
                                "pairing_status": device.pairing_status.value if hasattr(device.pairing_status, 'value') else str(device.pairing_status),
                                "capabilities": device.capabilities,
                                "last_seen": device.last_seen
                            }
                            for device in result.devices
                        ],
                        "total": result.total,
                        "connected": result.connected,
                        "disconnected": result.disconnected
                    }
                    return [TextContent(type="text", text=json.dumps(devices_data, indent=2))]
                    
                elif name == "atv_get_status":
                    result = await self.command_processor.get_status(device_id=device_id)
                    
                elif name == "atv_power":
                    command = DeviceCommand(
                        device_id=device_id,
                    )
                    result = await self.command_processor.execute_device_command(command)
                    
                elif name == "atv_start_pairing":
                    result = await self.command_processor.start_pairing(arguments["device_id"])
                    
                elif name == "atv_complete_pairing":
                    result = await self.command_processor.complete_pairing(
                        arguments["device_id"],
                        arguments["pin"]
                    )
                    
                elif name == "atv_unpair_device":
                    result = await self.command_processor.unpair_device(arguments["device_id"])
                    
                elif name == "atv_get_pairing_status":
                    result = await self.command_processor.get_pairing_status(arguments["device_id"])
                    
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=str(result))]
                
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def _register_resources(self) -> None:
        """Register MCP resources for Android TV information."""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available Android TV resources."""
            resources = []
            
            # Add device resources
            device_response = await self.device_manager.get_devices()
            for device in device_response.devices:
                # URL-encode device ID to handle spaces and special characters
                import urllib.parse
                device_id_encoded = urllib.parse.quote(device.id, safe='')
                device_name = device.name or device.id
                
                resources.extend([
                    Resource(
                        uri=f"device://{device_id_encoded}/info",
                        name=f"Device {device_name} Information",
                        description=f"Information about Android TV device {device_name}",
                        mimeType="application/json"
                    ),
                    Resource(
                        uri=f"device://{device_id_encoded}/status",
                        name=f"Device {device_name} Status",
                        description=f"Current status of Android TV device {device_name}",
                        mimeType="application/json"
                    ),
                    Resource(
                        uri=f"device://{device_id_encoded}/apps",
                        name=f"Device {device_name} Applications",
                        description=f"Available applications on Android TV device {device_name}",
                        mimeType="application/json"
                    )
                ])
            
            # Add state resources
            resources.extend([
                Resource(
                    uri="state://current_app",
                    name="Current Application",
                    description="Currently active application across all devices",
                    mimeType="application/json"
                ),
                Resource(
                    uri="state://playback",
                    name="Playback Status",
                    description="Current playback status across all devices",
                    mimeType="application/json"
                ),
                Resource(
                    uri="state://volume",
                    name="Volume Status",
                    description="Current volume levels across all devices",
                    mimeType="application/json"
                )
            ])
            
            return resources

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read Android TV resource content."""
            try:
                if uri.startswith("device://"):
                    # Parse device resource URI
                    parts = uri.replace("device://", "").split("/")
                    if len(parts) >= 2:
                        # URL-decode device ID to handle spaces and special characters
                        import urllib.parse
                        device_id = urllib.parse.unquote(parts[0])
                        resource_type = parts[1]
                        
                        if resource_type == "info":
                            result = await self.command_processor.get_device_info(device_id)
                        elif resource_type == "status":
                            result = await self.command_processor.get_status(device_id)
                        elif resource_type == "apps":
                            result = await self.command_processor.get_apps(device_id)
                        else:
                            raise ValueError(f"Unknown device resource type: {resource_type}")
                    else:
                        raise ValueError(f"Invalid device resource URI: {uri}")
                        
                elif uri.startswith("state://"):
                    # Parse state resource URI
                    state_type = uri.replace("state://", "")
                    
                    if state_type == "current_app":
                        result = await self.command_processor.get_current_apps()
                    elif state_type == "playback":
                        result = await self.command_processor.get_playback_status()
                    elif state_type == "volume":
                        result = await self.command_processor.get_volume_status()
                    else:
                        raise ValueError(f"Unknown state resource type: {state_type}")
                        
                else:
                    raise ValueError(f"Unknown resource URI scheme: {uri}")
                
                return str(result)
                
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                return f"Error: {str(e)}"

    async def start_discovery(self) -> None:
        """Start device discovery."""
        await self.device_manager.start_discovery()

    async def stop_discovery(self) -> None:
        """Stop device discovery."""
        await self.device_manager.stop_discovery()

    async def run_stdio(self, log_level: int = logging.INFO) -> None:
        """Run the MCP server with stdio transport."""
        logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger.info(f"Starting AndroidTVMCP server with stdio transport (log_level={logging.getLevelName(log_level)})")
        
        try:
            # Start device discovery
            logger.debug("Starting device discovery...")
            await self.start_discovery()
            logger.debug("Device discovery started successfully")
            
            logger.debug("Initializing stdio server...")
            async with stdio_server() as (read_stream, write_stream):
                logger.debug("stdio server initialized, starting MCP server...")
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="androidtvmcp",
                        server_version="0.2.0",
                        capabilities=ServerCapabilities(
                            tools={},
                            resources={}
                        ),
                    ),
                )
        except Exception as e:
            import traceback
            logger.error(f"Server error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        finally:
            # Stop device discovery
            try:
                await self.stop_discovery()
            except Exception as e:
                logger.error(f"Error stopping discovery: {e}")
            logger.info("AndroidTVMCP server stopped")

    async def run_tcp(self, host: str = "localhost", port: int = 8080) -> None:
        """Run the MCP server with TCP transport.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        logger.info(f"Starting AndroidTVMCP server on {host}:{port}")
        
        # Start device discovery
        await self.start_discovery()
        
        try:
            # TCP transport implementation would go here
            # This is a placeholder for future TCP transport support
            raise NotImplementedError("TCP transport not yet implemented")
        finally:
            # Stop device discovery
            await self.stop_discovery()
            logger.info("AndroidTVMCP server stopped")
