#!/usr/bin/env python3
"""
Script to pair with an Android TV device using MCP.
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
    """Main function to handle the pairing process."""
    common_parser = create_common_parser()
    parser = argparse.ArgumentParser(
        description="Pair with an Android TV device.",
        parents=[common_parser],
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    server_params = get_server_params(args)

    async with MCPClient(server_params) as client:
        if not await client.discover_devices():
            return

        if not await client.select_device(args.device):
            return

        device_id = client.selected_device_id
        device_name = next((d['name'] for d in client.devices if d['id'] == device_id), device_id)

        print(f"\nStarting pairing process with {device_name}...")
        
        # Start pairing
        start_result = await client.send_mcp_command("atv_start_pairing", {})
        if not start_result:
            print("Failed to start pairing.")
            return

        # Prompt for PIN
        print("\nPlease look at your Android TV screen for the PIN code.")
        while True:
            try:
                pin = input("Enter PIN code (or 'q' to quit): ").strip()
                if pin.lower() == 'q':
                    print("Pairing cancelled.")
                    return
                if not pin:
                    print("PIN cannot be empty.")
                    continue

                # Complete pairing
                await client.send_mcp_command("atv_complete_pairing", {"pin": pin})
                break
            except KeyboardInterrupt:
                print("\nPairing cancelled.")
                return


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
