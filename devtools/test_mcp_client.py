#!/usr/bin/env python3
"""
Test script to validate MCP client-server communication with pairing support
"""
import asyncio
import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def prompt_for_pin() -> str:
    """Prompt the user to enter the PIN displayed on the TV."""
    print("\n" + "=" * 50)
    print("🔗 PAIRING REQUIRED")
    print("=" * 50)
    print("Please look at your Android TV screen and enter the PIN code displayed:")
    print("(The PIN should be a 4-6 digit number)")
    print()
    print("📺 IMPORTANT: Make sure the PIN is currently visible on your TV screen")
    print("⏰ Note: PINs typically expire after 30-60 seconds")
    print()
    
    while True:
        try:
            pin = input("Enter PIN: ").strip()
            
            # Enhanced validation with detailed feedback
            if not pin:
                print("❌ PIN cannot be empty. Please enter the PIN displayed on your TV.")
                continue
                
            if len(pin) < 4:
                print(f"❌ PIN too short. You entered {len(pin)} digits, but PIN must be 4-6 digits long.")
                continue
                
            if len(pin) > 6:
                print(f"❌ PIN too long. You entered {len(pin)} digits, but PIN must be 4-6 digits long.")
                continue
            
            # PIN is valid format
            pin_masked = pin[:2] + "*" * (len(pin) - 2)
            print(f"✓ PIN format valid: {pin_masked} (length: {len(pin)})")
            print(f"🔄 Sending PIN to Android TV...")
            
            return pin
            
        except KeyboardInterrupt:
            print("\n❌ Pairing cancelled by user")
            sys.exit(1)
        except EOFError:
            print("\n❌ No input received")
            sys.exit(1)

def parse_devices_from_result(result_text: str) -> List[Dict[str, str]]:
    """Parse device information from the result text."""
    devices = []
    try:
        # Look for device information in the result text
        if "devices=" in result_text:
            # This is a simplified parser - in a real implementation,
            # we might want to parse JSON or use a more robust method
            lines = result_text.split('\n')
            for line in lines:
                if 'AndroidTVDevice' in line or 'device_id' in line.lower():
                    # Extract device info (this is a placeholder implementation)
                    # In practice, we'd parse the actual device data structure
                    devices.append({
                        'id': f'device_{len(devices)}',
                        'name': f'Android TV Device {len(devices) + 1}',
                        'status': 'discovered'
                    })
    except Exception as e:
        print(f"⚠️  Could not parse device information: {e}")
    
    return devices

