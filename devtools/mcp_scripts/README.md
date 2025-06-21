# MCP Client Scripts

This directory contains a set of Python scripts for interacting with the AndroidTVMCP server. Each script is designed to perform a specific action, making them easy to use for testing, automation, and command-line control.

## Prerequisites

- Python 3.8+
- The `androidtvmcp` package installed (`pip install androidtvmcp`)

## Common Usage

All scripts share a common set of command-line arguments:

- `--device <device_name_or_id>`: The name or ID of the device to control. If not provided, you will be prompted to select from a list of discovered devices.
- `--python <path_to_python>`: The Python executable to use for running the MCP server. Defaults to the current Python executable.
- `-v, --verbose`: Enable verbose logging for debugging.

## Scripts

### `get_devices.py`

Discovers and lists all available Android TV devices on the network.

**Usage:**

```bash
python -m devtools.mcp_scripts.get_devices
```

### `launch_app.py`

Launches an application on a specified device.

**Usage:**

```bash
python -m devtools.mcp_scripts.launch_app --device "Living Room TV" --app-name "Netflix"
python -m devtools.mcp_scripts.launch_app --device "Living Room TV" --app-id "com.netflix.ninja"
```

### `navigate.py`

Sends a navigation command to a device.

**Usage:**

```bash
python -m devtools.mcp_scripts.navigate --device "Living Room TV" up
python -m devtools.mcp_scripts.navigate --device "Living Room TV" select
```

**Directions:** `up`, `down`, `left`, `right`, `select`, `back`, `home`

### `playback.py`

Controls media playback on a device.

**Usage:**

```bash
python -m devtools.mcp_scripts.playback --device "Living Room TV" play_pause
python -m devtools.mcp_scripts.playback --device "Living Room TV" next
```

**Actions:** `play_pause`, `next`, `previous`

### `power.py`

Turns a device on or off.

**Usage:**

```bash
python -m devtools.mcp_scripts.power --device "Living Room TV"
```

### `volume.py`

Controls the volume of a device.

**Usage:**

```bash
python -m devtools.mcp_scripts.volume --device "Living Room TV" up
python -m devtools.mcp_scripts.volume --device "Living Room TV" set --level 50
```

**Actions:** `up`, `down`, `mute`

### `input_text.py`

Sends a text string to a device.

**Usage:**

```bash
python -m devtools.mcp_scripts.input_text --device "Living Room TV" "Hello, world!"
```

### `pair_device.py`

Initiates the pairing process with a device.

**Usage:**

```bash
python -m devtools.mcp_scripts.pair_device --device "Living Room TV"
```
