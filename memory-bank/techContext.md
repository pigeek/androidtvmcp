# Technical Context

## Technology Stack

### Core Technologies
- **Python 3.8+**: Primary runtime with asyncio for async operations
- **MCP (Model Context Protocol)**: Using official Python SDK for server implementation
- **androidtvremote2**: Python library for Android TV device communication
- **Zeroconf**: Network service discovery for finding Android TV devices
- **Pydantic**: Data validation and type safety throughout

### Development Environment
- **Operating System**: Linux 5.15
- **Shell**: /bin/bash
- **Working Directory**: /home/ilyap/workspace/atvrc2mcp
- **Development Tools**: VSCode, Python development ecosystem
- **Package Manager**: pip with modern pyproject.toml configuration

## Technical Architecture

### MCP Integration
- ✅ Full MCP server implementation using official Python SDK
- ✅ 9 comprehensive tools for Android TV control operations
- ✅ 3 resource types for device information and state
- ✅ stdio transport with planned TCP transport support
- ✅ Proper MCP protocol compliance with error handling

### Android TV Communication
- ✅ androidtvremote2 library integration for device communication
- ✅ Zeroconf-based device discovery on local network
- ✅ Async connection management with retry logic
- ✅ Command abstraction layer with comprehensive error handling
- ✅ State synchronization and device monitoring

## Key Dependencies

### Production Dependencies
- **mcp>=1.0.0**: Official MCP Python SDK for server implementation
- **androidtvremote2>=0.1.0**: Android TV remote control library
- **zeroconf>=0.131.0**: Network service discovery (mDNS/Bonjour)
- **pydantic>=2.0.0**: Data validation and type safety
- **click>=8.0.0**: CLI framework for command-line tools
- **asyncio-mqtt>=0.11.0**: MQTT support for advanced features

### Development Dependencies
- **pytest>=7.0.0**: Testing framework with async support
- **pytest-asyncio>=0.21.0**: Async test support
- **black>=23.0.0**: Code formatting
- **isort>=5.12.0**: Import sorting
- **mypy>=1.0.0**: Static type checking
- **pre-commit>=3.0.0**: Git hooks for code quality

## Technical Constraints

### Android TV Limitations
- ✅ Network-only communication via androidtvremote2 protocol
- ✅ Device discovery requires same network segment
- ✅ Command execution latency depends on network conditions
- ✅ Device pairing and authentication complexity handled by library

### MCP Requirements
- ✅ Full MCP protocol specification compliance implemented
- ✅ Proper tool and resource schema definitions
- ✅ MCP-compliant error handling and response formats
- ✅ stdio transport implemented, TCP transport planned

## Development Setup

### Prerequisites
- ✅ Python 3.8+ with asyncio support
- ✅ Network access to Android TV devices on same subnet
- ✅ MCP client for testing (Cline, Claude Desktop, etc.)
- ✅ pip package manager for dependency installation

### Installation
```bash
# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Linux/macOS
# venv\Scripts\activate   # On Windows

# Development installation
pip install -e ".[dev]"

# Production installation
pip install androidtvmcp
```

### Configuration
- ✅ JSON-based configuration with CLI override support
- ✅ Device discovery timeout and retry settings
- ✅ Connection management parameters
- ✅ Logging levels and output configuration
- ✅ MCP transport selection (stdio/tcp)

## Security Considerations
- ✅ Input validation through Pydantic models
- ✅ Device authentication handled by androidtvremote2
- ✅ Network communication security via library
- ✅ Error message sanitization to prevent information leakage

## Performance Requirements
- ✅ Async/await throughout for non-blocking operations
- ✅ Connection pooling and reuse for multiple devices
- ✅ Configurable timeouts and retry mechanisms
- ✅ Efficient state management with minimal memory usage

## Testing Strategy
- ✅ pytest-based unit testing framework
- ✅ Async test support with pytest-asyncio
- ✅ Mock-based testing for device interactions
- [ ] Integration testing with real Android TV devices
- [ ] MCP protocol compliance validation
- [ ] Performance benchmarking and load testing

## Deployment
- ✅ CLI-based server management (serve, discover, test, config)
- ✅ Configuration file support with JSON format
- ✅ Standalone executable via pip installation
- ✅ stdio transport for MCP client integration
- [ ] TCP transport for network-based MCP clients
- [ ] Service/daemon deployment documentation

## Implementation Status
- ✅ Complete core implementation finished
- ✅ All major components implemented and documented
- ✅ CLI tools for full lifecycle management
- ✅ Comprehensive error handling and logging
- ✅ Type safety throughout with Pydantic
- [ ] Real-world testing and validation needed
- [ ] Performance optimization and monitoring
