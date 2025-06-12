# Development Tools

This directory contains development and testing utilities for the AndroidTVMCP project. These are standalone scripts designed for manual testing, validation, and demonstration of the system's functionality.

## Scripts

### test_command_processor.py
Tests the command processor functionality with real device discovery and command execution.

**Usage:**
```bash
cd devtools
python test_command_processor.py
```

**What it tests:**
- Device manager initialization
- Device discovery process
- Command processor functionality
- Device status queries
- Navigation command structure
- Error handling

### test_mcp_client.py
Tests MCP client-server communication by starting a server process and connecting to it as a client.

**Usage:**
```bash
cd devtools
python test_mcp_client.py
```

**What it tests:**
- MCP server process startup
- Client session establishment
- Tool and resource listing
- Device discovery tool execution
- Navigation tool execution
- Error handling and cleanup

### test_mcp_integration.py
Tests the MCP server functionality directly without client-server communication.

**Usage:**
```bash
cd devtools
python test_mcp_integration.py
```

**What it tests:**
- MCP server initialization
- Tool handler registration
- Resource handler registration
- Device discovery integration
- Direct tool execution
- Server lifecycle management

## Purpose

These scripts serve different purposes than the unit tests in the `tests/` directory:

- **Unit tests** (`tests/`): Automated testing with mocks for CI/CD
- **Dev tools** (`devtools/`): Manual integration testing with real components

## Requirements

These scripts require the same dependencies as the main project. Make sure you have installed the project in development mode:

```bash
pip install -e ".[dev]"
```

## Notes

- These scripts test with real Android TV device discovery
- Some functionality may require paired devices to work fully
- Scripts include human-readable output for debugging
- All scripts are designed to be run independently
