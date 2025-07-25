#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting installation script for Solana AI Trading Bot..."

# Check for Docker installation
if ! command -v docker &> /dev/null
then
    echo "Docker is not installed. Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "Docker found. Proceeding with image build."

# Build the Docker image
# Ensure you are in the root directory of the project where Dockerfile is located
# The --platform linux/arm64 is crucial for Oracle ARM instances

echo "Building Docker image 'solana-ai-trading-bot' for ARM64 architecture..."
docker build --platform linux/arm64 -t solana-ai-trading-bot .

if [ $? -eq 0 ]; then
    echo "Docker image 'solana-ai-trading-bot' built successfully."
else
    echo "Error: Docker image build failed. Please check the Dockerfile and your Docker setup."
    exit 1
fi

echo "Installation script finished. You can now run the bot using run.sh."