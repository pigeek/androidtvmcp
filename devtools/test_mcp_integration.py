#!/usr/bin/env python3
"""
Test script to validate MCP server functionality
"""
import asyncio
import json
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from androidtvmcp.server import AndroidTVMCPServer

async def test_mcp_server():
    """Test the MCP server functionality"""
    print("Testing AndroidTVMCP MCP Server Integration")
    print("=" * 50)
    
    # Create the server
    server = AndroidTVMCPServer()
    
    # Test server initialization
    print("✓ Server created successfully")
    
    # Start device discovery
    try:
        await server.start_discovery()
        print("✓ Device discovery started")
        
        # Wait a moment for discovery
        await asyncio.sleep(3)
        
    except Exception as e:
        print(f"✗ Error starting discovery: {e}")
    
    # Test tool listing
    try:
        # Get the tools directly from the server's registered handlers
        tools = []
        for handler_name, handler in server.server._tool_handlers.items():
            if hasattr(handler, '__name__'):
                tools.append(handler_name)
        
        print(f"✓ Found {len(tools)} MCP tool handlers registered")
        
        # Test the list_tools handler directly
        list_tools_handler = server.server._tool_handlers.get('list_tools')
        if list_tools_handler:
            tools_response = await list_tools_handler()
            print(f"✓ Found {len(tools_response)} MCP tools:")
            for tool in tools_response:
                print(f"  - {tool.name}: {tool.description}")
        
    except Exception as e:
        print(f"✗ Error listing tools: {e}")
        import traceback
        traceback.print_exc()
    
    # Test resource listing
    try:
        list_resources_handler = server.server._resource_handlers.get('list_resources')
        if list_resources_handler:
            resources_response = await list_resources_handler()
            print(f"✓ Found {len(resources_response)} MCP resources:")
            for resource in resources_response:
                print(f"  - {resource.uri}: {resource.name}")
        
    except Exception as e:
        print(f"✗ Error listing resources: {e}")
        import traceback
        traceback.print_exc()
    
    # Test device discovery tool
    try:
        call_tool_handler = server.server._tool_handlers.get('call_tool')
        if call_tool_handler:
            discover_response = await call_tool_handler(
                name="atv_get_devices",
                arguments={}
            )
            
            print("✓ Device discovery tool executed successfully")
            if discover_response:
                result_text = discover_response[0].text
                print(f"  Result: {result_text}")
                
                # Try to parse as JSON
                try:
                    result = json.loads(result_text)
                    if isinstance(result, dict) and 'devices' in result:
                        devices = result['devices']
                        print(f"  Found {len(devices)} devices")
                        for device in devices:
                            print(f"    - {device.get('name', 'Unknown')} ({device.get('id', 'No ID')})")
                    else:
                        print(f"  Raw result: {result}")
                except json.JSONDecodeError:
                    print(f"  Non-JSON result: {result_text}")
        
    except Exception as e:
        print(f"✗ Error testing device discovery: {e}")
        import traceback
        traceback.print_exc()
    
    # Stop discovery
    try:
        await server.stop_discovery()
        print("✓ Device discovery stopped")
    except Exception as e:
        print(f"✗ Error stopping discovery: {e}")
    
    print("\nMCP Server Integration Test Complete")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
