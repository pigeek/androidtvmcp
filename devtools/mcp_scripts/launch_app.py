#!/usr/bin/env python3
"""
Script to launch an application on an Android TV device using MCP.
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
    """Main function to launch an application."""
    common_parser = create_common_parser()
    parser = argparse.ArgumentParser(
        description="Launch an application on an Android TV device.",
        parents=[common_parser],
    )
    parser.add_argument("--app-name", help="Name of the application to launch.")
    parser.add_argument("--app-id", help="ID of the application to launch.")
    
    args = parser.parse_args()

    if not args.app_name and not args.app_id:
        parser.error("Either --app-name or --app-id must be specified.")

    setup_logging(args.verbose)
    server_params = get_server_params(args)

    async with MCPClient(server_params) as client:
        if not await client.discover_devices():
            return

        if not await client.select_device(args.device):
            return

        arguments = {}
        if args.app_name:
            arguments['app_name'] = args.app_name
        if args.app_id:
            arguments['app_id'] = args.app_id

        await client.send_mcp_command("atv_launch_app", arguments)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
