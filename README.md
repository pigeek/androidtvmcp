# AndroidTVMCP - Android TV Remote Control to MCP Bridge

A Model Context Protocol (MCP) server that provides Android TV remote control functionality to AI assistants and other MCP clients.

## Overview

AndroidTVMCP bridges Android TV remote control capabilities with the Model Context Protocol, enabling seamless integration of Android TV control into AI-powered workflows and automation systems.

## Features

- **Device Discovery**: Automatic detection of Android TV devices on the local network
- **Remote Control**: Full navigation and playback control capabilities
- **App Management**: Launch and switch between Android TV applications
- **State Monitoring**: Query device status and current state
- **MCP Integration**: Standard MCP protocol compliance for easy integration

## Quick Start

### Installation

#### Using Virtual Environment (Recommended)

```bash
# Create a virtual environment
python -m venv androidtvmcp-env

# Activate the virtual environment
# On Linux/macOS:
source androidtvmcp-env/bin/activate
# On Windows:
# androidtvmcp-env\Scripts\activate

# Install the package
pip install androidtvmcp
```

#### Global Installation

```bash
pip install androidtvmcp
```

### Basic Usage

1. Start the MCP server:

```bash
androidtvmcp --host localhost --port 8080
```

2. Configure your MCP client to connect to the server

3. Use Android TV control tools through your AI assistant

### Example Commands

- Navigate: "Move up on the Android TV"
- Playback: "Pause the current video"
- Apps: "Launch Netflix on Android TV"
- Status: "What's currently playing on Android TV?"

## Configuration

Create a configuration file `config.json`:

```json
{
  "devices": {
    "discovery": {
      "enabled": true,
      "timeout": 10
    },
    "connection": {
      "timeout": 5,
      "retry_attempts": 3
    }
  },
  "mcp": {
    "host": "localhost",
    "port": 8080,
    "transport": "stdio"
  },
  "logging": {
    "level": "INFO",
    "file": "androidtvmcp.log"
  }
}
```

## MCP Tools

### Navigation Tools

- `atv_navigate`: Navigate Android TV interface (up, down, left, right, select, menu, back, home)
- `atv_input_text`: Send text input to Android TV

### Playback Tools

- `atv_playback`: Control media playback (play, pause, stop, fast_forward, rewind)
- `atv_volume`: Adjust volume (up, down, mute)

### App Management Tools

- `atv_launch_app`: Launch specific applications
- `atv_get_apps`: List available applications
- `atv_switch_app`: Switch between running applications

### Device Tools

- `atv_get_devices`: List discovered Android TV devices
- `atv_get_status`: Get current device status and state
- `atv_power`: Power control (on, off, sleep)

## MCP Resources

### Device Information

- `device://[device_id]/info`: Device capabilities and information
- `device://[device_id]/status`: Current device status
- `device://[device_id]/apps`: Available applications

### Current State

- `state://current_app`: Currently active application
- `state://playback`: Current playback status
- `state://volume`: Current volume level

## Development

### Setup Development Environment

#### Using Virtual Environment (Recommended)

```bash
# Clone the repository
git clone https://github.com/pigeek/androidtvmcp.git
cd androidtvmcp

# Create and activate virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

#### Alternative Setup

```bash
git clone https://github.com/pigeek/androidtvmcp.git
cd androidtvmcp
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Development Tools

The `devtools/` directory contains standalone scripts for manual testing and validation:

```bash
cd devtools
python test_command_processor.py  # Test command processor functionality
python test_mcp_client.py         # Test MCP client-server communication
python test_mcp_integration.py    # Test MCP server integration
```

See `devtools/README.md` for detailed information about each script.

### Code Formatting

```bash
black src/ tests/
isort src/ tests/
```

### Type Checking

```bash
mypy src/
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │◄──►│  AndroidTVMCP   │◄──►│   Android TV    │
│  (AI Assistant) │    │    Server       │    │   Devices       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Components

- **MCP Server**: Handles MCP protocol communication
- **Device Manager**: Manages Android TV device discovery and connections
- **Command Processor**: Translates MCP requests to Android TV commands
- **Network Layer**: Handles Android TV protocol communication

## Requirements

- Python 3.8+
- Android TV devices on the same network
- Network connectivity for device discovery

## Troubleshooting

### Common Issues

1. **Device Not Found**

   - Ensure Android TV is on the same network
   - Check firewall settings
   - Verify device discovery is enabled

2. **Connection Failed**

   - Check network connectivity
   - Verify Android TV remote control is enabled
   - Try restarting the Android TV device

3. **Commands Not Working**
   - Ensure device is powered on
   - Check if device supports the command
   - Verify connection status

### Debug Mode

Enable debug logging:

```bash
androidtvmcp --log-level DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- [GitHub Issues](https://github.com/pigeek/androidtvmcp/issues)
- [Documentation](https://androidtvmcp.readthedocs.io/)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)

## Related Projects

- [androidtvremote2](https://github.com/tronikos/androidtvremote2) - Android TV remote control library
- [Model Context Protocol](https://modelcontextprotocol.io/) - Protocol specification
