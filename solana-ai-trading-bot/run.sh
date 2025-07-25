#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting run script for Solana AI Trading Bot..."

# Check for Docker installation
if ! command -v docker &> /dev/null
then
    echo "Docker is not installed. Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if the Docker image exists
if [[ "$(docker images -q solana-ai-trading-bot 2> /dev/null)" == "" ]]; then
    echo "Docker image 'solana-ai-trading-bot' not found. Please run install.sh first to build the image."
    exit 1
fi

# Run the Docker container
# -d: Run container in background and print container ID
# -p 8000:8000: Map port 8000 of the host to port 8000 of the container
# --name: Assign a name to the container
# --restart unless-stopped: Automatically restart the container unless it is explicitly stopped
# -v $(pwd)/.env:/app/.env: Mount the .env file for secure environment variables
# -v $(pwd)/logs:/app/logs: Mount a volume for persistent logs
# -v $(pwd)/data:/app/data: Mount a volume for persistent data (e.g., SQLite DB)

echo "Running Docker container 'solana-ai-trading-bot-instance'..."
docker run -d \
    -p 8000:8000 \
    --name solana-ai-trading-bot-instance \
    --restart unless-stopped \
    -v "$(pwd)/.env":/app/.env \
    -v "$(pwd)/logs":/app/logs \
    -v "$(pwd)/data":/app/data \
    solana-ai-trading-bot

if [ $? -eq 0 ]; then
    echo "Docker container 'solana-ai-trading-bot-instance' started successfully."
    echo "You can check the logs using: docker logs -f solana-ai-trading-bot-instance"
    echo "The web interface should be available at http://localhost:8000 (if configured to serve on this port)."
else
    echo "Error: Docker container failed to start."
    exit 1
fi

# Make scripts executable
chmod +x install.sh run.sh