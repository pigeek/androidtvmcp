#!/usr/bin/env python3
"""
Debug script to test pairing with enhanced logging
"""
import asyncio
import logging
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pairing_debug.log')
    ]
)

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def test_pairing_debug():
    """Test pairing with debug logging enabled"""
    print("AndroidTV MCP Pairing Debug Test")
    print("=" * 50)
    print("This script will run with enhanced logging to help debug pairing issues.")
    print("Logs will be written to both console and 'pairing_debug.log' file.")
    print()
    
    # Get device ID from user
    device_id = input("Enter device ID to pair with (e.g., 'Living Room TV'): ").strip()
    if not device_id:
        print("No device ID provided, exiting.")
        return
    
    # Configure the server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "androidtvmcp", "serve", "--transport", "stdio"],
        cwd=os.path.join(os.path.dirname(__file__), "..")
    )
    
    try:
        print(f"\n🔄 Starting debug test for device: {device_id}")
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✓ MCP session initialized")
                
                # Wait for device discovery
                await asyncio.sleep(3)
                
                # Get devices first
                print("\n📱 Getting available devices...")
                devices_result = await session.call_tool("atv_get_devices", {})
                if devices_result.content:
                    content = devices_result.content[0]
                    if hasattr(content, 'text'):
                        print(f"Devices found: {content.text}")
                
                # Start pairing
                print(f"\n🔄 Starting pairing with {device_id}...")
                pairing_result = await session.call_tool("atv_start_pairing", {
                    "device_id": device_id
                })
                
                if pairing_result.content:
                    content = pairing_result.content[0]
                    if hasattr(content, 'text'):
                        print(f"Pairing start result: {content.text}")
                        
                        if "success=True" in content.text or "pin_required=True" in content.text:
                            # Get PIN from user
                            pin = input("\nEnter PIN displayed on TV: ").strip()
                            
                            if pin:
                                print(f"\n🔐 Completing pairing with PIN...")
                                completion_result = await session.call_tool("atv_complete_pairing", {
                                    "device_id": device_id,
                                    "pin": pin
                                })
                                
                                if completion_result.content:
                                    completion_content = completion_result.content[0]
                                    if hasattr(completion_content, 'text'):
                                        print(f"Pairing completion result: {completion_content.text}")
                                        
                                        if "success=True" in completion_content.text:
                                            print("🎉 Pairing successful!")
                                        else:
                                            print("❌ Pairing failed - check the logs above for details")
                            else:
                                print("No PIN provided, skipping completion")
                        else:
                            print("❌ Pairing start failed - check the logs above for details")
                
    except Exception as e:
        print(f"✗ Error in debug test: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n📋 Debug test complete. Check 'pairing_debug.log' for detailed logs.")

if __name__ == "__main__":
    asyncio.run(test_pairing_debug())
