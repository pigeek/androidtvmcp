#!/usr/bin/env python3
"""
Script to discover and list Android TV devices using MCP.
"""

import argparse
import asyncio
import sys
import os

# Add the devtools directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_scripts.common import (
    MCPClient,
    get_server_params,
    setup_logging,
    create_common_parser,
)


async def main():
    """Main function to discover and list devices."""
    common_parser = create_common_parser()
    parser = argparse.ArgumentParser(
        description="Discover and list Android TV devices.",
        parents=[common_parser],
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    server_params = get_server_params(args)

    async with MCPClient(server_params) as client:
        if await client.discover_devices():
            print("\nAvailable Android TV devices:")
            for i, device in enumerate(client.devices, 1):
                status = device.get('status', 'unknown')
                pairing_status = device.get('pairing_status', 'unknown')
                print(f"  {i}. {device['name']} ({device['id']})")
                print(f"     Status: {status}, Pairing: {pairing_status}")
                print(f"     Host: {device.get('host', 'N/A')}:{device.get('port', 'N/A')}")
                print(f"     Model: {device.get('model', 'N/A')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
