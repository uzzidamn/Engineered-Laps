#!/bin/bash

# Kafka Start Script
# This script starts ZooKeeper and Kafka services

echo "Starting Kafka and ZooKeeper services..."

# Set Kafka and ZooKeeper paths (adjust these based on your installation)
KAFKA_HOME="${KAFKA_HOME:-/opt/kafka}"

# Find Kafka installation and set paths
KAFKA_BIN=""
KAFKA_CONFIG=""

# Try to find kafka-server-start.sh in various locations
if [ -z "$KAFKA_BIN" ]; then
    # Check if KAFKA_HOME is set and valid
    if [ -n "$KAFKA_HOME" ] && [ -f "$KAFKA_HOME/bin/kafka-server-start.sh" ]; then
        KAFKA_BIN="$KAFKA_HOME/bin"
        KAFKA_CONFIG="$KAFKA_HOME/config"
    # Try Homebrew installation (libexec structure)
    elif KAFKA_BIN_PATH=$(find /opt/homebrew/Cellar/kafka -name "kafka-server-start.sh" 2>/dev/null | head -1); then
        KAFKA_BIN=$(dirname "$KAFKA_BIN_PATH")
        KAFKA_CONFIG=$(dirname "$KAFKA_BIN")/config
    elif KAFKA_BIN_PATH=$(find /usr/local/Cellar/kafka -name "kafka-server-start.sh" 2>/dev/null | head -1); then
        KAFKA_BIN=$(dirname "$KAFKA_BIN_PATH")
        KAFKA_CONFIG=$(dirname "$KAFKA_BIN")/config
    # Try standard installation
    elif [ -d "$HOME/kafka" ] && [ -f "$HOME/kafka/bin/kafka-server-start.sh" ]; then
        KAFKA_BIN="$HOME/kafka/bin"
        KAFKA_CONFIG="$HOME/kafka/config"
    # Try /opt/kafka
    elif [ -d "/opt/kafka" ] && [ -f "/opt/kafka/bin/kafka-server-start.sh" ]; then
        KAFKA_BIN="/opt/kafka/bin"
        KAFKA_CONFIG="/opt/kafka/config"
    fi
fi

# Check if we found Kafka
if [ -z "$KAFKA_BIN" ] || [ ! -f "$KAFKA_BIN/kafka-server-start.sh" ]; then
    echo "Error: Kafka installation not found. Please install Kafka first."
    echo "Manual installation instructions:"
    echo "1. Download Kafka from https://kafka.apache.org/downloads"
    echo "2. Extract to ~/kafka"
    echo "3. Set KAFKA_HOME environment variable"
    echo ""
    echo "Or install via Homebrew: brew install kafka"
    exit 1
fi

echo "Using Kafka binaries at: $KAFKA_BIN"
echo "Using Kafka config at: $KAFKA_CONFIG"

# Check for Java
if ! command -v java &> /dev/null; then
    echo "❌ Error: Java is not installed or not in PATH"
    echo "Kafka requires Java JDK 11 or higher."
    echo ""
    echo "Install Java:"
    echo "  brew install openjdk@11"
    echo "  Or download from: https://www.oracle.com/java/technologies/downloads/"
    exit 1
fi

JAVA_VERSION=$(java -version 2>&1 | head -1)
echo "✅ Found Java: $JAVA_VERSION"

# Check if ZooKeeper script exists (for older Kafka versions)
ZOOKEEPER_SCRIPT="$KAFKA_BIN/zookeeper-server-start.sh"
USE_ZOOKEEPER=false

if [ -f "$ZOOKEEPER_SCRIPT" ]; then
    USE_ZOOKEEPER=true
    echo "Starting ZooKeeper (required for this Kafka version)..."
    $ZOOKEEPER_SCRIPT -daemon $KAFKA_CONFIG/zookeeper.properties
    sleep 5
    echo "✅ ZooKeeper started"
else
    echo "ℹ️  ZooKeeper not required (Kafka is using KRaft mode)"
fi

# Start Kafka
echo "Starting Kafka..."
$KAFKA_BIN/kafka-server-start.sh -daemon $KAFKA_CONFIG/server.properties

# Wait for Kafka to start
sleep 10

# Check if Kafka is running
if pgrep -f "kafka.Kafka" > /dev/null; then
    echo "✅ Kafka started successfully!"
    echo "Kafka is running on localhost:9092"
    if [ "$USE_ZOOKEEPER" = true ]; then
        echo "ZooKeeper is running on localhost:2181"
    fi
else
    echo "❌ Error: Kafka failed to start"
    echo "Check logs for details"
    exit 1
fi

# Create the F1 telemetry topic
echo "Creating F1 telemetry topic..."
$KAFKA_BIN/kafka-topics.sh --create \
    --topic f1-speed-stream \
    --bootstrap-server localhost:9092 \
    --partitions 4 \
    --replication-factor 1 \
    --if-not-exists

echo "Topic 'f1-speed-stream' created successfully!"
echo "Use './scripts/stop_kafka.sh' to stop the services"

