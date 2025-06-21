"""Command processor for Android TV Remote Control operations."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json

from androidtvremote2 import AndroidTVRemote

from .device_manager import DeviceManager
from .models import (
    NavigationCommand,
    PlaybackCommand,
    VolumeCommand,
    AppCommand,
    DeviceCommand,
    PairingCommand,
    CommandResult,
    PairingResult,
    AndroidTVApp,
    PlaybackState,
    DeviceState,
    StatusResponse,
    AppListResponse,
    DeviceListResponse,
    AndroidTVDevice,
    DeviceStatus,
)

logger = logging.getLogger(__name__)


class CommandProcessor:
    """Processes Android TV remote control commands."""

    def __init__(self, device_manager: DeviceManager):
        """Initialize the command processor.
        
        Args:
            device_manager: Device manager instance
        """
        self.device_manager = device_manager

    async def execute_navigation(self, command: NavigationCommand) -> CommandResult:
        """Execute a navigation command.
        
        Args:
            command: Navigation command to execute
            
        Returns:
            CommandResult with execution status
        """
        try:
            remote = await self.device_manager.get_connection(command.device_id)
            if not remote:
                return CommandResult(
                    success=False,
                    message="No Android TV device available",
                    error_code="NO_DEVICE",
                    device_id=command.device_id
                )

            # Map navigation directions to remote methods
            navigation_map = {
                "up": "DPAD_UP",
                "down": "DPAD_DOWN",
                "left": "DPAD_LEFT",
                "right": "DPAD_RIGHT",
                "select": "DPAD_CENTER",
                "back": "BACK",
                "home": "HOME"
            }

            if command.direction not in navigation_map:
                return CommandResult(
                    success=False,
                    message=f"Unknown navigation direction: {command.direction}",
                    error_code="INVALID_DIRECTION",
                    device_id=command.device_id
                )

            # Execute the navigation command
            remote.send_key_command(navigation_map[command.direction])
            
            return CommandResult(
                success=True,
                message=f"Navigation command '{command.direction}' executed successfully",
                device_id=command.device_id
            )

        except Exception as e:
            logger.error(f"Error executing navigation command: {e}")
            return CommandResult(
                success=False,
                message=f"Failed to execute navigation command: {str(e)}",
                error_code="EXECUTION_ERROR",
                device_id=command.device_id
            )

    async def input_text(self, device_id: Optional[str], text: str) -> CommandResult:
        """Send text input to Android TV.
        
        Args:
            device_id: Device ID to send text to
            text: Text to input
            
        Returns:
            CommandResult with execution status
        """
        try:
            remote = await self.device_manager.get_connection(device_id)
            if not remote:
                return CommandResult(
                    success=False,
                    message="No Android TV device available",
                    error_code="NO_DEVICE",
                    device_id=device_id
                )

            # Send text input
            await remote.send_text(text)

            return CommandResult(
                success=True,
                message=f"Text input '{text}' sent successfully",
                device_id=device_id
            )

        except Exception as e:
            logger.error(f"Error sending text input: {e}")
            return CommandResult(
                success=False,
                message=f"Failed to send text input: {str(e)}",
                error_code="EXECUTION_ERROR",
                device_id=device_id
            )

    async def execute_playback(self, command: PlaybackCommand) -> CommandResult:
        """Execute a playback command.
        
        Args:
            command: Playback command to execute
            
        Returns:
            CommandResult with execution status
        """
        try:
            remote = await self.device_manager.get_connection(command.device_id)
            if not remote:
                return CommandResult(
                    success=False,
                    message="No Android TV device available",
                    error_code="NO_DEVICE",
                    device_id=command.device_id
                )

            # Map playback actions to remote methods
            playback_map = {
                "play_pause": "MEDIA_PLAY_PAUSE",
                "next": "DPAD_RIGHT",
                "previous": "DPAD_LEFT"
            }

            if command.action not in playback_map:
                return CommandResult(
                    success=False,
                    message=f"Unknown playback action: {command.action}",
                    error_code="INVALID_ACTION",
                    device_id=command.device_id
                )

            # Execute the playback command
            remote.send_key_command(playback_map[command.action])

            return CommandResult(
                success=True,
                message=f"Playback command '{command.action}' executed successfully",
                device_id=command.device_id
            )

        except Exception as e:
            logger.error(f"Error executing playback command: {e}")
            return CommandResult(
                success=False,
                message=f"Failed to execute playback command: {str(e)}",
                error_code="EXECUTION_ERROR",
                device_id=command.device_id
            )

    async def execute_volume(self, command: VolumeCommand) -> CommandResult:
        """Execute a volume command.
        
        Args:
            command: Volume command to execute
            
        Returns:
            CommandResult with execution status
        """
        try:
            remote = await self.device_manager.get_connection(command.device_id)
            if not remote:
                return CommandResult(
                    success=False,
                    message="No Android TV device available",
                    error_code="NO_DEVICE",
                    device_id=command.device_id
                )

            # Map volume actions to remote methods
            volume_map = {
                "up": "VOLUME_UP",
                "down": "VOLUME_DOWN",
                "mute": "MUTE"
            }

            if command.action not in volume_map:
                return CommandResult(
                    success=False,
                    message=f"Unknown volume action: {command.action}",
                    error_code="INVALID_ACTION",
                    device_id=command.device_id
                )

            # Execute the volume command
            remote.send_key_command(volume_map[command.action])

            message = f"Volume command '{command.action}' executed successfully"

            return CommandResult(
                success=True,
                message=message,
                device_id=command.device_id
            )

        except Exception as e:
            logger.error(f"Error executing volume command: {e}")
            return CommandResult(
                success=False,
                message=f"Failed to execute volume command: {str(e)}",
                error_code="EXECUTION_ERROR",
                device_id=command.device_id
            )

    async def execute_app_command(self, command: AppCommand) -> CommandResult:
        """Execute an application command.
        
        Args:
            command: App command to execute
            
        Returns:
            CommandResult with execution status
        """
        try:
            remote = await self.device_manager.get_connection(command.device_id)
            if not remote:
                return CommandResult(
                    success=False,
                    message="No Android TV device available",
                    error_code="NO_DEVICE",
                    device_id=command.device_id
                )

            if command.action == "launch":
                if command.app_id:
                    # Launch app by package name
                    remote.send_launch_app_command(command.app_id)
                    message = f"Launched app with ID: {command.app_id}"
                elif command.app_name:
                    # Find app by name and launch
                    apps = await self._get_device_apps(remote)
                    target_app = None
                    
                    # Try exact match first
                    for app in apps:
                        if app.name.lower() == command.app_name.lower():
                            target_app = app
                            break
                    
                    # If no exact match, try partial match
                    if not target_app:
                        for app in apps:
                            if command.app_name.lower() in app.name.lower():
                                target_app = app
                                break
                    
                    # If still no match, try common app package names
                    if not target_app:
                        common_apps = {
                            "netflix": "com.netflix.ninja",
                            "youtube": "com.google.android.youtube.tv",
                            "prime video": "com.amazon.amazonvideo.livingroom",
                            "disney+": "com.disney.disneyplus",
                            "hulu": "com.hulu.plus",
                            "spotify": "com.spotify.tv.android",
                            "plex": "com.plexapp.android",
                            "kodi": "org.xbmc.kodi",
                        }
                        
                        app_name_lower = command.app_name.lower()
                        if app_name_lower in common_apps:
                            # Try to launch directly by package name
                            try:
                                remote.send_launch_app_command(common_apps[app_name_lower])
                                message = f"Launched app: {command.app_name}"
                            except Exception as e:
                                return CommandResult(
                                    success=False,
                                    message=f"Failed to launch {command.app_name}: {str(e)}",
                                    error_code="APP_LAUNCH_FAILED",
                                    device_id=command.device_id
                                )
                        else:
                            return CommandResult(
                                success=False,
                                message=f"App not found: {command.app_name}. Available apps: {', '.join([app.name for app in apps[:5]])}{'...' if len(apps) > 5 else ''}",
                                error_code="APP_NOT_FOUND",
                                device_id=command.device_id
                            )
                    else:
                        await remote.launch_app(target_app.package_name)
                        message = f"Launched app: {target_app.name}"
                else:
                    return CommandResult(
                        success=False,
                        message="Either app_id or app_name must be specified",
                        error_code="MISSING_APP_IDENTIFIER",
                        device_id=command.device_id
                    )
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown app action: {command.action}",
                    error_code="INVALID_ACTION",
                    device_id=command.device_id
                )

            return CommandResult(
                success=True,
                message=message,
                device_id=command.device_id
            )

        except Exception as e:
            logger.error(f"Error executing app command: {e}")
            return CommandResult(
                success=False,
                message=f"Failed to execute app command: {str(e)}",
                error_code="EXECUTION_ERROR",
                device_id=command.device_id
            )

    async def execute_device_command(self, command: DeviceCommand) -> CommandResult:
        """Execute a device power command.
        
        Args:
            command: Device command to execute
            
        Returns:
            CommandResult with execution status
        """
        try:
            remote = await self.device_manager.get_connection(command.device_id)
            if not remote:
                return CommandResult(
                    success=False,
                    message="No Android TV device available",
                    error_code="NO_DEVICE",
                    device_id=command.device_id
                )

            # Execute the power command
            remote.send_key_command('POWER')

            return CommandResult(
                success=True,
                message=f"Power command executed successfully",
                device_id=command.device_id
            )

        except Exception as e:
            logger.error(f"Error executing device command: {e}")
            return CommandResult(
                success=False,
                message=f"Failed to execute device command: {str(e)}",
                error_code="EXECUTION_ERROR",
                device_id=command.device_id
            )

    async def get_apps(self, device_id: Optional[str] = None) -> AppListResponse:
        """Get list of applications on Android TV.
        
        Args:
            device_id: Device ID to get apps from
            
        Returns:
            AppListResponse with application list
        """
        try:
            remote = await self.device_manager.get_connection(device_id)
            if not remote:
                return AppListResponse(
                    device_id=device_id or "unknown",
                    apps=[],
                    total=0,
                    running=0
                )

            apps = await self._get_device_apps(remote)
            running_count = sum(1 for app in apps if app.is_running)

            return AppListResponse(
                device_id=device_id or "unknown",
                apps=apps,
                total=len(apps),
                running=running_count
            )

        except Exception as e:
            logger.error(f"Error getting apps: {e}")
            return AppListResponse(
                device_id=device_id or "unknown",
                apps=[],
                total=0,
                running=0
            )

    async def get_devices(self) -> DeviceListResponse:
        """Get list of discovered devices.
        
        Returns:
            DeviceListResponse with device information
        """
        return await self.device_manager.get_devices()

    async def get_status(self, device_id: Optional[str] = None) -> StatusResponse:
        """Get current status of Android TV device.
        
        Args:
            device_id: Device ID to get status for
            
        Returns:
            StatusResponse with device status
        """
        try:
            # Get device info
            if device_id:
                device = await self.device_manager.get_device(device_id)
            else:
                devices = await self.device_manager.get_devices()
                device = devices.devices[0] if devices.devices else None

            if not device:
                # Create a placeholder device state
                device_state = DeviceState(
                    device_id=device_id or "unknown",
                    status=DeviceStatus.DISCONNECTED,
                    last_updated=datetime.now(timezone.utc).isoformat()
                )
                return StatusResponse(
                    device_id=device_id or "unknown",
                    device_state=device_state,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )

            # Get connection and current state
            remote = await self.device_manager.get_connection(device.id)
            
            device_state = DeviceState(
                device_id=device.id,
                status=device.status,
                last_updated=datetime.now(timezone.utc).isoformat()
            )

            playback_state = None
            if remote:
                try:
                    # Get current playback state
                    playback_state = await self._get_playback_state(remote, device.id)
                    
                    # Update device state with current info
                    device_state.screen_on = True  # Assume screen is on if connected
                    if playback_state:
                        device_state.volume = playback_state.volume
                        device_state.is_muted = playback_state.is_muted
                        
                except Exception as e:
                    logger.warning(f"Could not get detailed status for device {device.id}: {e}")

            return StatusResponse(
                device_id=device.id,
                device_state=device_state,
                playback_state=playback_state,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            device_state = DeviceState(
                device_id=device_id or "unknown",
                status=DeviceStatus.ERROR,
                last_updated=datetime.now(timezone.utc).isoformat()
            )
            return StatusResponse(
                device_id=device_id or "unknown",
                device_state=device_state,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

    async def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get detailed device information.
        
        Args:
            device_id: Device ID to get info for
            
        Returns:
            Dictionary with device information
        """
        try:
            device = await self.device_manager.get_device(device_id)
            if not device:
                return {"error": "Device not found"}

            return {
                "id": device.id,
                "name": device.name,
                "host": device.host,
                "port": device.port,
                "model": device.model,
                "version": device.version,
                "status": device.status,
                "capabilities": device.capabilities,
                "last_seen": device.last_seen
            }

        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return {"error": str(e)}

    async def get_current_apps(self) -> Dict[str, Any]:
        """Get currently active applications across all devices.
        
        Returns:
            Dictionary with current app information
        """
        try:
            devices = await self.device_manager.get_devices()
            current_apps = {}

            for device in devices.devices:
                if device.status == DeviceStatus.CONNECTED:
                    remote = await self.device_manager.get_connection(device.id)
                    if remote:
                        try:
                            # Get current app info
                            current_app = await self._get_current_app(remote)
                            if current_app:
                                current_apps[device.id] = current_app
                        except Exception as e:
                            logger.warning(f"Could not get current app for device {device.id}: {e}")

            return {"current_apps": current_apps}

        except Exception as e:
            logger.error(f"Error getting current apps: {e}")
            return {"error": str(e)}

    async def get_playback_status(self) -> Dict[str, Any]:
        """Get playback status across all devices.
        
        Returns:
            Dictionary with playback status information
        """
        try:
            devices = await self.device_manager.get_devices()
            playback_status = {}

            for device in devices.devices:
                if device.status == DeviceStatus.CONNECTED:
                    remote = await self.device_manager.get_connection(device.id)
                    if remote:
                        try:
                            playback_state = await self._get_playback_state(remote, device.id)
                            if playback_state:
                                playback_status[device.id] = playback_state.dict()
                        except Exception as e:
                            logger.warning(f"Could not get playback status for device {device.id}: {e}")

            return {"playback_status": playback_status}

        except Exception as e:
            logger.error(f"Error getting playback status: {e}")
            return {"error": str(e)}

    async def get_volume_status(self) -> Dict[str, Any]:
        """Get volume status across all devices.
        
        Returns:
            Dictionary with volume status information
        """
        try:
            devices = await self.device_manager.get_devices()
            volume_status = {}

            for device in devices.devices:
                if device.status == DeviceStatus.CONNECTED:
                    remote = await self.device_manager.get_connection(device.id)
                    if remote:
                        try:
                            # Get volume info
                            volume_info = await self._get_volume_info(remote)
                            volume_status[device.id] = volume_info
                        except Exception as e:
                            logger.warning(f"Could not get volume status for device {device.id}: {e}")

            return {"volume_status": volume_status}

        except Exception as e:
            logger.error(f"Error getting volume status: {e}")
            return {"error": str(e)}

    async def start_pairing(self, device_id: str) -> PairingResult:
        """Start pairing process with an Android TV device.
        
        Args:
            device_id: Device ID to pair with
            
        Returns:
            PairingResult with pairing status
        """
        return await self.device_manager.start_pairing(device_id)

    async def complete_pairing(self, device_id: str, pin: str) -> PairingResult:
        """Complete pairing process with PIN.
        
        Args:
            device_id: Device ID to complete pairing for
            pin: PIN code from Android TV
            
        Returns:
            PairingResult with pairing completion status
        """
        return await self.device_manager.complete_pairing(device_id, pin)

    async def unpair_device(self, device_id: str) -> CommandResult:
        """Unpair an Android TV device.
        
        Args:
            device_id: Device ID to unpair
            
        Returns:
            CommandResult with operation status
        """
        return await self.device_manager.unpair_device(device_id)

    async def get_pairing_status(self, device_id: str) -> Dict[str, Any]:
        """Get pairing status for a device.
        
        Args:
            device_id: Device ID to check
            
        Returns:
            Dictionary with pairing status information
        """
        try:
            device = await self.device_manager.get_device(device_id)
            if not device:
                return {"error": "Device not found"}

            is_paired = self.device_manager.is_device_paired(device_id)
            
            return {
                "device_id": device_id,
                "device_name": device.name,
                "is_paired": is_paired,
                "pairing_status": device.pairing_status,
                "connection_status": device.status
            }

        except Exception as e:
            logger.error(f"Error getting pairing status: {e}")
            return {"error": str(e)}

    async def get_paired_devices(self) -> Dict[str, Any]:
        """Get list of all paired devices.
        
        Returns:
            Dictionary with paired devices information
        """
        try:
            paired_device_ids = self.device_manager.get_paired_devices()
            paired_devices = []

            for device_id in paired_device_ids:
                device = await self.device_manager.get_device(device_id)
                if device:
                    paired_devices.append({
                        "device_id": device.id,
                        "device_name": device.name,
                        "host": device.host,
                        "port": device.port,
                        "status": device.status,
                        "pairing_status": device.pairing_status,
                        "last_seen": device.last_seen
                    })
                else:
                    # Device not currently discoverable but still paired
                    paired_devices.append({
                        "device_id": device_id,
                        "device_name": "Unknown (not discoverable)",
                        "host": "unknown",
                        "port": 0,
                        "status": "disconnected",
                        "pairing_status": "paired",
                        "last_seen": None
                    })

            return {
                "paired_devices": paired_devices,
                "total_paired": len(paired_devices)
            }

        except Exception as e:
            logger.error(f"Error getting paired devices: {e}")
            return {"error": str(e)}

    async def _get_device_apps(self, remote: AndroidTVRemote) -> List[AndroidTVApp]:
        """Get list of apps from Android TV device.
        
        Args:
            remote: AndroidTVRemote connection
            
        Returns:
            List of AndroidTVApp objects
        """
        try:
            # This is a placeholder implementation
            # The actual implementation would depend on the androidtvremote2 API
            apps_data = await remote.get_installed_apps()
            
            apps = []
            for app_data in apps_data:
                app = AndroidTVApp(
                    id=app_data.get("id", ""),
                    name=app_data.get("name", "Unknown"),
                    package_name=app_data.get("package_name", ""),
                    version=app_data.get("version"),
                    is_running=app_data.get("is_running", False),
                    is_system_app=app_data.get("is_system_app", False),
                    icon_url=app_data.get("icon_url")
                )
                apps.append(app)
            
            return apps
            
        except Exception as e:
            logger.error(f"Error getting device apps: {e}")
            return []

    async def _get_playback_state(self, remote: AndroidTVRemote, device_id: str) -> Optional[PlaybackState]:
        """Get current playback state from device.
        
        Args:
            remote: AndroidTVRemote connection
            device_id: Device ID
            
        Returns:
            PlaybackState object or None
        """
        try:
            # This is a placeholder implementation
            # The actual implementation would depend on the androidtvremote2 API
            state_data = await remote.get_playback_state()
            
            return PlaybackState(
                device_id=device_id,
                is_playing=state_data.get("is_playing", False),
                is_paused=state_data.get("is_paused", False),
                current_app=state_data.get("current_app"),
                title=state_data.get("title"),
                artist=state_data.get("artist"),
                duration=state_data.get("duration"),
                position=state_data.get("position"),
                volume=state_data.get("volume"),
                is_muted=state_data.get("is_muted", False)
            )
            
        except Exception as e:
            logger.error(f"Error getting playback state: {e}")
            return None

    async def _get_current_app(self, remote: AndroidTVRemote) -> Optional[Dict[str, Any]]:
        """Get current active app from device.
        
        Args:
            remote: AndroidTVRemote connection
            
        Returns:
            Dictionary with current app info or None
        """
        try:
            # This is a placeholder implementation
            app_data = await remote.get_current_app()
            return app_data
            
        except Exception as e:
            logger.error(f"Error getting current app: {e}")
            return None

    async def _get_volume_info(self, remote: AndroidTVRemote) -> Dict[str, Any]:
        """Get volume information from device.
        
        Args:
            remote: AndroidTVRemote connection
            
        Returns:
            Dictionary with volume info
        """
        try:
            # This is a placeholder implementation
            volume_data = await remote.get_volume_info()
            return {
                "level": volume_data.get("level", 0),
                "is_muted": volume_data.get("is_muted", False),
                "max_level": volume_data.get("max_level", 100)
            }
            
        except Exception as e:
            logger.error(f"Error getting volume info: {e}")
            return {"level": 0, "is_muted": False, "max_level": 100}
