#!/bin/bash

# Kafka Stop Script
# This script stops Kafka and ZooKeeper services

echo "Stopping Kafka and ZooKeeper services..."

# Set Kafka path
KAFKA_HOME="${KAFKA_HOME:-/opt/kafka}"

# Find Kafka installation if not set
if [ ! -d "$KAFKA_HOME" ]; then
    if [ -d "/opt/homebrew/Cellar/kafka" ]; then
        KAFKA_HOME=$(find /opt/homebrew/Cellar/kafka -maxdepth 1 -type d | head -1)
    elif [ -d "/usr/local/Cellar/kafka" ]; then
        KAFKA_HOME=$(find /usr/local/Cellar/kafka -maxdepth 1 -type d | head -1)
    elif [ -d "$HOME/kafka" ]; then
        KAFKA_HOME="$HOME/kafka"
    else
        echo "Error: Kafka installation not found."
        exit 1
    fi
fi

# Stop Kafka
echo "Stopping Kafka..."
pkill -f "kafka.Kafka" || echo "Kafka was not running"

# Stop ZooKeeper
echo "Stopping ZooKeeper..."
pkill -f "zookeeper" || echo "ZooKeeper was not running"

# Wait for processes to stop
sleep 5

echo "Kafka and ZooKeeper services stopped successfully!"

