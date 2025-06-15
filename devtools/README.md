# Android TV MCP Development Tools

This directory contains development tools and example clients for the Android TV MCP server.

## Client Examples

### 1. Interactive MCP Client (`interactive_mcp_client.py`)

The most feature-rich client with natural language processing and comprehensive command support.

**Features:**

- Natural language command parsing ("launch Netflix", "volume up")
- Direct tool commands (`atv_navigate direction=up`)
- Resource access (`get_device Living Room TV`)
- Command history and built-in help
- Device pairing support
- Continuous event loop

**Usage:**

```bash
python interactive_mcp_client.py
```

**Example commands:**

```
🎮 > help                          # Show all commands
🎮 > list devices                  # Natural language
🎮 > atv_get_devices              # Direct tool call
🎮 > pair with Living Room TV     # Start pairing
🎮 > launch Netflix               # Launch app
🎮 > navigate up                  # Navigation
🎮 > volume up                    # Volume control
🎮 > get_status Living Room TV    # Resource access
```

### 2. Example Event Loop Client (`example_event_loop_client.py`)

A simplified but complete example showing how to implement an MCP client with event loop.

**Features:**

- Basic command processing
- Tool calling with error handling
- Proper connection management
- Simple command syntax

**Usage:**

```bash
python example_event_loop_client.py
```

**Example commands:**

```
🎮 > devices                      # List devices
🎮 > pair Living_Room_TV          # Start pairing
🎮 > pin Living_Room_TV 1234      # Complete pairing
🎮 > launch Netflix               # Launch app
🎮 > up                           # Navigate up
🎮 > play                         # Start playback
🎮 > vol+                         # Volume up
```

### 3. Simple Interactive Client (`simple_interactive_client.py`)

The most basic example for learning MCP client implementation.

**Features:**

- Minimal code for educational purposes
- Basic command handling
- Direct tool calls only
- Simple error handling

**Usage:**

```bash
python simple_interactive_client.py
```

**Example commands:**

```
> devices                         # List devices
> launch Netflix                  # Launch app
> up                             # Navigate up
> play                           # Start playback
> help                           # Show commands
> exit                           # Exit client
```

## Test Scripts

### Device Testing

- `test_mcp_client.py` - Basic MCP client functionality tests
- `test_mcp_integration.py` - Integration tests with real devices
- `test_pairing_demo.py` - Pairing process demonstration
- `test_pairing_debug.py` - Pairing troubleshooting tools

### Command Testing

- `test_command_processor.py` - Command processor unit tests
- `test_validation_logic.py` - Input validation tests
- `test_openai_schema_validation.py` - OpenAI schema compatibility tests

## Documentation

- `MCP_EVENT_LOOP_GUIDE.md` - Comprehensive guide for using the event loop client
- `PAIRING_DEBUG_GUIDE.md` - Troubleshooting guide for device pairing
- `INTERACTIVE_CLIENT_GUIDE.md` - Guide for the interactive client features

## Getting Started

### Prerequisites

1. Install the Android TV MCP package:

```bash
pip install -e .
```

2. Ensure your Android TV has developer options enabled
3. Connect to the same network as your Android TV

### Quick Start

1. **Start with the simple client** to understand basics:

```bash
cd devtools
python simple_interactive_client.py
```

2. **Try the example client** for more features:

```bash
python example_event_loop_client.py
```

3. **Use the full interactive client** for complete functionality:

```bash
python interactive_mcp_client.py
```

### Device Pairing Workflow

1. **Discover devices:**

```bash
🎮 > list devices
```

2. **Start pairing:**

```bash
🎮 > pair with Living Room TV
```

3. **Complete pairing with PIN from TV:**

```bash
🎮 > atv_complete_pairing device_id=Living_Room_TV pin=1234
```

4. **Verify pairing:**

```bash
🎮 > pairing status Living Room TV
```

5. **Control the device:**

```bash
🎮 > launch Netflix
🎮 > navigate down
🎮 > select
```

## Event Loop Implementation

All clients implement a continuous event loop pattern:

```python
async def run_event_loop(self):
    """Run the main event loop."""
    self.running = True

    while self.running:
        try:
            # Get user input
            user_input = input("🎮 > ").strip()

            # Process command
            await self.process_command(user_input)

        except KeyboardInterrupt:
            print("\n⚠️  Interrupted. Type 'exit' to quit.")
            continue
        except Exception as e:
            print(f"❌ Error: {e}")
```

This allows for:

- Continuous user interaction
- Persistent connections to devices
- Real-time command processing
- Graceful error handling
- Interrupt handling (Ctrl+C)

## MCP Connection Pattern

All clients use the standard MCP connection pattern:

```python
# Configure server parameters
server_params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "androidtvmcp", "serve", "--transport", "stdio"],
    cwd=os.path.join(os.path.dirname(__file__), "..")
)

# Connect and run session
async with stdio_client(server_params) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        # Initialize session
        await session.initialize()

        # Get available tools
        tools_response = await session.list_tools()

        # Call tools
        result = await session.call_tool(tool_name, arguments)
```

## Default Device Behavior

When no specific device is mentioned in commands:

1. **First Available Device**: Commands target the first available connected device
2. **Auto-Connection**: If no devices are connected, the system attempts to connect to the first paired device
3. **Error Handling**: If no devices are paired, commands fail with helpful error messages

## Natural Language Processing

The interactive client includes natural language processing for intuitive commands:

```python
# Navigation patterns
(r"(?:navigate|go|move) (up|down|left|right|home|back|menu|select)",
 lambda m: ("atv_navigate", {"direction": m.group(1)})),

# Volume patterns
(r"(?:volume|turn) (up|down|mute|unmute)",
 lambda m: ("atv_volume", {"action": m.group(1)})),

# App launch patterns
(r"(?:launch|open|start) (?:app |application )?(.+)",
 lambda m: ("atv_launch_app", {"app_name": m.group(1).strip()})),
```

## Error Handling Best Practices

1. **Graceful Degradation**: Continue running even if individual commands fail
2. **User Feedback**: Provide clear error messages with suggestions
3. **Connection Recovery**: Attempt to reconnect on connection failures
4. **Interrupt Handling**: Allow users to interrupt with Ctrl+C

## Contributing

When adding new client examples:

1. Follow the event loop pattern
2. Include comprehensive error handling
3. Provide clear user feedback
4. Document all commands in help text
5. Add example usage to this README

## Troubleshooting

### Connection Issues

- Ensure MCP server is running
- Check network connectivity
- Verify Android TV is discoverable

### Pairing Issues

- Enter PIN quickly (it expires)
- Ensure correct device ID
- Check Android TV pairing screen

### Command Issues

- Use `help` to see available commands
- Check command syntax
- Verify device is paired and connected

For detailed troubleshooting, see `PAIRING_DEBUG_GUIDE.md`.
