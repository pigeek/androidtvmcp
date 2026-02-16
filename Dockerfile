FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for pychromecast, zeroconf, and pynput (evdev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libavahi-client3 \
    libavahi-common3 \
    linux-libc-dev \
    libc6-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy all necessary files for building
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir .

# Run the MCP server
# Note: Requires --network host for mDNS device discovery
CMD ["androidtvmcp"]
