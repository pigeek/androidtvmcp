#!/usr/bin/env python3
"""
Test script to validate MCP client-server communication
"""
import asyncio
import json
import sys
import os
from typing import Any, Dict

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def test_mcp_client():
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
                
                # Test device discovery tool
                try:
                    result = await session.call_tool("atv_get_devices", {})
                    print("✓ Device discovery tool executed successfully")
                    
                    if result.content:
                        content = result.content[0]
                        if hasattr(content, 'text'):
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
    asyncio.run(test_mcp_client())
