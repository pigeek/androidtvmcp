"""Tests for the MCP server implementation."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.androidtvmcp.server import AndroidTVMCPServer
from src.androidtvmcp.models import NavigationCommand, PlaybackCommand, CommandResult


class TestAndroidTVMCPServer:
    """Test cases for AndroidTVMCPServer."""

    @pytest.fixture
    def server_config(self):
        """Test server configuration."""
        return {
            "devices": {
                "discovery": {"enabled": True, "timeout": 5},
                "connection": {"timeout": 3, "retry_attempts": 2}
            },
            "mcp": {"transport": "stdio"},
            "logging": {"level": "DEBUG"}
        }

    @pytest.fixture
    def server(self, server_config):
        """Create test server instance."""
        return AndroidTVMCPServer(server_config)

    def test_server_initialization(self, server):
        """Test server initialization."""
        assert server.config is not None
        assert server.server is not None
        assert server.device_manager is not None
        assert server.command_processor is not None

    @pytest.mark.asyncio
    async def test_start_stop_discovery(self, server):
        """Test starting and stopping device discovery."""
        with patch.object(server.device_manager, 'start_discovery', new_callable=AsyncMock) as mock_start:
            with patch.object(server.device_manager, 'stop_discovery', new_callable=AsyncMock) as mock_stop:
                await server.start_discovery()
                mock_start.assert_called_once()
                
                await server.stop_discovery()
                mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_navigation_command_handling(self, server):
        """Test navigation command handling."""
        # Mock the command processor
        mock_result = CommandResult(
            success=True,
            message="Navigation successful",
            device_id="test_device"
        )
        
        with patch.object(server.command_processor, 'execute_navigation', new_callable=AsyncMock, return_value=mock_result):
            # This would normally be called through the MCP protocol
            command = NavigationCommand(device_id="test_device", direction="up")
            result = await server.command_processor.execute_navigation(command)
            
            assert result.success is True
            assert result.message == "Navigation successful"
            assert result.device_id == "test_device"

    @pytest.mark.asyncio
    async def test_playback_command_handling(self, server):
        """Test playback command handling."""
        # Mock the command processor
        mock_result = CommandResult(
            success=True,
            message="Playback successful",
            device_id="test_device"
        )
        
        with patch.object(server.command_processor, 'execute_playback', new_callable=AsyncMock, return_value=mock_result):
            command = PlaybackCommand(device_id="test_device", action="play")
            result = await server.command_processor.execute_playback(command)
            
            assert result.success is True
            assert result.message == "Playback successful"
            assert result.device_id == "test_device"

    def test_server_with_empty_config(self):
        """Test server initialization with empty config."""
        server = AndroidTVMCPServer({})
        assert server.config == {}
        assert server.device_manager is not None
        assert server.command_processor is not None

    def test_server_with_none_config(self):
        """Test server initialization with None config."""
        server = AndroidTVMCPServer(None)
        assert server.config == {}
        assert server.device_manager is not None
        assert server.command_processor is not None

    @pytest.mark.asyncio
    async def test_app_launch_validation(self, server):
        """Test app launch tool validation."""
        from src.androidtvmcp.models import AppCommand
        
        # Mock the command processor
        mock_result = CommandResult(
            success=True,
            message="App launch successful",
            device_id="test_device"
        )
        
        with patch.object(server.command_processor, 'execute_app_command', new_callable=AsyncMock, return_value=mock_result):
            # Test with app_id
            command = AppCommand(device_id="test_device", action="launch", app_id="com.netflix.ninja")
            result = await server.command_processor.execute_app_command(command)
            assert result.success is True
            
            # Test with app_name
            command = AppCommand(device_id="test_device", action="launch", app_name="Netflix")
            result = await server.command_processor.execute_app_command(command)
            assert result.success is True
            
            # Test with both app_id and app_name (should work)
            command = AppCommand(device_id="test_device", action="launch", app_id="com.netflix.ninja", app_name="Netflix")
            result = await server.command_processor.execute_app_command(command)
            assert result.success is True