async def select_device_interactively(devices: List[Dict[str, str]]) -> Optional[str]:
    """Allow user to select a device from the list."""
    if not devices:
        print("❌ No devices found to pair with")
        return None
    
    print("\n📱 Available Android TV Devices:")
    print("-" * 40)
    for i, device in enumerate(devices, 1):
        print(f"{i}. {device.get('name', 'Unknown Device')} ({device.get('id', 'unknown')})")
    
    print("\nWhich device would you like to pair with?")
    
    while True:
        try:
            choice = input(f"Enter number (1-{len(devices)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                print("❌ Pairing cancelled by user")
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(devices):
                selected_device = devices[choice_num - 1]
                return selected_device.get('id')
            else:
                print(f"❌ Please enter a number between 1 and {len(devices)}")
        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n❌ Pairing cancelled by user")
            return None

async def test_mcp_client(pair_device_id: Optional[str] = None, wait_for_pin: bool = False):
    """Test MCP client communication with the AndroidTVMCP server"""
    print("Testing AndroidTVMCP MCP Client Communication")
    print("=" * 50)
    
    # Configure the server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "androidtvmcp", "serve", "--transport", "stdio"],
        cwd=os.path.join(os.path.dirname(__file__), "..")
    )
    
    try:
        print("✓ Server parameters configured")
        
        # Create MCP client session using stdio_client
        async with stdio_client(server_params) as (read, write):
            print("✓ Server process started via stdio_client")
            
            async with ClientSession(read, write) as session:
                print("✓ MCP client session established")
                
                # Initialize the session
                await session.initialize()
                print("✓ Session initialized")
                
                # Wait for device discovery to complete
                print("⏳ Waiting for device discovery...")
                await asyncio.sleep(3)  # Give time for device discovery
                
                # List available tools
                try:
                    tools = await session.list_tools()
                    print(f"✓ Found {len(tools.tools)} MCP tools:")
                    for tool in tools.tools:
                        print(f"  - {tool.name}: {tool.description}")
                except Exception as e:
                    print(f"✗ Error listing tools: {e}")
                
                # List available resources
                try:
                    resources = await session.list_resources()
                    print(f"✓ Found {len(resources.resources)} MCP resources:")
                    for resource in resources.resources:
                        print(f"  - {resource.uri}: {resource.name}")
                except Exception as e:
                    print(f"✗ Error listing resources: {e}")
                
                # Test device discovery tool and handle pairing if requested
                devices_result_text = ""
                try:
                    result = await session.call_tool("atv_get_devices", {})
                    print("✓ Device discovery tool executed successfully")
                    
                    if result.content:
                        content = result.content[0]
                        if hasattr(content, 'text'):
                            devices_result_text = content.text
                            print(f"  Result: {content.text}")
                            
                            # Try to parse the result
                            try:
                                # The result might be a string representation of the result object
                                result_text = content.text
                                if "devices=" in result_text:
                                    # Extract device count
                                    if "total=" in result_text:
                                        total_start = result_text.find("total=") + 6
                                        total_end = result_text.find(" ", total_start)
                                        if total_end == -1:
                                            total_end = len(result_text)
                                        total_devices = result_text[total_start:total_end]
                                        print(f"  Found {total_devices} total devices")
                                    
                                    if "connected=" in result_text:
                                        connected_start = result_text.find("connected=") + 10
                                        connected_end = result_text.find(" ", connected_start)
                                        if connected_end == -1:
                                            connected_end = len(result_text)
                                        connected_devices = result_text[connected_start:connected_end]
                                        print(f"  Connected devices: {connected_devices}")
                                        
                            except Exception as parse_e:
                                print(f"  Could not parse result details: {parse_e}")
                        
                except Exception as e:
                    print(f"✗ Error testing device discovery tool: {e}")
                
                # Handle pairing if requested
                if pair_device_id is not None or wait_for_pin:
                    print("\n" + "=" * 50)
                    print("🔗 PAIRING MODE ACTIVATED")
                    print("=" * 50)
                    
                    # Determine which device to pair with
                    target_device_id = pair_device_id
                    
                    if not target_device_id:
                        # Parse available devices and let user select
                        devices = parse_devices_from_result(devices_result_text)
                        if devices:
                            target_device_id = await select_device_interactively(devices)
                        else:
                            print("❌ No devices found for pairing. Trying with a default device ID...")
                            # Try with a common device name pattern
                            target_device_id = "Living Room TV"  # Common default
                    
                    if target_device_id:
                        print(f"\n🔄 Starting pairing with device: {target_device_id}")
                        
                        # Start pairing process
                        try:
                            pairing_result = await session.call_tool("atv_start_pairing", {
                                "device_id": target_device_id
                            })
                            
                            if pairing_result.content:
                                content = pairing_result.content[0]
                                if hasattr(content, 'text'):
                                    print(f"✓ Pairing started: {content.text}")
                                    
                                    # Check if PIN is required
                                    if "PIN" in content.text or "pin" in content.text.lower() or wait_for_pin:
                                        # Wait for user to enter PIN
                                        pin = await prompt_for_pin()
                                        
                                        pin_masked = pin[:2] + "*" * (len(pin) - 2)
                                        print(f"\n🔐 Completing pairing with PIN: {pin_masked}")
                                        
                                        # Complete pairing
                                        try:
                                            completion_result = await session.call_tool("atv_complete_pairing", {
                                                "device_id": target_device_id,
                                                "pin": pin
                                            })
                                            
                                            if completion_result.content:
                                                completion_content = completion_result.content[0]
                                                if hasattr(completion_content, 'text'):
                                                    result_text = completion_content.text
                                                    print(f"📋 Pairing result: {result_text}")
                                                    
                                                    # Parse the result for success/failure
                                                    if "success=True" in result_text or "Successfully paired" in result_text:
                                                        print("🎉 Device successfully paired!")
                                                        
                                                        # Check if connection was established
                                                        if "connection" in result_text.lower():
                                                            if "successful" in result_text.lower():
                                                                print("🔗 Device connection established successfully")
                                                            else:
                                                                print("⚠️  Device paired but connection may have failed")
                                                    
                                                    elif "success=False" in result_text:
                                                        print("❌ Pairing failed!")
                                                        
                                                        # Provide specific error guidance based on error codes
                                                        if "INVALID_PIN" in result_text:
                                                            print("💡 The PIN you entered was rejected by the TV.")
                                                            print("   Please check:")
                                                            print("   - Is the PIN still displayed on your TV?")
                                                            print("   - Did you enter all digits correctly?")
                                                            print("   - Try starting the pairing process again")
                                                        elif "PAIRING_TIMEOUT" in result_text:
                                                            print("💡 The pairing session timed out.")
                                                            print("   Please restart the pairing process and enter the PIN faster")
                                                        elif "CONNECTION_ERROR" in result_text:
                                                            print("💡 Network connection issue during pairing.")
                                                            print("   Please check your network connection and try again")
                                                        elif "NO_PAIRING_SESSION" in result_text:
                                                            print("💡 No active pairing session found.")
                                                            print("   Please start the pairing process first")
                                                        else:
                                                            print("💡 Unknown pairing error. Check the error message above.")
                                                    
                                                    else:
                                                        print("⚠️  Pairing result unclear. Check the result above.")
                                        
                                        except Exception as completion_e:
                                            print(f"✗ Error completing pairing: {completion_e}")
                                            print("💡 This could indicate:")
                                            print("   - Network connectivity issues")
                                            print("   - MCP server communication problems")
                                            print("   - Android TV device not responding")
                                    
                                    else:
                                        print("ℹ️  Pairing started but no PIN required or pairing already complete")
                        
                        except Exception as pairing_e:
                            print(f"✗ Error starting pairing: {pairing_e}")
                            print("ℹ️  This might be expected if the device is already paired or not available")
                    
                    else:
                        print("❌ No device selected for pairing")
                    
                    print("\n" + "=" * 50)
                    print("📱 CONTINUING WITH REGULAR TESTS")
                    print("=" * 50)
                
                # Test navigation tool (should fail gracefully without paired device)
                try:
                    result = await session.call_tool("atv_navigate", {"direction": "up"})
                    print("✓ Navigation tool executed (expected to fail without paired device)")
                    
                    if result.content:
                        content = result.content[0]
                        if hasattr(content, 'text'):
                            print(f"  Result: {content.text}")
                        
                except Exception as e:
                    print(f"✗ Error testing navigation tool: {e}")
                
                # Test app launch tool with validation
                try:
                    # Test with missing app_id and app_name (should fail)
                    result = await session.call_tool("atv_launch_app", {})
                    print("✓ App launch tool validation test (expected to fail)")
                    
                    if result.content:
                        content = result.content[0]
                        if hasattr(content, 'text'):
                            print(f"  Result: {content.text}")
                        
                except Exception as e:
                    print(f"✗ Error testing app launch validation: {e}")
                
                # Test app launch tool with app_name
                try:
                    result = await session.call_tool("atv_launch_app", {"app_name": "Netflix"})
                    print("✓ App launch tool with app_name executed (expected to fail without paired device)")
                    
                    if result.content:
                        content = result.content[0]
                        if hasattr(content, 'text'):
                            print(f"  Result: {content.text}")
                        
                except Exception as e:
                    print(f"✗ Error testing app launch with app_name: {e}")
                
                # Test app launch tool with app_id
                try:
                    result = await session.call_tool("atv_launch_app", {"app_id": "com.netflix.ninja"})
                    print("✓ App launch tool with app_id executed (expected to fail without paired device)")
                    
                    if result.content:
                        content = result.content[0]
                        if hasattr(content, 'text'):
                            print(f"  Result: {content.text}")
                        
                except Exception as e:
                    print(f"✗ Error testing app launch with app_id: {e}")
                
                print("✓ MCP client communication test completed")
                
    except Exception as e:
        print(f"✗ Error in MCP client test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nMCP Client Test Complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test MCP client with Android TV pairing support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regular test without pairing
  python test_mcp_client.py
  
  # Start pairing with a specific device
  python test_mcp_client.py --pair "Living Room TV" --wait-for-pin
  
  # Start pairing and select device interactively
  python test_mcp_client.py --pair --wait-for-pin
  
  # Just start pairing without waiting for PIN (for testing)
  python test_mcp_client.py --pair "Bedroom TV"
        """
    )
    
    parser.add_argument(
        "--pair", 
        dest="pair_device_id", 
        nargs="?",
        const="",  # If --pair is used without value, set to empty string
        help="Device ID to pair with. Use without value to select interactively."
    )
    
    parser.add_argument(
        "--wait-for-pin", 
        action="store_true", 
        help="Wait for PIN input during pairing process"
    )
    
    args = parser.parse_args()
    
    # Convert empty string to None for cleaner logic
    pair_device_id = args.pair_device_id if args.pair_device_id else None
    
    asyncio.run(test_mcp_client(pair_device_id, args.wait_for_pin))
