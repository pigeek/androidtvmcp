#!/usr/bin/env python3
"""
Test script to validate command processor functionality
"""
import asyncio
import json
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from androidtvmcp.device_manager import DeviceManager
from androidtvmcp.commands import CommandProcessor

async def test_command_processor():
    """Test the command processor functionality"""
    print("Testing AndroidTVMCP Command Processor")
    print("=" * 40)
    
    # Create device manager and command processor
    device_manager = DeviceManager({})
    command_processor = CommandProcessor(device_manager)
    
    print("✓ Command processor created successfully")
    
    # Start device discovery
    try:
        await device_manager.start_discovery()
        print("✓ Device discovery started")
        
        # Wait for discovery
        await asyncio.sleep(3)
        
    except Exception as e:
        print(f"✗ Error starting discovery: {e}")
    
    # Test get_devices command
    try:
        result = await command_processor.get_devices()
        print("✓ get_devices command executed successfully")
        print(f"  Result: {result}")
        
        # Parse the result
        if hasattr(result, 'data') and result.data:
            devices = result.data.get('devices', [])
            print(f"  Found {len(devices)} devices:")
            for device in devices:
                print(f"    - {device.get('name', 'Unknown')} ({device.get('id', 'No ID')})")
                print(f"      Status: {device.get('status', 'Unknown')}")
                print(f"      Paired: {device.get('is_paired', 'Unknown')}")
        
    except Exception as e:
        print(f"✗ Error testing get_devices: {e}")
        import traceback
        traceback.print_exc()
    
    # Test device status for each discovered device
    try:
        devices_result = await command_processor.get_devices()
        if hasattr(devices_result, 'data') and devices_result.data:
            devices = devices_result.data.get('devices', [])
            
            for device in devices[:2]:  # Test first 2 devices
                device_id = device.get('id')
                if device_id:
                    print(f"\nTesting device status for: {device.get('name', device_id)}")
                    
                    try:
                        status_result = await command_processor.get_status(device_id)
                        print(f"  ✓ Status: {status_result}")
                    except Exception as e:
                        print(f"  ✗ Error getting status: {e}")
                    
                    try:
                        pairing_result = await command_processor.get_pairing_status(device_id)
                        print(f"  ✓ Pairing status: {pairing_result}")
                    except Exception as e:
                        print(f"  ✗ Error getting pairing status: {e}")
        
    except Exception as e:
        print(f"✗ Error testing device status: {e}")
    
    # Test navigation command (this will likely fail without pairing, but we can test the structure)
    try:
        from androidtvmcp.models import NavigationCommand
        nav_command = NavigationCommand(direction="up")
        result = await command_processor.execute_navigation(nav_command)
        print(f"✓ Navigation command structure test: {result}")
        
    except Exception as e:
        print(f"✗ Navigation command test (expected to fail without pairing): {e}")
    
    # Stop discovery
    try:
        await device_manager.stop_discovery()
        print("\n✓ Device discovery stopped")
    except Exception as e:
        print(f"\n✗ Error stopping discovery: {e}")
    
    print("\nCommand Processor Test Complete")

if __name__ == "__main__":
    asyncio.run(test_command_processor())
