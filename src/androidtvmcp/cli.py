"""Command line interface for AndroidTVMCP server."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click

from .server import AndroidTVMCPServer
from .models import ConfigModel, DeviceConfig, MCPConfig, LoggingConfig


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Setup logging configuration.
    
    Args:
        level: Logging level
        log_file: Optional log file path
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers
    )


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                click.echo(f"Error loading config file {config_path}: {e}", err=True)
                sys.exit(1)
        else:
            click.echo(f"Config file not found: {config_path}", err=True)
            sys.exit(1)
    
    # Return default configuration
    return {
        "devices": {
            "discovery": {
                "enabled": True,
                "timeout": 10,
                "interval": 30
            },
            "connection": {
                "timeout": 5,
                "retry_attempts": 3,
                "retry_delay": 1
            }
        },
        "mcp": {
            "host": "localhost",
            "port": 8080,
            "transport": "stdio"
        },
        "logging": {
            "level": "INFO",
            "file": None
        }
    }


@click.group()
@click.version_option(version="0.2.0", prog_name="androidtvmcp")
def cli():
    """AndroidTVMCP - Android TV Remote Control to MCP Bridge."""
    pass


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Configuration file path"
)
@click.option(
    "--host", "-h",
    default="localhost",
    help="Host to bind to (for TCP transport)"
)
@click.option(
    "--port", "-p",
    default=8080,
    type=int,
    help="Port to bind to (for TCP transport)"
)
@click.option(
    "--transport", "-t",
    default="stdio",
    type=click.Choice(["stdio", "tcp"]),
    help="Transport mechanism"
)
@click.option(
    "--log-level", "-l",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Logging level"
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Log file path"
)
def serve(
    config: Optional[str],
    host: str,
    port: int,
    transport: str,
    log_level: str,
    log_file: Optional[str]
):
    """Start the AndroidTVMCP server."""
    # Load configuration
    config_data = load_config(config)
    
    # Override config with command line options
    if host != "localhost":
        config_data.setdefault("mcp", {})["host"] = host
    if port != 8080:
        config_data.setdefault("mcp", {})["port"] = port
    if transport != "stdio":
        config_data.setdefault("mcp", {})["transport"] = transport
    if log_level != "INFO":
        config_data.setdefault("logging", {})["level"] = log_level
    if log_file:
        config_data.setdefault("logging", {})["file"] = log_file
    
    # Setup logging
    logging_config = config_data.get("logging", {})
    setup_logging(
        level=logging_config.get("level", "INFO"),
        log_file=logging_config.get("file")
    )
    
    # Create and run server
    server = AndroidTVMCPServer(config_data)
    
    try:
        if transport == "stdio":
            log_level_int = getattr(logging, log_level.upper(), logging.INFO)
            asyncio.run(server.run_stdio(log_level=log_level_int))
        elif transport == "tcp":
            mcp_config = config_data.get("mcp", {})
            asyncio.run(server.run_tcp(
                host=mcp_config.get("host", host),
                port=mcp_config.get("port", port)
            ))
    except KeyboardInterrupt:
        click.echo("\nShutting down server...")
    except Exception as e:
        click.echo(f"Server error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Configuration file path"
)
@click.option(
    "--timeout", "-t",
    default=10,
    type=int,
    help="Discovery timeout in seconds"
)
def discover(config: Optional[str], timeout: int):
    """Discover Android TV devices on the network."""
    # Load configuration
    config_data = load_config(config)
    
    # Setup logging
    setup_logging(level="INFO")
    
    async def run_discovery():
        from .device_manager import DeviceManager
        
        device_manager = DeviceManager(config_data.get("devices", {}))
        
        try:
            click.echo("Starting Android TV device discovery...")
            await device_manager.start_discovery()
            
            # Wait for discovery
            await asyncio.sleep(timeout)
            
            # Get discovered devices
            devices_response = await device_manager.get_devices()
            
            click.echo(f"\nDiscovered {devices_response.total} Android TV devices:")
            for device in devices_response.devices:
                status_color = "green" if device.status == "connected" else "red"
                click.echo(f"  • {device.name} ({device.id})")
                click.echo(f"    Host: {device.host}:{device.port}")
                click.echo(f"    Status: ", nl=False)
                click.secho(device.status, fg=status_color)
                if device.model:
                    click.echo(f"    Model: {device.model}")
                if device.capabilities:
                    click.echo(f"    Capabilities: {', '.join(device.capabilities)}")
                click.echo()
            
        except Exception as e:
            click.echo(f"Discovery error: {e}", err=True)
        finally:
            await device_manager.stop_discovery()
    
    try:
        asyncio.run(run_discovery())
    except KeyboardInterrupt:
        click.echo("\nDiscovery interrupted.")


@cli.command()
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path (default: config.json)"
)
@click.option(
    "--discovery/--no-discovery",
    default=True,
    help="Enable/disable device discovery"
)
@click.option(
    "--discovery-timeout",
    default=10,
    type=int,
    help="Device discovery timeout"
)
@click.option(
    "--connection-timeout",
    default=5,
    type=int,
    help="Device connection timeout"
)
@click.option(
    "--retry-attempts",
    default=3,
    type=int,
    help="Connection retry attempts"
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Logging level"
)
def config(
    output: Optional[str],
    discovery: bool,
    discovery_timeout: int,
    connection_timeout: int,
    retry_attempts: int,
    log_level: str
):
    """Generate a configuration file."""
    config_data = {
        "devices": {
            "discovery": {
                "enabled": discovery,
                "timeout": discovery_timeout,
                "interval": 30
            },
            "connection": {
                "timeout": connection_timeout,
                "retry_attempts": retry_attempts,
                "retry_delay": 1
            }
        },
        "mcp": {
            "host": "localhost",
            "port": 8080,
            "transport": "stdio"
        },
        "logging": {
            "level": log_level,
            "file": None,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    output_path = output or "config.json"
    
    try:
        with open(output_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        click.echo(f"Configuration file created: {output_path}")
    except Exception as e:
        click.echo(f"Error creating config file: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Configuration file path"
)
@click.option(
    "--device-id", "-d",
    help="Specific device ID to test"
)
def test(config: Optional[str], device_id: Optional[str]):
    """Test connection to Android TV devices."""
    # Load configuration
    config_data = load_config(config)
    
    # Setup logging
    setup_logging(level="DEBUG")
    
    async def run_test():
        from .device_manager import DeviceManager
        from .commands import CommandProcessor
        from .models import NavigationCommand
        
        device_manager = DeviceManager(config_data.get("devices", {}))
        command_processor = CommandProcessor(device_manager)
        
        try:
            click.echo("Starting device discovery...")
            await device_manager.start_discovery()
            
            # Wait for discovery
            await asyncio.sleep(5)
            
            # Get devices
            devices_response = await device_manager.get_devices()
            
            if not devices_response.devices:
                click.echo("No Android TV devices found.")
                return
            
            # Test specific device or first available
            test_device = None
            if device_id:
                test_device = await device_manager.get_device(device_id)
                if not test_device:
                    click.echo(f"Device not found: {device_id}")
                    return
            else:
                test_device = devices_response.devices[0]
            
            click.echo(f"Testing device: {test_device.name} ({test_device.id})")
            
            # Test connection
            connection = await device_manager.ensure_connection(test_device.id)
            if not connection:
                click.echo("Failed to connect to device.")
                return
            
            click.echo("Connection successful!")
            
            # Test navigation command
            click.echo("Testing navigation command (home)...")
            nav_command = NavigationCommand(device_id=test_device.id, direction="home")
            result = await command_processor.execute_navigation(nav_command)
            
            if result.success:
                click.secho("Navigation test successful!", fg="green")
            else:
                click.secho(f"Navigation test failed: {result.message}", fg="red")
            
            # Test status query
            click.echo("Testing status query...")
            status = await command_processor.get_status(test_device.id)
            click.echo(f"Device status: {status.device_state.status}")
            
        except Exception as e:
            click.echo(f"Test error: {e}", err=True)
        finally:
            await device_manager.stop_discovery()
    
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        click.echo("\nTest interrupted.")


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Configuration file path"
)
@click.argument("device_id")
def pair(config: Optional[str], device_id: str):
    """Start pairing process with an Android TV device."""
    # Load configuration
    config_data = load_config(config)
    
    # Setup logging
    setup_logging(level="INFO")
    
    async def run_pairing():
        from .device_manager import DeviceManager
        
        device_manager = DeviceManager(config_data.get("devices", {}))
        
        try:
            click.echo("Starting device discovery...")
            await device_manager.start_discovery()
            
            # Wait for discovery
            await asyncio.sleep(5)
            
            # Check if device exists
            device = await device_manager.get_device(device_id)
            if not device:
                click.echo(f"Device not found: {device_id}")
                click.echo("Available devices:")
                devices_response = await device_manager.get_devices()
                for d in devices_response.devices:
                    click.echo(f"  • {d.name} ({d.id})")
                return
            
            click.echo(f"Starting pairing with {device.name} ({device_id})")
            
            # Start pairing
            result = await device_manager.start_pairing(device_id)
            
            if not result.success:
                click.secho(f"Failed to start pairing: {result.message}", fg="red")
                return
            
            click.secho(result.message, fg="green")
            
            if result.pin_required:
                # Prompt for PIN
                pin = click.prompt("Enter the PIN displayed on your Android TV", type=str)
                
                click.echo("Completing pairing...")
                complete_result = await device_manager.complete_pairing(device_id, pin)
                
                if complete_result.success:
                    click.secho(f"Successfully paired with {device.name}!", fg="green")
                    click.echo("You can now use the device with AndroidTVMCP.")
                else:
                    click.secho(f"Pairing failed: {complete_result.message}", fg="red")
            
        except Exception as e:
            click.echo(f"Pairing error: {e}", err=True)
        finally:
            await device_manager.stop_discovery()
    
    try:
        asyncio.run(run_pairing())
    except KeyboardInterrupt:
        click.echo("\nPairing interrupted.")


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Configuration file path"
)
@click.argument("device_id")
def unpair(config: Optional[str], device_id: str):
    """Unpair an Android TV device."""
    # Load configuration
    config_data = load_config(config)
    
    # Setup logging
    setup_logging(level="INFO")
    
    async def run_unpair():
        from .device_manager import DeviceManager
        
        device_manager = DeviceManager(config_data.get("devices", {}))
        
        try:
            # Check if device is paired
            if not device_manager.is_device_paired(device_id):
                click.echo(f"Device {device_id} is not paired.")
                return
            
            click.echo(f"Unpairing device {device_id}...")
            
            # Unpair device
            result = await device_manager.unpair_device(device_id)
            
            if result.success:
                click.secho(result.message, fg="green")
            else:
                click.secho(f"Failed to unpair device: {result.message}", fg="red")
            
        except Exception as e:
            click.echo(f"Unpair error: {e}", err=True)
    
    try:
        asyncio.run(run_unpair())
    except KeyboardInterrupt:
        click.echo("\nUnpair interrupted.")


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Configuration file path"
)
def list_paired(config: Optional[str]):
    """List all paired Android TV devices."""
    # Load configuration
    config_data = load_config(config)
    
    # Setup logging
    setup_logging(level="INFO")
    
    async def run_list():
        from .device_manager import DeviceManager
        
        device_manager = DeviceManager(config_data.get("devices", {}))
        
        try:
            paired_devices = device_manager.get_paired_devices()
            
            if not paired_devices:
                click.echo("No paired devices found.")
                return
            
            click.echo(f"Found {len(paired_devices)} paired device(s):")
            
            # Start discovery to get device details
            await device_manager.start_discovery()
            await asyncio.sleep(3)
            
            for device_id in paired_devices:
                device = await device_manager.get_device(device_id)
                if device:
                    status_color = "green" if device.status == "connected" else "yellow"
                    click.echo(f"  • {device.name} ({device_id})")
                    click.echo(f"    Host: {device.host}:{device.port}")
                    click.echo(f"    Status: ", nl=False)
                    click.secho(device.status, fg=status_color)
                    click.echo(f"    Pairing: ", nl=False)
                    click.secho(device.pairing_status, fg="green")
                else:
                    click.echo(f"  • {device_id} (device not currently discoverable)")
                click.echo()
            
        except Exception as e:
            click.echo(f"List error: {e}", err=True)
        finally:
            await device_manager.stop_discovery()
    
    try:
        asyncio.run(run_list())
    except KeyboardInterrupt:
        click.echo("\nList interrupted.")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
