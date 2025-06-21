#!/usr/bin/env python3
"""
Script to send navigation commands to an Android TV device using MCP.
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
    """Main function to send a navigation command."""
    common_parser = create_common_parser()
    parser = argparse.ArgumentParser(
        description="Send a navigation command to an Android TV device.",
        parents=[common_parser],
    )
    parser.add_argument(
        "direction",
        choices=["up", "down", "left", "right", "select", "back", "home"],
        help="The navigation direction.",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    server_params = get_server_params(args)

    async with MCPClient(server_params) as client:
        if not await client.discover_devices():
            return

        if not await client.select_device(args.device):
            return

        await client.send_mcp_command("atv_navigate", {"direction": args.direction})


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
