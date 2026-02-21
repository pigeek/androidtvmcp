"""Chromecast controller for Canvas casting with custom messaging."""

import asyncio
import logging
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse
from uuid import UUID

import pychromecast
from pychromecast.controllers import BaseController
from pychromecast.socket_client import CastStatus

logger = logging.getLogger(__name__)

# Custom namespace for Canvas communication
CANVAS_NAMESPACE = "urn:x-cast:com.nanobot.canvas"

# Default receiver URL and App ID
DEFAULT_RECEIVER_URL = "https://uijit.com/canvas-receiver"
DEFAULT_APP_ID = "BE2EA00B"  # Registered Canvas receiver app


class CastState(str, Enum):
    """Cast connection states."""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CASTING = "casting"
    ERROR = "error"


@dataclass
class CastSession:
    """Represents an active cast session."""
    device_name: str
    device_host: str
    surface_id: str
    canvas_server_url: str
    state: CastState
    receiver_url: str


class CanvasController(BaseController):
    """Custom Cast controller for Canvas communication.

    This controller handles the custom namespace messages between
    the sender (this MCP server) and the receiver app running on Chromecast.
    """

    def __init__(self, app_id: str = DEFAULT_APP_ID):
        super().__init__(CANVAS_NAMESPACE, app_id)
        self._message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._connected = False

    def receive_message(self, message: Dict[str, Any], data: Any) -> bool:
        """Handle incoming messages from the receiver.

        Args:
            message: The message payload
            data: Additional data

        Returns:
            True if the message was handled
        """
        logger.debug(f"Received Canvas message: {message}")

        if self._message_callback:
            self._message_callback(message)

        return True

    def set_message_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set a callback for incoming messages.

        Args:
            callback: Function to call when messages are received
        """
        self._message_callback = callback

    def connect_canvas(self, canvas_server_url: str, surface_id: str) -> None:
        """Send connect message to receiver with canvas server details.

        Args:
            canvas_server_url: WebSocket URL of the Canvas server (base or full)
            surface_id: Canvas surface ID to connect to
        """
        # Normalize to base URL (scheme://host:port) — the receiver appends /ws/{surfaceId}
        parsed = urlparse(canvas_server_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        message = {
            "type": "connect",
            "canvasServerUrl": base_url,
            "surfaceId": surface_id
        }
        logger.info(f"Sending Canvas connect message: {message}")
        self.send_message(message)
        self._connected = True

    def disconnect_canvas(self) -> None:
        """Send disconnect message to receiver."""
        message = {"type": "disconnect"}
        logger.info("Sending Canvas disconnect message")
        self.send_message(message)
        self._connected = False

    def ping(self) -> None:
        """Send ping message to check receiver status."""
        message = {"type": "ping"}
        self.send_message(message)

    @property
    def is_canvas_connected(self) -> bool:
        """Check if canvas is connected."""
        return self._connected


class ChromecastController:
    """Manages Chromecast connections and Canvas casting.

    This controller handles:
    - Finding Chromecast devices by IP (using existing Android TV discovery)
    - Launching the Canvas receiver app
    - Sending custom messages to connect to Canvas server
    - Managing cast sessions
    """

    def __init__(
        self,
        receiver_url: str = DEFAULT_RECEIVER_URL,
        app_id: str = DEFAULT_APP_ID
    ):
        """Initialize the Chromecast controller.

        Args:
            receiver_url: URL of the hosted Canvas receiver app
            app_id: Registered Chromecast App ID for the receiver
        """
        self.receiver_url = receiver_url
        self.app_id = app_id
        self._cast_devices: Dict[str, pychromecast.Chromecast] = {}
        self._canvas_controllers: Dict[str, CanvasController] = {}
        self._sessions: Dict[str, CastSession] = {}
        self._lock = asyncio.Lock()

    async def cast_to_device(
        self,
        host: str,
        canvas_server_url: str,
        surface_id: str,
        device_name: Optional[str] = None,
        timeout: float = 15.0
    ) -> Dict[str, Any]:
        """Cast a Canvas surface to a Chromecast device.

        On connection failure, cleans up stale state and retries once with
        a fresh connection, avoiding the need to restart the server.

        Args:
            host: IP address of the Chromecast device
            canvas_server_url: WebSocket URL of the Canvas server
            surface_id: Canvas surface ID to display
            device_name: Friendly name for the device (optional)
            timeout: Connection timeout in seconds

        Returns:
            Dictionary with cast result
        """
        async with self._lock:
            result = await self._try_cast(host, canvas_server_url, surface_id, device_name, timeout)

            if not result["success"] and result.get("error_code") == "CONNECTION_FAILED":
                # Clean up all stale state for this host and retry once
                logger.info(f"First cast attempt to {host} failed, cleaning up and retrying")
                self._cleanup_device_state(host)
                result = await self._try_cast(host, canvas_server_url, surface_id, device_name, timeout)

            return result

    def _cleanup_device_state(self, host: str) -> None:
        """Clean up all cached state for a device host.

        Disconnects any stale pychromecast instance and removes
        associated controllers and sessions.
        """
        if host in self._cast_devices:
            try:
                self._cast_devices[host].disconnect()
            except Exception:
                pass
            del self._cast_devices[host]
        self._canvas_controllers.pop(host, None)
        self._sessions.pop(host, None)

    async def _try_cast(
        self,
        host: str,
        canvas_server_url: str,
        surface_id: str,
        device_name: Optional[str] = None,
        timeout: float = 15.0
    ) -> Dict[str, Any]:
        """Single attempt to cast a Canvas surface to a Chromecast device."""
        try:
            logger.info(f"Starting cast to {host} for surface {surface_id}")

            # Get or create Chromecast connection
            cast = await self._get_or_connect_device(host, timeout)
            if not cast:
                return {
                    "success": False,
                    "error": f"Failed to connect to device at {host}",
                    "error_code": "CONNECTION_FAILED"
                }

            device_name = device_name or cast.name or host

            # Create and register Canvas controller
            canvas_ctrl = CanvasController(app_id=self.app_id)
            cast.register_handler(canvas_ctrl)
            self._canvas_controllers[host] = canvas_ctrl

            # Launch the receiver app and wait for it to be ready
            logger.info(f"Launching Canvas receiver on {device_name} (App ID: {self.app_id})")
            await self._launch_app_and_wait(cast, self.app_id, timeout=15.0)

            # Send connect message with Canvas server details
            canvas_ctrl.connect_canvas(canvas_server_url, surface_id)

            # Store session
            self._sessions[host] = CastSession(
                device_name=device_name,
                device_host=host,
                surface_id=surface_id,
                canvas_server_url=canvas_server_url,
                state=CastState.CASTING,
                receiver_url=self.receiver_url
            )

            logger.info(f"Successfully casting to {device_name}")
            return {
                "success": True,
                "device_name": device_name,
                "device_host": host,
                "surface_id": surface_id,
                "message": f"Casting to {device_name}"
            }

        except Exception as e:
            logger.error(f"Error casting to {host}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "CAST_ERROR"
            }

    async def stop_cast(self, host: str) -> Dict[str, Any]:
        """Stop casting on a device.

        Args:
            host: IP address of the Chromecast device

        Returns:
            Dictionary with stop result
        """
        async with self._lock:
            try:
                # Send disconnect message if controller exists
                if host in self._canvas_controllers:
                    canvas_ctrl = self._canvas_controllers[host]
                    canvas_ctrl.disconnect_canvas()
                    del self._canvas_controllers[host]

                # Stop the app on the device
                if host in self._cast_devices:
                    cast = self._cast_devices[host]
                    cast.quit_app()

                # Remove session
                session = self._sessions.pop(host, None)
                device_name = session.device_name if session else host

                logger.info(f"Stopped casting on {device_name}")
                return {
                    "success": True,
                    "device_name": device_name,
                    "message": f"Stopped casting on {device_name}"
                }

            except Exception as e:
                logger.error(f"Error stopping cast on {host}: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "error_code": "STOP_ERROR"
                }

    async def get_cast_status(self, host: str) -> Dict[str, Any]:
        """Get casting status for a device.

        Args:
            host: IP address of the Chromecast device

        Returns:
            Dictionary with cast status
        """
        try:
            session = self._sessions.get(host)

            if not session:
                return {
                    "casting": False,
                    "device_host": host,
                    "state": CastState.IDLE.value
                }

            # Check if device is still connected
            is_connected = False
            if host in self._cast_devices:
                cast = self._cast_devices[host]
                is_connected = cast.socket_client.is_connected

            return {
                "casting": True,
                "device_name": session.device_name,
                "device_host": session.device_host,
                "surface_id": session.surface_id,
                "canvas_server_url": session.canvas_server_url,
                "state": session.state.value,
                "connected": is_connected
            }

        except Exception as e:
            logger.error(f"Error getting cast status for {host}: {e}")
            return {
                "casting": False,
                "device_host": host,
                "error": str(e)
            }

    async def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active cast sessions.

        Returns:
            Dictionary mapping device host to session info
        """
        result = {}
        for host, session in self._sessions.items():
            result[host] = {
                "device_name": session.device_name,
                "device_host": session.device_host,
                "surface_id": session.surface_id,
                "state": session.state.value
            }
        return result

    async def _get_or_connect_device(
        self,
        host: str,
        timeout: float = 15.0
    ) -> Optional[pychromecast.Chromecast]:
        """Get existing connection or create new one.

        Connects directly by IP using get_chromecast_from_host (no zeroconf/mDNS).
        Properly cleans up pychromecast instances on timeout to prevent leaked
        background threads that accumulate and require server restarts.

        Args:
            host: IP address of the device
            timeout: Connection timeout

        Returns:
            Chromecast instance or None
        """
        # Check if we already have a healthy connection
        if host in self._cast_devices:
            cast = self._cast_devices[host]
            if cast.socket_client.is_connected:
                return cast
            # Connection lost — disconnect cleanly and reconnect
            logger.info(f"Stale connection to {host}, reconnecting")
            try:
                cast.disconnect()
            except Exception:
                pass
            del self._cast_devices[host]
            # Also clean up associated controllers/sessions
            self._canvas_controllers.pop(host, None)
            self._sessions.pop(host, None)

        try:
            logger.info(f"Connecting to Chromecast at {host} (timeout: {timeout}s)")

            loop = asyncio.get_event_loop()

            # Use a list to capture the pychromecast instance from the executor
            # so we can clean it up on timeout (prevents leaked background threads)
            cast_holder: list = []

            def _blocking_connect():
                """Connect directly by IP — no zeroconf needed."""
                _cast = pychromecast.get_chromecast_from_host(
                    (host, 8009, UUID(int=0), None, None),
                    timeout=timeout,
                )
                cast_holder.append(_cast)
                _cast.wait(timeout=timeout)
                return _cast

            try:
                cast = await asyncio.wait_for(
                    loop.run_in_executor(None, _blocking_connect),
                    timeout=timeout + 2  # small buffer over internal timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout connecting to Chromecast at {host} after {timeout}s")
                # Clean up the leaked pychromecast instance to stop its background thread
                if cast_holder:
                    try:
                        cast_holder[0].disconnect()
                        logger.debug(f"Cleaned up timed-out pychromecast instance for {host}")
                    except Exception:
                        pass
                return None

            self._cast_devices[host] = cast
            logger.info(f"Connected to Chromecast: {cast.name or host}")

            return cast

        except Exception as e:
            logger.error(f"Failed to connect to Chromecast at {host}: {e}")
            return None

    async def _launch_app_and_wait(
        self,
        cast: pychromecast.Chromecast,
        app_id: str,
        timeout: float = 15.0
    ) -> bool:
        """Launch an app and wait for it to be ready.

        Args:
            cast: Chromecast instance
            app_id: App ID to launch
            timeout: Maximum time to wait for app launch

        Returns:
            True if app launched successfully

        Raises:
            TimeoutError: If app doesn't launch within timeout
            RuntimeError: If app fails to start
        """
        loop = asyncio.get_event_loop()
        app_ready = asyncio.Event()

        class AppLaunchListener:
            """Listener to detect when app has launched."""
            def __init__(self, target_app_id: str, event: asyncio.Event, loop):
                self.target_app_id = target_app_id
                self.event = event
                self.loop = loop

            def new_cast_status(self, status: CastStatus):
                """Called when cast status changes."""
                if status.app_id == self.target_app_id:
                    logger.info(f"App {self.target_app_id} is now running")
                    self.loop.call_soon_threadsafe(self.event.set)

        listener = AppLaunchListener(app_id, app_ready, loop)
        cast.register_status_listener(listener)

        try:
            # Check if app is already running
            if cast.status and cast.status.app_id == app_id:
                logger.info(f"App {app_id} is already running")
                return True

            # Launch the app
            logger.info(f"Calling start_app({app_id}) on {cast.name}")
            try:
                cast.start_app(app_id)
            except Exception as e:
                logger.error(f"start_app raised exception: {type(e).__name__}: {e}")
                raise RuntimeError(f"Failed to start app {app_id}: {type(e).__name__}: {e}")

            # Wait for app to be ready
            try:
                await asyncio.wait_for(app_ready.wait(), timeout=timeout)
                logger.info(f"App {app_id} launched successfully")
                return True
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for app {app_id} to launch")
                raise TimeoutError(f"App {app_id} did not launch within {timeout}s")

        finally:
            # Unregister listener (pychromecast doesn't have unregister, but listener will be garbage collected)
            pass

    async def disconnect_all(self) -> None:
        """Disconnect from all Chromecast devices."""
        async with self._lock:
            for host in list(self._sessions.keys()):
                try:
                    await self.stop_cast(host)
                except Exception as e:
                    logger.error(f"Error stopping cast on {host}: {e}")

            for host, cast in list(self._cast_devices.items()):
                try:
                    cast.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting from {host}: {e}")

            self._cast_devices.clear()
            self._canvas_controllers.clear()
            self._sessions.clear()
