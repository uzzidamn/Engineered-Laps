#!/bin/bash

# Kafka Installation Script
# This script checks for Kafka, installs Homebrew if needed, and installs Kafka

set -e

echo "🔍 Checking for Kafka installation..."

# Function to check if Kafka is installed
check_kafka() {
    # Check in PATH
    if command -v kafka-server-start.sh &> /dev/null; then
        KAFKA_BIN=$(which kafka-server-start.sh)
        KAFKA_HOME=$(dirname $(dirname "$KAFKA_BIN"))
        echo "✅ Kafka found at: $KAFKA_HOME"
        return 0
    fi
    
    # Check common Homebrew locations
    for path in /opt/homebrew/Cellar/kafka /usr/local/Cellar/kafka; do
        if [ -d "$path" ]; then
            KAFKA_HOME=$(find "$path" -maxdepth 1 -type d | head -1)
            if [ -f "$KAFKA_HOME/bin/kafka-server-start.sh" ]; then
                echo "✅ Kafka found at: $KAFKA_HOME"
                return 0
            fi
        fi
    done
    
    # Check ~/kafka
    if [ -d "$HOME/kafka" ] && [ -f "$HOME/kafka/bin/kafka-server-start.sh" ]; then
        KAFKA_HOME="$HOME/kafka"
        echo "✅ Kafka found at: $KAFKA_HOME"
        return 0
    fi
    
    echo "❌ Kafka not found"
    return 1
}

# Function to check if Homebrew is installed
check_homebrew() {
    if command -v brew &> /dev/null; then
        echo "✅ Homebrew is installed at: $(which brew)"
        return 0
    else
        echo "❌ Homebrew not found"
        return 1
    fi
}

# Function to install Homebrew
install_homebrew() {
    echo ""
    echo "📦 Installing Homebrew..."
    echo "This may take a few minutes..."
    
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH (for Apple Silicon Macs)
    if [ -d "/opt/homebrew/bin" ]; then
        export PATH="/opt/homebrew/bin:$PATH"
        echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
    fi
    
    # For Intel Macs
    if [ -d "/usr/local/bin" ]; then
        export PATH="/usr/local/bin:$PATH"
    fi
    
    echo "✅ Homebrew installed successfully"
}

# Function to install Kafka via Homebrew
install_kafka_brew() {
    echo ""
    echo "📦 Installing Kafka via Homebrew..."
    echo "This may take a few minutes..."
    
    brew install kafka
    
    # Find Kafka installation
    if [ -d "/opt/homebrew/Cellar/kafka" ]; then
        KAFKA_HOME=$(find /opt/homebrew/Cellar/kafka -maxdepth 1 -type d | head -1)
    elif [ -d "/usr/local/Cellar/kafka" ]; then
        KAFKA_HOME=$(find /usr/local/Cellar/kafka -maxdepth 1 -type d | head -1)
    fi
    
    echo "✅ Kafka installed at: $KAFKA_HOME"
}

# Main installation flow
main() {
    echo "=========================================="
    echo "Kafka Installation Checker & Installer"
    echo "=========================================="
    echo ""
    
    # Step 1: Check if Kafka is already installed
    if check_kafka; then
        echo ""
        echo "✅ Kafka is already installed!"
        echo "   Location: $KAFKA_HOME"
        echo ""
        echo "To start Kafka, run:"
        echo "  bash scripts/start_kafka.sh"
        echo ""
        exit 0
    fi
    
    echo ""
    echo "Kafka needs to be installed."
    echo ""
    
    # Step 2: Check if Homebrew is installed
    if ! check_homebrew; then
        echo ""
        read -p "Homebrew is not installed. Install it now? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_homebrew
        else
            echo ""
            echo "❌ Installation cancelled. Please install Homebrew manually or install Kafka manually."
            echo "   Homebrew: https://brew.sh"
            echo "   Kafka: https://kafka.apache.org/downloads"
            exit 1
        fi
    fi
    
    # Ensure Homebrew is in PATH
    if [ -d "/opt/homebrew/bin" ]; then
        export PATH="/opt/homebrew/bin:$PATH"
    fi
    
    # Step 3: Install Kafka
    echo ""
    read -p "Install Kafka via Homebrew? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_kafka_brew
        
        echo ""
        echo "=========================================="
        echo "✅ Installation Complete!"
        echo "=========================================="
        echo ""
        echo "Kafka has been installed at: $KAFKA_HOME"
        echo ""
        echo "Next steps:"
        echo "1. Start Kafka:"
        echo "   bash scripts/start_kafka.sh"
        echo ""
        echo "2. Or set KAFKA_HOME and start manually:"
        echo "   export KAFKA_HOME=$KAFKA_HOME"
        echo "   \$KAFKA_HOME/bin/zookeeper-server-start.sh -daemon \$KAFKA_HOME/config/zookeeper.properties"
        echo "   sleep 5"
        echo "   \$KAFKA_HOME/bin/kafka-server-start.sh -daemon \$KAFKA_HOME/config/server.properties"
        echo ""
    else
        echo ""
        echo "Installation cancelled."
        echo "You can install Kafka manually from: https://kafka.apache.org/downloads"
        exit 1
    fi
}

# Run main function
main

