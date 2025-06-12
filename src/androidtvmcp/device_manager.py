"""Device manager for Android TV discovery and connection management."""

import asyncio
import logging
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
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
        self.cert_dir = Path.home() / ".atvrc2mcp" / "certificates"
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing certificates
        self.certificates: Dict[str, DeviceCertificate] = {}
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
            self.zeroconf = Zeroconf()
            
            # Get the current event loop
            loop = asyncio.get_running_loop()
            self.listener = AndroidTVServiceListener(self, loop)
            
            # Android TV services typically use these service types
            service_types = [
                "_androidtvremote2._tcp.local.",
                "_googlecast._tcp.local.",
                "_airplay._tcp.local.",
            ]
            
            self.browser = ServiceBrowser(
                self.zeroconf,
                service_types,
                self.listener
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
                self.browser.cancel()
                self.browser = None
                
            if self.zeroconf:
                self.zeroconf.close()
                self.zeroconf = None
                
            self.listener = None
            self.discovery_running = False
            
            logger.info("Android TV device discovery stopped")
            
        except Exception as e:
            logger.error(f"Error stopping device discovery: {e}")

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
        
        # Skip connection for non-Android TV devices (like Chromecast, Sonos, etc.)
        if not self._is_android_tv_device(device):
            logger.debug(f"Skipping connection to non-Android TV device: {device.name}")
            return False
        
        # Check if device has certificate for connection
        if device_id in self.certificates:
            device.pairing_status = PairingStatus.PAIRED
            return await self._attempt_connection_with_cert(device_id)
        
        # Device requires pairing
        logger.info(f"Android TV device found but requires pairing: {device.name} ({device_id})")
        device.status = DeviceStatus.PAIRING_REQUIRED
        device.pairing_status = PairingStatus.NOT_PAIRED
        return False

    def _is_android_tv_device(self, device: AndroidTVDevice) -> bool:
        """Check if a device is actually an Android TV device.
        
        Args:
            device: Device to check
            
        Returns:
            True if device is Android TV, False otherwise
        """
        # Check if device is on Android TV remote port (6466)
        if device.port == 6466:
            return True
            
        # Check model names that indicate Android TV
        if device.model:
            android_tv_models = ['BRAVIA', 'Android TV', 'Google TV']
            return any(model in device.model for model in android_tv_models)
            
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

    async def get_devices(self) -> DeviceListResponse:
        """Get list of all discovered devices.
        
        Returns:
            DeviceListResponse with device information
        """
        devices = list(self.devices.values())
        connected = sum(1 for d in devices if d.status == DeviceStatus.CONNECTED)
        disconnected = len(devices) - connected
        
        return DeviceListResponse(
            devices=devices,
            total=len(devices),
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
        # If no device_id specified, use first available device
        if not device_id and self.devices:
            device_id = next(iter(self.devices.keys()))
        
        if not device_id:
            return None

        # Check if already connected
        connection = await self.get_connection(device_id)
        if connection:
            return connection

        # Attempt to connect
        if await self._attempt_connection(device_id):
            return await self.get_connection(device_id)

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
                    for device_id, cert_info in cert_data.items():
                        self.certificates[device_id] = DeviceCertificate(**cert_info)
                logger.info(f"Loaded {len(self.certificates)} certificates")
        except Exception as e:
            logger.error(f"Error loading certificates: {e}")

    def _save_certificates(self) -> None:
        """Save certificates to storage."""
        try:
            cert_file = self.cert_dir / "certificates.json"
            cert_data = {}
            for device_id, cert in self.certificates.items():
                cert_data[device_id] = cert.dict()
            
            with open(cert_file, 'w') as f:
                json.dump(cert_data, f, indent=2)
            logger.debug("Certificates saved")
        except Exception as e:
            logger.error(f"Error saving certificates: {e}")

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
        
        # Check if device is Android TV
        if not self._is_android_tv_device(device):
            return PairingResult(
                success=False,
                message=f"Device is not an Android TV: {device.name}",
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code="NOT_ANDROID_TV"
            )

        try:
            device.status = DeviceStatus.PAIRING
            device.pairing_status = PairingStatus.PAIRING
            
            logger.info(f"Starting pairing with {device.name} ({device_id})")
            
            # Create temporary certificate files for pairing
            temp_cert_file = self.cert_dir / f"temp_{device_id}.crt"
            temp_key_file = self.cert_dir / f"temp_{device_id}.key"
            
            # Create AndroidTVRemote for pairing
            remote = AndroidTVRemote(
                client_name="ATVRC2MCP",
                certfile=str(temp_cert_file),
                keyfile=str(temp_key_file),
                host=device.host,
                api_port=device.port,
                pair_port=6467  # Standard Android TV pairing port
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
            return PairingResult(
                success=False,
                message=f"No active pairing session found for {device.name}. Please start pairing first.",
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code="NO_PAIRING_SESSION"
            )
        
        try:
            logger.info(f"Completing pairing with {device.name} using PIN: {pin}")
            
            # Use the existing pairing remote
            remote = pairing_remotes[device_id]
            
            # Complete pairing with PIN
            await remote.async_finish_pairing(pin)
            
            # Read the generated certificate files
            temp_cert_file = self.cert_dir / f"temp_{device_id}.crt"
            temp_key_file = self.cert_dir / f"temp_{device_id}.key"
            
            if not temp_cert_file.exists() or not temp_key_file.exists():
                raise Exception("Certificate files were not generated during pairing")
            
            # Read certificate and key
            with open(temp_cert_file, 'r') as f:
                cert_content = f.read()
            with open(temp_key_file, 'r') as f:
                key_content = f.read()
            
            # Store certificate
            certificate = DeviceCertificate(
                device_id=device_id,
                certificate=cert_content,
                private_key=key_content,
                created_at=datetime.now(timezone.utc).isoformat()
            )
            
            self.certificates[device_id] = certificate
            self._save_certificates()
            
            # Clean up temporary files
            temp_cert_file.unlink()
            temp_key_file.unlink()
            
            # Clean up pairing remote
            del pairing_remotes[device_id]
            
            # Update device status
            device.status = DeviceStatus.DISCONNECTED
            device.pairing_status = PairingStatus.PAIRED
            
            logger.info(f"Successfully paired with {device.name}")
            
            # Attempt to connect now that we have certificates
            await self._attempt_connection_with_cert(device_id)
            
            return PairingResult(
                success=True,
                message=f"Successfully paired with {device.name}",
                device_id=device_id,
                status=PairingStatus.PAIRED,
                certificate=certificate
            )
            
        except Exception as e:
            logger.error(f"Error completing pairing with {device_id}: {e}")
            device.status = DeviceStatus.ERROR
            device.pairing_status = PairingStatus.PAIRING_FAILED
            
            # Clean up temporary files and pairing remote
            try:
                temp_cert_file = self.cert_dir / f"temp_{device_id}.crt"
                temp_key_file = self.cert_dir / f"temp_{device_id}.key"
                if temp_cert_file.exists():
                    temp_cert_file.unlink()
                if temp_key_file.exists():
                    temp_key_file.unlink()
                if device_id in pairing_remotes:
                    del pairing_remotes[device_id]
            except:
                pass
            
            return PairingResult(
                success=False,
                message=f"Failed to complete pairing: {str(e)}",
                device_id=device_id,
                status=PairingStatus.PAIRING_FAILED,
                error_code="PAIRING_COMPLETION_FAILED"
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
                client_name="ATVRC2MCP",
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
            logger.error(f"Error connecting to {device_id} with certificate: {e}")
            device.status = DeviceStatus.ERROR
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
            
            # Update device status
            device = self.devices[device_id]
            device.status = DeviceStatus.DISCONNECTED
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
