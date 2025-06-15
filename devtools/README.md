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

Tests MCP client-server communication by starting a server process and connecting to it as a client. **Now includes Android TV pairing functionality!**

**Usage:**

```bash
cd devtools

# Regular test without pairing
python test_mcp_client.py

# Start pairing with a specific device
python test_mcp_client.py --pair "Living Room TV" --wait-for-pin

# Start pairing and select device interactively
python test_mcp_client.py --pair --wait-for-pin

# Just start pairing without waiting for PIN (for testing)
python test_mcp_client.py --pair "Bedroom TV"
```

**What it tests:**

- MCP server process startup
- Client session establishment
- Tool and resource listing
- Device discovery tool execution
- **Android TV pairing workflow** (NEW!)
- **PIN entry and pairing completion** (NEW!)
- Navigation tool execution
- App launch tool validation
- Error handling and cleanup

**Pairing Workflow:**

1. 🔄 Starts pairing process with selected Android TV device
2. 📺 Displays instructions to look at your TV screen
3. ⌨️ Prompts you to enter the PIN displayed on the TV
4. 🔐 Completes the pairing process with the entered PIN
5. 🎉 Confirms successful pairing
6. 📱 Continues with regular MCP functionality tests

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

### test_pairing_demo.py

Demonstrates the Android TV pairing workflow without requiring actual TV interaction.

**Usage:**

```bash
cd devtools
python test_pairing_demo.py
```

**What it demonstrates:**

- Available Android TV devices on the network
- Step-by-step pairing workflow explanation
- Command examples for different pairing scenarios
- Expected user interaction flow
- Integration with MCP server discovery

### test_openai_schema_validation.py

Tests OpenAI library compatibility with MCP tool schemas.

**Usage:**

```bash
cd devtools
python test_openai_schema_validation.py
```

**What it tests:**

- OpenAI function schema validation
- MCP tool schema compatibility
- Schema constraint handling (anyOf, oneOf, etc.)
- Function calling integration

### test_validation_logic.py

Tests the validation logic for MCP tools directly.

**Usage:**

```bash
cd devtools
python test_validation_logic.py
```

**What it tests:**

- Tool parameter validation
- Error handling for missing parameters
- Schema compliance verification
- Input sanitization

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
