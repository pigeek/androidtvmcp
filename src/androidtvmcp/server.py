"""MCP Server implementation for Android TV Remote Control."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
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
from .chromecast import ChromecastController

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
        
        # Initialize Chromecast controller for casting
        cast_config = self.config.get("cast", {})
        receiver_url = cast_config.get("receiver_url", "https://uijit.com/canvas-receiver")
        app_id = cast_config.get("app_id", "BE2EA00B")
        self.chromecast_controller = ChromecastController(receiver_url=receiver_url, app_id=app_id)
        
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
                    description="Navigate Android TV interface. Requires pairing first (use atv_start_pairing).",
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
                    description="Send text input to Android TV. Requires pairing first (use atv_start_pairing).",
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
                    description="Control media playback on Android TV. Requires pairing first (use atv_start_pairing).",
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
                    description="Control volume on Android TV. Requires pairing first (use atv_start_pairing).",
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
                    description="Launch an application on Android TV. Requires pairing first (use atv_start_pairing). Provide either app_id or app_name.",
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
                    description="Get list of discovered Android TV/Chromecast devices on the network. IMPORTANT: Casting (atv_cast_url) works on ANY discovered device - no pairing needed. Pairing is ONLY required for remote control features (navigate, input, playback, volume, power). When multiple devices are found, ALWAYS ask the user which device to use - never assume.",
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
                    description="Control power state of Android TV. Requires pairing first (use atv_start_pairing).",
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
                ),
                # Chromecast Casting Tools (no pairing required)
                Tool(
                    name="atv_cast_url",
                    description="Cast a Canvas surface to a Chromecast/Android TV device. NO PAIRING REQUIRED - works with ANY discovered device. If the user didn't specify which device, ask them to choose from the available devices first.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID to cast to"
                            },
                            "canvas_server_url": {
                                "type": "string",
                                "description": "WebSocket URL of the Canvas server (e.g., ws://192.168.1.50:8080)"
                            },
                            "surface_id": {
                                "type": "string",
                                "description": "Canvas surface ID to display"
                            }
                        },
                        "required": ["device_id", "canvas_server_url", "surface_id"]
                    }
                ),
                Tool(
                    name="atv_cast_stop",
                    description="Stop casting on a Chromecast/Android TV device. No pairing required.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID to stop casting on"
                            }
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="atv_cast_status",
                    description="Get casting status for a Chromecast/Android TV device. No pairing required.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Android TV device ID to check casting status"
                            }
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="atv_list_paired",
                    description="List all paired Android TV devices with their status",
                    inputSchema={
                        "type": "object",
                        "properties": {}
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
                    devices_list = [
                        {
                            "id": device.id,
                            "name": device.name,
                            "host": device.host,
                            "port": device.port,
                            "model": device.model,
                            "version": device.version,
                            "status": device.status.value if hasattr(device.status, 'value') else str(device.status),
                            "pairing_status_for_remote_control": device.pairing_status.value if hasattr(device.pairing_status, 'value') else str(device.pairing_status),
                            "casting_available": True,
                            "capabilities": device.capabilities,
                            "last_seen": device.last_seen
                        }
                        for device in result.devices
                    ]
                    devices_data = {
                        "casting_info": "Casting works on ALL devices listed - no pairing needed. Pairing is only for remote control features.",
                        "devices": devices_list,
                        "total": result.total,
                        "connected": result.connected,
                        "disconnected": result.disconnected
                    }
                    # Add action_required if multiple devices
                    if len(devices_list) > 1:
                        devices_data["action_required"] = f"STOP! {len(devices_list)} devices found. You MUST ask the user which device to use. Present the list of device names and wait for user selection. Do NOT assume or proceed without explicit user choice."
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
                
                # Chromecast Casting Tools
                elif name == "atv_cast_url":
                    # Get device to find its host IP
                    device = await self.device_manager.get_device(arguments["device_id"])
                    if not device:
                        return [TextContent(type="text", text=f"Error: Device not found: {arguments['device_id']}")]
                    
                    result = await self.chromecast_controller.cast_to_device(
                        host=device.host,
                        canvas_server_url=arguments["canvas_server_url"],
                        surface_id=arguments["surface_id"],
                        device_name=device.name
                    )
                    import json
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "atv_cast_stop":
                    device = await self.device_manager.get_device(arguments["device_id"])
                    if not device:
                        return [TextContent(type="text", text=f"Error: Device not found: {arguments['device_id']}")]
                    
                    result = await self.chromecast_controller.stop_cast(device.host)
                    import json
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "atv_cast_status":
                    device = await self.device_manager.get_device(arguments["device_id"])
                    if not device:
                        return [TextContent(type="text", text=f"Error: Device not found: {arguments['device_id']}")]
                    
                    result = await self.chromecast_controller.get_cast_status(device.host)
                    import json
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "atv_list_paired":
                    paired_devices = await self.command_processor.get_paired_devices()
                    # Also get cast sessions
                    cast_sessions = await self.chromecast_controller.get_all_sessions()
                    
                    # Merge cast status into paired devices
                    result = {
                        "paired_devices": paired_devices.get("paired_devices", []),
                        "total_paired": paired_devices.get("total_paired", 0),
                        "active_casts": cast_sessions
                    }
                    import json
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                    
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

    async def run_sse(self, port: int = 3002, log_level: int = logging.INFO) -> None:
        """Run the MCP server with SSE transport for remote access.

        Args:
            port: Port for the SSE endpoint
            log_level: Logging level
        """
        import uvicorn

        logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger.info(f"Starting AndroidTVMCP server with SSE transport on port {port}")

        # Create SSE transport
        sse_transport = SseServerTransport("/messages/")
        
        # Keep reference to discovery task
        discovery_task = None

        # Create raw ASGI handlers for SSE (Starlette Request doesn't expose send correctly)
        async def handle_sse(scope, receive, send):
            async with sse_transport.connect_sse(scope, receive, send) as streams:
                await self.server.run(
                    streams[0],
                    streams[1],
                    InitializationOptions(
                        server_name="androidtvmcp",
                        server_version="0.2.0",
                        capabilities=ServerCapabilities(
                            tools={},
                            resources={}
                        ),
                    ),
                )

        async def handle_messages(scope, receive, send):
            await sse_transport.handle_post_message(scope, receive, send)

        # Create ASGI app that routes based on path
        async def app(scope, receive, send):
            nonlocal discovery_task
            if scope["type"] == "http":
                path = scope["path"]
                if path == "/sse" and scope["method"] == "GET":
                    await handle_sse(scope, receive, send)
                elif path.startswith("/messages") and scope["method"] == "POST":
                    await handle_messages(scope, receive, send)
                else:
                    # Return 404
                    await send({"type": "http.response.start", "status": 404, "headers": []})
                    await send({"type": "http.response.body", "body": b"Not Found"})
            elif scope["type"] == "lifespan":
                # Handle lifespan events - discovery starts here, orthogonal to MCP
                while True:
                    message = await receive()
                    if message["type"] == "lifespan.startup":
                        # Start discovery as background task - doesn't block server startup
                        logger.info("Starting device discovery (background task)")
                        discovery_task = asyncio.create_task(self.start_discovery())
                        await send({"type": "lifespan.startup.complete"})
                    elif message["type"] == "lifespan.shutdown":
                        # Cancel discovery task if running
                        if discovery_task and not discovery_task.done():
                            discovery_task.cancel()
                            try:
                                await discovery_task
                            except asyncio.CancelledError:
                                pass
                        await self.stop_discovery()
                        await send({"type": "lifespan.shutdown.complete"})
                        return

        try:
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=port,
                log_level="info",
            )
            server = uvicorn.Server(config)
            await server.serve()
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            await self.stop_discovery()
            logger.info("AndroidTVMCP server stopped")
