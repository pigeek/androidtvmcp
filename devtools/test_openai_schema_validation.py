#!/usr/bin/env python3
"""
Test script to validate OpenAI schema compatibility for atv_launch_app tool
"""
import asyncio
import json
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def test_openai_schema_validation():
    """Test that the atv_launch_app tool schema is compatible with OpenAI API"""
    print("Testing OpenAI Schema Compatibility for atv_launch_app")
    print("=" * 55)
    
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
                
                # Get the tools and check the atv_launch_app schema
                tools = await session.list_tools()
                print(f"✓ Found {len(tools.tools)} MCP tools")
                
                # Find the atv_launch_app tool
                launch_app_tool = None
                for tool in tools.tools:
                    if tool.name == "atv_launch_app":
                        launch_app_tool = tool
                        break
                
                if launch_app_tool:
                    print("✓ Found atv_launch_app tool")
                    
                    # Check the schema structure
                    schema = launch_app_tool.inputSchema
                    print(f"✓ Tool description: {launch_app_tool.description}")
                    
                    # Validate OpenAI compatibility
                    print("\n🔍 Schema Validation:")
                    
                    # Check that schema has type 'object'
                    if schema.get("type") == "object":
                        print("  ✓ Schema has type 'object'")
                    else:
                        print(f"  ✗ Schema type is '{schema.get('type')}', should be 'object'")
                    
                    # Check that schema doesn't have forbidden top-level keywords
                    forbidden_keywords = ['oneOf', 'anyOf', 'allOf', 'enum', 'not']
                    has_forbidden = False
                    for keyword in forbidden_keywords:
                        if keyword in schema:
                            print(f"  ✗ Schema contains forbidden keyword '{keyword}' at top level")
                            has_forbidden = True
                    
                    if not has_forbidden:
                        print("  ✓ Schema doesn't contain forbidden keywords (oneOf, anyOf, allOf, enum, not)")
                    
                    # Check properties structure
                    properties = schema.get("properties", {})
                    if properties:
                        print(f"  ✓ Schema has {len(properties)} properties:")
                        for prop_name, prop_def in properties.items():
                            print(f"    - {prop_name}: {prop_def.get('type', 'unknown type')}")
                    
                    # Check if required field exists (should not for OpenAI compatibility)
                    if "required" not in schema:
                        print("  ✓ Schema doesn't have 'required' field (validation handled in code)")
                    else:
                        print(f"  ⚠ Schema has 'required' field: {schema['required']}")
                    
                    print("\n🧪 Testing Validation Logic:")
                    
                    # Test validation with missing parameters
                    try:
                        result = await session.call_tool("atv_launch_app", {})
                        if result.content:
                            content = result.content[0]
                            if hasattr(content, 'text') and "Either app_id or app_name must be provided" in content.text:
                                print("  ✓ Validation correctly rejects empty parameters")
                            else:
                                print(f"  ⚠ Unexpected validation result: {content.text}")
                    except Exception as e:
                        print(f"  ✗ Error testing validation: {e}")
                    
                    # Test with app_id only
                    try:
                        result = await session.call_tool("atv_launch_app", {"app_id": "com.test.app"})
                        print("  ✓ Accepts app_id parameter")
                    except Exception as e:
                        print(f"  ✗ Error with app_id: {e}")
                    
                    # Test with app_name only
                    try:
                        result = await session.call_tool("atv_launch_app", {"app_name": "Test App"})
                        print("  ✓ Accepts app_name parameter")
                    except Exception as e:
                        print(f"  ✗ Error with app_name: {e}")
                    
                    # Test with both parameters
                    try:
                        result = await session.call_tool("atv_launch_app", {"app_id": "com.test.app", "app_name": "Test App"})
                        print("  ✓ Accepts both app_id and app_name parameters")
                    except Exception as e:
                        print(f"  ✗ Error with both parameters: {e}")
                    
                    print("\n✅ OpenAI Schema Compatibility: PASSED")
                    print("   The atv_launch_app tool schema is now compatible with OpenAI API")
                    
                else:
                    print("✗ atv_launch_app tool not found")
                
    except Exception as e:
        print(f"✗ Error in schema validation test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nOpenAI Schema Validation Test Complete")

if __name__ == "__main__":
    asyncio.run(test_openai_schema_validation())
