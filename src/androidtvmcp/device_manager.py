"""Device manager for Android TV discovery and connection management."""

import asyncio
import logging
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf
from androidtvremote2 import AndroidTVRemote

from .models import (
    AndroidTVDevice,
    DeviceStatus,
    PairingStatus,
    DiscoveryResult,
    DeviceListResponse,
    CommandResult,
    PairingCommand,
    PairingResult,
    DeviceCertificate,
)

logger = logging.getLogger(__name__)


class AndroidTVServiceListener(ServiceListener):
    """Service listener for Android TV device discovery."""

    def __init__(self, device_manager: "DeviceManager", loop: asyncio.AbstractEventLoop):
        """Initialize the service listener.
        
        Args:
            device_manager: Reference to the device manager
            loop: The event loop to schedule coroutines on
        """
        self.device_manager = device_manager
        self.loop = loop

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a new Android TV service is discovered."""
        info = zc.get_service_info(type_, name)
        if info:
            asyncio.run_coroutine_threadsafe(
                self.device_manager._handle_discovered_device(info), 
                self.loop
            )

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when an Android TV service is removed."""
        asyncio.run_coroutine_threadsafe(
            self.device_manager._handle_removed_device(name), 
            self.loop
        )

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when an Android TV service is updated."""
        info = zc.get_service_info(type_, name)
        if info:
            asyncio.run_coroutine_threadsafe(
                self.device_manager._handle_updated_device(info), 
                self.loop
            )


class DeviceManager:
    """Manages Android TV device discovery and connections."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the device manager.
        
        Args:
            config: Device configuration dictionary
        """
        self.config = config
        self.devices: Dict[str, AndroidTVDevice] = {}
        self.connections: Dict[str, AndroidTVRemote] = {}
        self.zeroconf: Optional[Zeroconf] = None
        self.browser: Optional[ServiceBrowser] = None
        self.listener: Optional[AndroidTVServiceListener] = None
        self.discovery_running = False
        
        # Configuration
        self.discovery_config = config.get("discovery", {})
        self.connection_config = config.get("connection", {})
        
        # Discovery settings
        self.discovery_enabled = self.discovery_config.get("enabled", True)
        self.discovery_timeout = self.discovery_config.get("timeout", 10)
        self.discovery_interval = self.discovery_config.get("interval", 30)
        
        # Connection settings
        self.connection_timeout = self.connection_config.get("timeout", 5)
        self.retry_attempts = self.connection_config.get("retry_attempts", 3)
        self.retry_delay = self.connection_config.get("retry_delay", 1)
        
        # Certificate storage
        self.cert_dir = Path.home() / ".androidtv" / "certificates"
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing certificates
        self.certificates: Dict[str, DeviceCertificate] = {}
        self.paired_device_ids: set = set()
        self._load_certificates()

    async def start_discovery(self) -> None:
        """Start Android TV device discovery."""
        if not self.discovery_enabled:
            logger.info("Device discovery is disabled")
            return
            
        if self.discovery_running:
            logger.warning("Discovery is already running")
            return

        try:
            logger.info("Starting Android TV device discovery")
            
            # Use AsyncZeroconf instead of regular Zeroconf
            self.zeroconf = AsyncZeroconf()
            
            # Define the service state change handler
            def _async_on_service_state_change(
                zeroconf: Zeroconf,
                service_type: str,
                name: str,
                state_change: ServiceStateChange,
            ) -> None:
                if state_change is ServiceStateChange.Added:
                    asyncio.create_task(self._handle_discovered_service(zeroconf, service_type, name))
                elif state_change is ServiceStateChange.Removed:
                    asyncio.create_task(self._handle_removed_device(name))
                elif state_change is ServiceStateChange.Updated:
                    asyncio.create_task(self._handle_updated_service(zeroconf, service_type, name))
            
            # Focus specifically on Android TV remote service
            service_types = ["_androidtvremote2._tcp.local."]
            
            self.browser = AsyncServiceBrowser(
                self.zeroconf.zeroconf,
                service_types,
                handlers=[_async_on_service_state_change]
            )
            
            self.discovery_running = True
            logger.info("Android TV device discovery started")
            
        except Exception as e:
            logger.error(f"Failed to start device discovery: {e}")
            # Ensure cleanup on failure
            try:
                await self.stop_discovery()
            except Exception as cleanup_error:
                logger.error(f"Error during discovery cleanup: {cleanup_error}")
            # Don't re-raise the exception to prevent server crash
            # The server should continue running even if discovery fails

    async def stop_discovery(self) -> None:
        """Stop Android TV device discovery."""
        if not self.discovery_running:
            return

        try:
            logger.info("Stopping Android TV device discovery")
            
            if self.browser:
                await self.browser.async_cancel()
                self.browser = None
                
            if self.zeroconf:
                await self.zeroconf.async_close()
                self.zeroconf = None
                
            self.discovery_running = False
            
            logger.info("Android TV device discovery stopped")
            
        except Exception as e:
            logger.error(f"Error stopping device discovery: {e}")

    async def _handle_discovered_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Handle a newly discovered Android TV service."""
        try:
            # Get service info asynchronously
            info = AsyncServiceInfo(service_type, name)
            await info.async_request(zeroconf, 3000)
            
            if not info:
                logger.debug(f"No info available for service: {name}")
                return
            
            # Get addresses first
            addresses = info.parsed_scoped_addresses()
            if not addresses:
                logger.debug(f"No addresses found for device: {name}")
                return
            
            # Use the first address
            host = addresses[0]
            port = info.port or 6466
            
            # Generate consistent device ID from host:port
            device_id = self._generate_device_id(host, port)
            
            # Check if device already exists
            if device_id in self.devices:
                await self._update_device_last_seen(device_id)
                # Update host/port if changed
                device = self.devices[device_id]
                if device.host != host or device.port != port:
                    device.host = host
                    device.port = port
                    logger.info(f"Updated device address: {device.name} ({host}:{port})")
                return
            
            # Extract properties
            properties = {}
            if info.properties:
                for key, value in info.properties.items():
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    properties[key] = value
            
            # Determine initial pairing status based on stored certificates
            initial_pairing_status = PairingStatus.PAIRED if device_id in self.paired_device_ids else PairingStatus.NOT_PAIRED
            initial_device_status = DeviceStatus.DISCONNECTED if device_id in self.paired_device_ids else DeviceStatus.PAIRING_REQUIRED
            
            # Create new device
            device = AndroidTVDevice(
                id=device_id,
                name=self._extract_device_name_from_properties(properties, name),
                host=host,
                port=port,
                model=properties.get('md', properties.get('model')),
                version=properties.get('vs', properties.get('version')),
                status=initial_device_status,
                pairing_status=initial_pairing_status,
                capabilities=self._extract_capabilities_from_properties(properties),
                last_seen=datetime.now(timezone.utc).isoformat()
            )
            
            self.devices[device_id] = device
            logger.info(f"Discovered new Android TV device: {device.name} ({device_id}) at {host}:{port}")
            
            # Attempt to connect to the device
            await self._attempt_connection(device_id)
            
        except Exception as e:
            logger.error(f"Error handling discovered service: {e}")

    async def _handle_updated_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Handle an updated Android TV service."""
        try:
            # Similar to _handle_discovered_service but for updates
            await self._handle_discovered_service(zeroconf, service_type, name)
        except Exception as e:
            logger.error(f"Error handling updated service: {e}")

    async def _handle_discovered_device(self, service_info) -> None:
        """Handle a newly discovered Android TV device."""
        try:
            # Extract device information from service info
            device_id = self._extract_device_id(service_info)
            if not device_id:
                return

            # Check if device already exists
            if device_id in self.devices:
                await self._update_device_last_seen(device_id)
                return

            # Create new device
            device = AndroidTVDevice(
                id=device_id,
                name=self._extract_device_name(service_info),
                host=self._extract_host(service_info),
                port=self._extract_port(service_info),
                model=self._extract_model(service_info),
                version=self._extract_version(service_info),
                status=DeviceStatus.DISCONNECTED,
                capabilities=self._extract_capabilities(service_info),
                last_seen=datetime.now(timezone.utc).isoformat()
            )

            self.devices[device_id] = device
            logger.info(f"Discovered new Android TV device: {device.name} ({device_id})")

            # Attempt to connect to the device
            await self._attempt_connection(device_id)

        except Exception as e:
            logger.error(f"Error handling discovered device: {e}")

    async def _handle_removed_device(self, service_name: str) -> None:
        """Handle a removed Android TV device."""
        try:
            device_id = self._extract_device_id_from_name(service_name)
            if device_id and device_id in self.devices:
                device = self.devices[device_id]
                device.status = DeviceStatus.DISCONNECTED
                
                # Close connection if exists
                if device_id in self.connections:
                    await self._disconnect_device(device_id)
                
                logger.info(f"Android TV device removed: {device.name} ({device_id})")

        except Exception as e:
            logger.error(f"Error handling removed device: {e}")

    async def _handle_updated_device(self, service_info) -> None:
        """Handle an updated Android TV device."""
        try:
            device_id = self._extract_device_id(service_info)
            if device_id and device_id in self.devices:
                await self._update_device_last_seen(device_id)
                logger.debug(f"Updated Android TV device: {device_id}")

        except Exception as e:
            logger.error(f"Error handling updated device: {e}")

    async def _attempt_connection(self, device_id: str) -> bool:
        """Attempt to connect to an Android TV device.
        
        Args:
            device_id: Device ID to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        if device_id not in self.devices:
            return False

        device = self.devices[device_id]
        
        # Check if device has certificate for connection
        if device_id in self.certificates:
            logger.info(f"Found certificate for {device.name}, attempting connection")
            device.pairing_status = PairingStatus.PAIRED
            success = await self._attempt_connection_with_cert(device_id)
            if success:
                logger.info(f"Successfully connected to paired device: {device.name}")
                return True
        
        # Device requires pairing
        logger.info(f"Android TV device found but requires pairing: {device.name} ({device_id})")
        device.status = DeviceStatus.PAIRING_REQUIRED
        device.pairing_status = PairingStatus.NOT_PAIRED
        return False


    async def _disconnect_device(self, device_id: str) -> None:
        """Disconnect from an Android TV device.
        
        Args:
            device_id: Device ID to disconnect from
        """
        if device_id in self.connections:
            try:
                remote = self.connections[device_id]
                await remote.disconnect()
                del self.connections[device_id]
                
                if device_id in self.devices:
                    self.devices[device_id].status = DeviceStatus.DISCONNECTED
                    
                logger.info(f"Disconnected from device {device_id}")
                
            except Exception as e:
                logger.error(f"Error disconnecting from device {device_id}: {e}")

    async def _update_device_last_seen(self, device_id: str) -> None:
        """Update the last seen timestamp for a device.
        
        Args:
            device_id: Device ID to update
        """
        if device_id in self.devices:
            self.devices[device_id].last_seen = datetime.now(timezone.utc).isoformat()

    def _extract_device_id(self, service_info) -> Optional[str]:
        """Extract device ID from service info."""
        # Implementation depends on the actual service info structure
        # This is a placeholder implementation
        if hasattr(service_info, 'properties'):
            props = service_info.properties
            if b'id' in props:
                return props[b'id'].decode('utf-8')
        
        # Fallback to using service name or address
        if hasattr(service_info, 'name'):
            return service_info.name.split('.')[0]
        
        return None

    def _extract_device_name(self, service_info) -> str:
        """Extract device name from service info."""
        if hasattr(service_info, 'properties'):
            props = service_info.properties
            if b'fn' in props:
                return props[b'fn'].decode('utf-8')
            if b'name' in props:
                return props[b'name'].decode('utf-8')
        
        if hasattr(service_info, 'name'):
            return service_info.name.split('.')[0]
        
        return "Unknown Android TV"

    def _extract_host(self, service_info) -> str:
        """Extract host address from service info."""
        if hasattr(service_info, 'addresses') and service_info.addresses:
            import socket
            return socket.inet_ntoa(service_info.addresses[0])
        return "unknown"

    def _extract_port(self, service_info) -> int:
        """Extract port from service info."""
        if hasattr(service_info, 'port'):
            return service_info.port
        return 6466  # Default Android TV remote port

    def _extract_model(self, service_info) -> Optional[str]:
        """Extract device model from service info."""
        if hasattr(service_info, 'properties'):
            props = service_info.properties
            if b'md' in props:
                return props[b'md'].decode('utf-8')
            if b'model' in props:
                return props[b'model'].decode('utf-8')
        return None

    def _extract_version(self, service_info) -> Optional[str]:
        """Extract device version from service info."""
        if hasattr(service_info, 'properties'):
            props = service_info.properties
            if b'vs' in props:
                return props[b'vs'].decode('utf-8')
            if b'version' in props:
                return props[b'version'].decode('utf-8')
        return None

    def _extract_capabilities(self, service_info) -> List[str]:
        """Extract device capabilities from service info."""
        capabilities = []
        if hasattr(service_info, 'properties'):
            props = service_info.properties
            if b'features' in props:
                features = props[b'features'].decode('utf-8')
                capabilities = features.split(',')
        return capabilities

    def _extract_device_id_from_name(self, service_name: str) -> Optional[str]:
        """Extract device ID from service name."""
        return service_name.split('.')[0]
    
    def _generate_device_id(self, host: str, port: int) -> str:
        """Generate a consistent device ID from host and port.
        
        This ensures the same device gets the same ID during discovery and pairing.
        
        Args:
            host: Device host address
            port: Device port
            
        Returns:
            Consistent device ID
        """
        import hashlib
        device_key = f"{host}:{port}"
        return hashlib.md5(device_key.encode()).hexdigest()

    def _extract_device_name_from_properties(self, properties: dict, fallback_name: str) -> str:
        """Extract device name from properties."""
        # Try common property names for device name
        for key in ['fn', 'name', 'n', 'device_name']:
            if key in properties:
                return properties[key]
        
        # Fallback to service name
        return fallback_name.split('.')[0]

    def _extract_capabilities_from_properties(self, properties: dict) -> List[str]:
        """Extract device capabilities from properties."""
        capabilities = []
        
        # Check for features property
        if 'features' in properties:
            features = properties['features']
            capabilities = features.split(',')
        
        # Add other capability indicators
        for key in ['ca', 'capabilities']:
            if key in properties:
                cap_value = properties[key]
                if isinstance(cap_value, str):
                    capabilities.extend(cap_value.split(','))
        
        return capabilities

    async def get_devices(self) -> DeviceListResponse:
        """Get list of all discovered Android TV devices.
        
        Returns:
            DeviceListResponse with Android TV device information
        """
        # All devices are now Android TV devices since we're only discovering that service type
        all_devices = list(self.devices.values())
        
        connected = sum(1 for d in all_devices if d.status == DeviceStatus.CONNECTED)
        disconnected = len(all_devices) - connected
        
        return DeviceListResponse(
            devices=all_devices,
            total=len(all_devices),
            connected=connected,
            disconnected=disconnected
        )

    async def get_device(self, device_id: str) -> Optional[AndroidTVDevice]:
        """Get a specific device by ID.
        
        Args:
            device_id: Device ID to retrieve
            
        Returns:
            AndroidTVDevice if found, None otherwise
        """
        return self.devices.get(device_id)

    async def get_connection(self, device_id: Optional[str] = None) -> Optional[AndroidTVRemote]:
        """Get connection to a device.
        
        Args:
            device_id: Device ID to get connection for. If None, returns first available connection.
            
        Returns:
            AndroidTVRemote connection if available, None otherwise
        """
        if device_id:
            return self.connections.get(device_id)
        
        # Return first available connection if no device_id specified
        if self.connections:
            return next(iter(self.connections.values()))
        
        return None

    async def ensure_connection(self, device_id: Optional[str] = None) -> Optional[AndroidTVRemote]:
        """Ensure connection to a device, attempting to connect if needed.
        
        Args:
            device_id: Device ID to ensure connection for
            
        Returns:
            AndroidTVRemote connection if successful, None otherwise
        """
        # If no device_id specified, use first paired device
        if not device_id:
            paired_devices = self.get_paired_devices()
            if paired_devices:
                device_id = paired_devices[0]
            elif self.devices:
                # Fallback to first available device
                device_id = next(iter(self.devices.keys()))
        
        if not device_id:
            logger.warning("No device ID provided and no devices available")
            return None

        # Check if device exists
        if device_id not in self.devices:
            logger.warning(f"Device {device_id} not found in discovered devices")
            return None

        device = self.devices[device_id]
        logger.debug(f"Ensuring connection to device: {device.name} ({device_id})")

        # Check if already connected and connection is valid
        connection = await self.get_connection(device_id)
        if connection:
            try:
                # Test if connection is still valid by checking if it's connected
                if hasattr(connection, 'is_connected') and connection.is_connected:
                    logger.debug(f"Using existing valid connection to {device_id}")
                    return connection
                elif hasattr(connection, '_connected') and connection._connected:
                    logger.debug(f"Using existing valid connection to {device_id}")
                    return connection
                else:
                    logger.debug(f"Existing connection to {device_id} is not valid, reconnecting")
                    # Remove invalid connection
                    del self.connections[device_id]
            except Exception as e:
                logger.debug(f"Error checking connection validity for {device_id}: {e}")
                # Remove problematic connection
                if device_id in self.connections:
                    del self.connections[device_id]

        # Check if device is paired
        if not self.is_device_paired(device_id):
            logger.warning(f"Device {device_id} is not paired, cannot establish connection")
            device.status = DeviceStatus.PAIRING_REQUIRED
            return None

        # Attempt to connect with certificate
        logger.info(f"Attempting to connect to {device.name} ({device_id})")
        if await self._attempt_connection_with_cert(device_id):
            connection = await self.get_connection(device_id)
            if connection:
                logger.info(f"Successfully established connection to {device.name}")
                return connection
        
        logger.error(f"Failed to establish connection to {device_id}")
        return None

    async def refresh_devices(self) -> DiscoveryResult:
        """Refresh device discovery.
        
        Returns:
            DiscoveryResult with discovery information
        """
        # For now, just return current devices
        # In a full implementation, this might trigger a new discovery scan
        devices = list(self.devices.values())
        
        return DiscoveryResult(
            devices=devices,
            discovery_time=datetime.now(timezone.utc).isoformat(),
            total_found=len(devices)
        )

    def _load_certificates(self) -> None:
        """Load existing certificates from storage."""
        try:
            cert_file = self.cert_dir / "certificates.json"
            if cert_file.exists():
                with open(cert_file, 'r') as f:
                    cert_data = json.load(f)
                    logger.debug(f"Loading certificate data: {cert_data}")
                    for device_id, cert_info in cert_data.items():
                        logger.debug(f"Loading certificate for device {device_id}")
                        self.certificates[device_id] = DeviceCertificate(**cert_info)
                        self.paired_device_ids.add(device_id)
                logger.info(f"Loaded {len(self.certificates)} certificates for paired devices: {list(self.paired_device_ids)}")
            else:
                logger.info("No existing certificates file found")
        except Exception as e:
            logger.error(f"Error loading certificates: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

    def _save_certificates(self) -> None:
        """Save certificates to storage."""
        try:
            cert_file = self.cert_dir / "certificates.json"
            cert_data = {}
            
            logger.debug(f"Saving {len(self.certificates)} certificates to {cert_file}")
            
            for device_id, cert in self.certificates.items():
                logger.debug(f"Serializing certificate for device {device_id}")
                # Use model_dump() instead of deprecated dict() method
                cert_data[device_id] = cert.model_dump()
            
            logger.debug(f"Certificate data to save: {cert_data}")
            
            with open(cert_file, 'w') as f:
                json.dump(cert_data, f, indent=2)
            
            logger.info(f"Successfully saved {len(cert_data)} certificates to {cert_file}")
            
        except Exception as e:
            logger.error(f"Error saving certificates: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

    async def start_pairing(self, device_id: str) -> PairingResult:
        """Start pairing process with an Android TV device.
        
        Args:
            device_id: Device ID to pair with
            
        Returns:
            PairingResult with pairing status
        """
        if device_id not in self.devices:
            return PairingResult(
                success=False,
                message=f"Device not found: {device_id}",
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code="DEVICE_NOT_FOUND"
            )

        device = self.devices[device_id]

        try:
            device.status = DeviceStatus.PAIRING
            device.pairing_status = PairingStatus.PAIRING
            
            logger.info(f"Starting pairing with {device.name} ({device_id})")
            
            # Create temporary certificate files for pairing
            temp_cert_file = self.cert_dir / f"temp_{device_id}.crt"
            temp_key_file = self.cert_dir / f"temp_{device_id}.key"
            
            # Create AndroidTVRemote for pairing
            remote = AndroidTVRemote(
                client_name="androidtvmcp",
                certfile=str(temp_cert_file),
                keyfile=str(temp_key_file),
                host=device.host,
                # api_port=device.port,
                # pair_port=6467  # Standard Android TV pairing port
            )
            
            # Generate certificates if missing
            await remote.async_generate_cert_if_missing()
            
            # Store remote for completion
            self._pairing_remotes = getattr(self, '_pairing_remotes', {})
            self._pairing_remotes[device_id] = remote
            
            # Start pairing process
            await remote.async_start_pairing()
            
            return PairingResult(
                success=True,
                message=f"Pairing started with {device.name}. Please enter the PIN displayed on your TV.",
                device_id=device_id,
                status=PairingStatus.PAIRING,
                pin_required=True
            )
            
        except Exception as e:
            logger.error(f"Error starting pairing with {device_id}: {e}")
            device.status = DeviceStatus.ERROR
            device.pairing_status = PairingStatus.PAIRING_FAILED
            
            # Clean up temporary files
            try:
                temp_cert_file = self.cert_dir / f"temp_{device_id}.crt"
                temp_key_file = self.cert_dir / f"temp_{device_id}.key"
                if temp_cert_file.exists():
                    temp_cert_file.unlink()
                if temp_key_file.exists():
                    temp_key_file.unlink()
            except:
                pass
            
            return PairingResult(
                success=False,
                message=f"Failed to start pairing: {str(e)}",
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code="PAIRING_START_FAILED"
            )

    async def complete_pairing(self, device_id: str, pin: str) -> PairingResult:
        """Complete pairing process with PIN.
        
        Args:
            device_id: Device ID to complete pairing for
            pin: PIN code from Android TV
            
        Returns:
            PairingResult with pairing completion status
        """
        if device_id not in self.devices:
            logger.error(f"Device not found during pairing completion: {device_id}")
            return PairingResult(
                success=False,
                message=f"Device not found: {device_id}",
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code="DEVICE_NOT_FOUND"
            )

        device = self.devices[device_id]
        
        # Get the pairing remote that was started earlier
        pairing_remotes = getattr(self, '_pairing_remotes', {})
        if device_id not in pairing_remotes:
            logger.error(f"No active pairing session found for device {device_id} ({device.name})")
            return PairingResult(
                success=False,
                message=f"No active pairing session found for {device.name}. Please start pairing first.",
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code="NO_PAIRING_SESSION"
            )
        
        # Validate PIN format
        if not pin or not pin.strip():
            logger.error(f"Empty PIN provided for device {device_id}")
            return PairingResult(
                success=False,
                message="PIN cannot be empty",
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code="INVALID_PIN_FORMAT"
            )
        
        pin = pin.strip()
        
        if len(pin) < 4 or len(pin) > 6:
            logger.error(f"Invalid PIN length for device {device_id}: {len(pin)} characters")
            return PairingResult(
                success=False,
                message="PIN must be 4-6 digits long",
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code="INVALID_PIN_LENGTH"
            )
        
        try:
            # Log PIN details (masked for security)
            pin_masked = pin[:2] + "*" * (len(pin) - 2)
            logger.info(f"Completing pairing with {device.name} ({device_id}) using PIN: {pin_masked} (length: {len(pin)})")
            logger.debug(f"Device details - Host: {device.host}, Port: {device.port}")
            
            # Use the existing pairing remote
            remote = pairing_remotes[device_id]
            logger.debug(f"Using existing pairing remote for device {device_id}")
            
            # Complete pairing with PIN
            logger.debug(f"Calling async_finish_pairing with PIN for device {device_id}")
            await remote.async_finish_pairing(pin)
            logger.info(f"async_finish_pairing completed successfully for device {device_id}")
            
            # Read the generated certificate files
            temp_cert_file = self.cert_dir / f"temp_{device_id}.crt"
            temp_key_file = self.cert_dir / f"temp_{device_id}.key"
            
            logger.debug(f"Checking for certificate files: {temp_cert_file}, {temp_key_file}")
            
            if not temp_cert_file.exists() or not temp_key_file.exists():
                logger.error(f"Certificate files missing after pairing - cert exists: {temp_cert_file.exists()}, key exists: {temp_key_file.exists()}")
                raise Exception("Certificate files were not generated during pairing")
            
            logger.debug(f"Certificate files found, reading contents for device {device_id}")
            
            # Read certificate and key
            with open(temp_cert_file, 'r') as f:
                cert_content = f.read()
            with open(temp_key_file, 'r') as f:
                key_content = f.read()
            
            logger.debug(f"Certificate content length: {len(cert_content)}, Key content length: {len(key_content)}")            
            
            # Store certificate with consistent device ID
            certificate = DeviceCertificate(
                device_id=device_id,
                certificate=cert_content,
                private_key=key_content,
                created_at=datetime.now(timezone.utc).isoformat()
            )
            
            logger.debug(f"Created certificate object: {certificate}")
            
            self.certificates[device_id] = certificate
            self.paired_device_ids.add(device_id)
            logger.info(f"Certificate stored in memory for device {device_id}")
            logger.debug(f"Total certificates in memory: {len(self.certificates)}")
            logger.debug(f"Certificate keys: {list(self.certificates.keys())}")
            
            logger.info(f"About to save certificates to disk...")
            self._save_certificates()
            logger.info(f"Certificate save operation completed")
            
            # Clean up temporary files
            temp_cert_file.unlink()
            temp_key_file.unlink()
            logger.debug(f"Temporary certificate files cleaned up for device {device_id}")
            
            # Clean up pairing remote
            del pairing_remotes[device_id]
            logger.debug(f"Pairing remote cleaned up for device {device_id}")
            
            # Update device status
            device.status = DeviceStatus.DISCONNECTED
            device.pairing_status = PairingStatus.PAIRED
            
            logger.info(f"Successfully paired with {device.name} ({device_id})")
            
            # Attempt to connect now that we have certificates
            logger.debug(f"Attempting connection with certificate for device {device_id}")
            connection_success = await self._attempt_connection_with_cert(device_id)
            logger.info(f"Post-pairing connection attempt for {device_id}: {'successful' if connection_success else 'failed'}")
            
            return PairingResult(
                success=True,
                message=f"Successfully paired with {device.name}",
                device_id=device_id,
                status=PairingStatus.PAIRED
            )
            
        except Exception as e:
            # Enhanced error handling with specific error types
            error_message = str(e)
            error_code = "PAIRING_COMPLETION_FAILED"
            
            # Check for specific error types
            if "timeout" in error_message.lower():
                error_code = "PAIRING_TIMEOUT"
                error_message = f"Pairing timed out. The PIN may have expired. Please restart the pairing process. Original error: {error_message}"
            elif "invalid" in error_message.lower() and "pin" in error_message.lower():
                error_code = "INVALID_PIN"
                error_message = f"Invalid PIN. Please check the PIN displayed on your TV and try again. Original error: {error_message}"
            elif "connection" in error_message.lower():
                error_code = "CONNECTION_ERROR"
                error_message = f"Connection error during pairing. Please check your network connection. Original error: {error_message}"
            elif "certificate" in error_message.lower():
                error_code = "CERTIFICATE_ERROR"
                error_message = f"Certificate generation failed. Please try pairing again. Original error: {error_message}"
            
            logger.error(f"Error completing pairing with {device_id}: {error_message}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Log additional debugging information
            import traceback
            logger.debug(f"Full traceback for pairing error: {traceback.format_exc()}")
            
            device.status = DeviceStatus.ERROR
            device.pairing_status = PairingStatus.PAIRING_FAILED
            
            # Clean up temporary files and pairing remote
            try:
                temp_cert_file = self.cert_dir / f"temp_{device_id}.crt"
                temp_key_file = self.cert_dir / f"temp_{device_id}.key"
                if temp_cert_file.exists():
                    temp_cert_file.unlink()
                    logger.debug(f"Cleaned up temporary cert file: {temp_cert_file}")
                if temp_key_file.exists():
                    temp_key_file.unlink()
                    logger.debug(f"Cleaned up temporary key file: {temp_key_file}")
                if device_id in pairing_remotes:
                    del pairing_remotes[device_id]
                    logger.debug(f"Cleaned up pairing remote for device {device_id}")
            except Exception as cleanup_error:
                logger.warning(f"Error during cleanup after pairing failure: {cleanup_error}")
            
            return PairingResult(
                success=False,
                message=error_message,
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code=error_code
            )

    async def _attempt_connection_with_cert(self, device_id: str) -> bool:
        """Attempt to connect to device using stored certificate.
        
        Args:
            device_id: Device ID to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        if device_id not in self.devices or device_id not in self.certificates:
            return False

        device = self.devices[device_id]
        certificate = self.certificates[device_id]
        
        try:
            logger.info(f"Connecting to {device.name} with certificate")
            
            device.status = DeviceStatus.CONNECTING
            
            # Create temporary certificate files for connection
            cert_file = self.cert_dir / f"{device_id}.crt"
            key_file = self.cert_dir / f"{device_id}.key"
            
            # Write certificate and key to files
            with open(cert_file, 'w') as f:
                f.write(certificate.certificate)
            with open(key_file, 'w') as f:
                f.write(certificate.private_key)

            # Create AndroidTVRemote with certificate files
            remote = AndroidTVRemote(
                client_name="androidtvmcp",
                certfile=str(cert_file),
                keyfile=str(key_file),
                host=device.host,
                api_port=device.port
            )
            
            # Connect to device
            await remote.async_connect()
            
            # Store connection
            self.connections[device_id] = remote
            device.status = DeviceStatus.CONNECTED
            
            logger.info(f"Successfully connected to {device.name}")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"Error connecting to {device_id} with certificate: {e}")
            
            # Check for certificate-related errors that indicate the certificate is invalid
            certificate_error_indicators = [
                "certificate", "auth", "unauthorized", "permission", "denied",
                "ssl", "tls", "handshake", "verification", "invalid", "expired"
            ]
            
            is_certificate_error = any(indicator in error_str for indicator in certificate_error_indicators)
            
            if is_certificate_error:
                logger.warning(f"Certificate for {device.name} ({device_id}) appears to be invalid or rejected by TV, removing it")
                
                # Remove the invalid certificate
                if device_id in self.certificates:
                    del self.certificates[device_id]
                    self._save_certificates()
                    logger.info(f"Removed invalid certificate for device {device_id}")
                
                # Remove from paired device IDs
                if device_id in self.paired_device_ids:
                    self.paired_device_ids.remove(device_id)
                
                # Update device status to require pairing
                device.status = DeviceStatus.PAIRING_REQUIRED
                device.pairing_status = PairingStatus.NOT_PAIRED
                
                # Clean up certificate files
                self._cleanup_cert_files(device_id)
                
                logger.info(f"Device {device.name} now requires re-pairing due to invalid certificate")
            else:
                # For non-certificate errors (network issues, etc.), just mark as error
                device.status = DeviceStatus.ERROR
                logger.debug(f"Connection error for {device_id} appears to be network-related, keeping certificate")
            
            return False

    async def unpair_device(self, device_id: str) -> CommandResult:
        """Unpair a device by removing its certificate.
        
        Args:
            device_id: Device ID to unpair
            
        Returns:
            CommandResult with operation status
        """
        if device_id not in self.devices:
            return CommandResult(
                success=False,
                message=f"Device not found: {device_id}",
                error_code="DEVICE_NOT_FOUND",
                device_id=device_id
            )

        try:
            # Disconnect if connected
            if device_id in self.connections:
                await self._disconnect_device(device_id)
            
            # Remove certificate
            if device_id in self.certificates:
                del self.certificates[device_id]
                self._save_certificates()
            
            # Remove from paired device IDs
            if device_id in self.paired_device_ids:
                self.paired_device_ids.remove(device_id)
            
            # Update device status
            device = self.devices[device_id]
            device.status = DeviceStatus.PAIRING_REQUIRED
            device.pairing_status = PairingStatus.NOT_PAIRED
            
            logger.info(f"Unpaired device: {device.name}")
            
            return CommandResult(
                success=True,
                message=f"Successfully unpaired {device.name}",
                device_id=device_id
            )
            
        except Exception as e:
            logger.error(f"Error unpairing device {device_id}: {e}")
            return CommandResult(
                success=False,
                message=f"Failed to unpair device: {str(e)}",
                error_code="UNPAIR_FAILED",
                device_id=device_id
            )

    def is_device_paired(self, device_id: str) -> bool:
        """Check if a device is paired.
        
        Args:
            device_id: Device ID to check
            
        Returns:
            True if device is paired, False otherwise
        """
        return device_id in self.certificates

    def get_paired_devices(self) -> List[str]:
        """Get list of paired device IDs.
        
        Returns:
            List of paired device IDs
        """
        return list(self.certificates.keys())

    def _cleanup_cert_files(self, device_id: str) -> None:
        """Clean up certificate files for a device.
        
        Args:
            device_id: Device ID to clean up certificate files for
        """
        try:
            cert_file = self.cert_dir / f"{device_id}.crt"
            key_file = self.cert_dir / f"{device_id}.key"
            
            if cert_file.exists():
                cert_file.unlink()
                logger.debug(f"Cleaned up certificate file: {cert_file}")
            
            if key_file.exists():
                key_file.unlink()
                logger.debug(f"Cleaned up key file: {key_file}")
                
        except Exception as e:
            logger.error(f"Error cleaning up certificate files for {device_id}: {e}")
