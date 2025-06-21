"""Data models for Android TV Remote Control commands and responses."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class NavigationDirection(str, Enum):
    """Navigation directions for Android TV."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    SELECT = "select"
    MENU = "menu"
    BACK = "back"
    HOME = "home"


class PlaybackAction(str, Enum):
    """Playback actions for Android TV."""
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    FAST_FORWARD = "fast_forward"
    REWIND = "rewind"
    NEXT = "next"
    PREVIOUS = "previous"


class VolumeAction(str, Enum):
    """Volume actions for Android TV."""
    UP = "up"
    DOWN = "down"
    MUTE = "mute"
    UNMUTE = "unmute"


class PowerAction(str, Enum):
    """Power actions for Android TV."""
    ON = "on"
    OFF = "off"
    SLEEP = "sleep"
    WAKE = "wake"


class AppAction(str, Enum):
    """Application actions for Android TV."""
    LAUNCH = "launch"
    SWITCH = "switch"
    CLOSE = "close"


class DeviceStatus(str, Enum):
    """Device connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    PAIRING_REQUIRED = "pairing_required"
    PAIRING = "pairing"
    ERROR = "error"


class PairingStatus(str, Enum):
    """Device pairing status."""
    NOT_PAIRED = "not_paired"
    PAIRING = "pairing"
    PAIRED = "paired"
    PAIRING_FAILED = "pairing_failed"


class NavigationCommand(BaseModel):
    """Command for Android TV navigation."""
    device_id: Optional[str] = None
    direction: NavigationDirection
    
    class Config:
        use_enum_values = True


class PlaybackCommand(BaseModel):
    """Command for Android TV playback control."""
    device_id: Optional[str] = None
    action: PlaybackAction
    
    class Config:
        use_enum_values = True


class VolumeCommand(BaseModel):
    """Command for Android TV volume control."""
    device_id: Optional[str] = None
    action: VolumeAction
    level: Optional[int] = Field(None, ge=0, le=100)
    
    class Config:
        use_enum_values = True


class AppCommand(BaseModel):
    """Command for Android TV application control."""
    device_id: Optional[str] = None
    action: AppAction
    app_id: Optional[str] = None
    app_name: Optional[str] = None
    
    class Config:
        use_enum_values = True


class DeviceCommand(BaseModel):
    """Command for Android TV device control."""
    device_id: Optional[str] = None
    
    class Config:
        use_enum_values = True


class PairingCommand(BaseModel):
    """Command for Android TV device pairing."""
    device_id: str
    pin: Optional[str] = None
    
    class Config:
        use_enum_values = True


class DeviceCertificate(BaseModel):
    """Android TV device certificate information."""
    device_id: str
    certificate: str
    private_key: str
    created_at: str
    expires_at: Optional[str] = None


class PairingResult(BaseModel):
    """Result of a pairing operation."""
    success: bool
    message: str
    device_id: str
    status: PairingStatus
    pin_required: bool = False
    error_code: Optional[str] = None


class AndroidTVDevice(BaseModel):
    """Android TV device information."""
    id: str
    name: str
    host: str
    port: int
    model: Optional[str] = None
    version: Optional[str] = None
    status: DeviceStatus = DeviceStatus.DISCONNECTED
    pairing_status: PairingStatus = PairingStatus.NOT_PAIRED
    capabilities: List[str] = Field(default_factory=list)
    last_seen: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AndroidTVApp(BaseModel):
    """Android TV application information."""
    id: str
    name: str
    package_name: str
    version: Optional[str] = None
    is_running: bool = False
    is_system_app: bool = False
    icon_url: Optional[str] = None


class PlaybackState(BaseModel):
    """Current playback state information."""
    device_id: str
    is_playing: bool = False
    is_paused: bool = False
    current_app: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    duration: Optional[int] = None
    position: Optional[int] = None
    volume: Optional[int] = None
    is_muted: bool = False


class DeviceState(BaseModel):
    """Current device state information."""
    device_id: str
    status: DeviceStatus
    power_state: Optional[str] = None
    current_app: Optional[AndroidTVApp] = None
    volume: Optional[int] = None
    is_muted: bool = False
    screen_on: bool = False
    last_updated: Optional[str] = None
    
    class Config:
        use_enum_values = True


class CommandResult(BaseModel):
    """Result of a command execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    device_id: Optional[str] = None


class DiscoveryResult(BaseModel):
    """Result of device discovery."""
    devices: List[AndroidTVDevice]
    discovery_time: str
    total_found: int


class DeviceListResponse(BaseModel):
    """Response for device list requests."""
    devices: List[AndroidTVDevice]
    total: int
    connected: int
    disconnected: int


class AppListResponse(BaseModel):
    """Response for application list requests."""
    device_id: str
    apps: List[AndroidTVApp]
    total: int
    running: int


class StatusResponse(BaseModel):
    """Response for device status requests."""
    device_id: str
    device_state: DeviceState
    playback_state: Optional[PlaybackState] = None
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str


class ConfigModel(BaseModel):
    """Configuration model for the server."""
    devices: Dict[str, Any] = Field(default_factory=dict)
    mcp: Dict[str, Any] = Field(default_factory=dict)
    logging: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"


class DeviceConfig(BaseModel):
    """Device-specific configuration."""
    discovery: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "timeout": 10,
        "interval": 30
    })
    connection: Dict[str, Any] = Field(default_factory=lambda: {
        "timeout": 5,
        "retry_attempts": 3,
        "retry_delay": 1
    })
    
    class Config:
        extra = "allow"


class MCPConfig(BaseModel):
    """MCP server configuration."""
    host: str = "localhost"
    port: int = 8080
    transport: str = "stdio"
    
    class Config:
        extra = "allow"


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: Optional[str] = None
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        extra = "allow"
