#!/bin/bash

# Automated Kafka Installation Script (Non-Interactive)
# This script automatically installs Homebrew and Kafka if not present

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
    
    return 1
}

# Function to check if Homebrew is installed
check_homebrew() {
    if command -v brew &> /dev/null; then
        echo "✅ Homebrew is installed"
        return 0
    else
        return 1
    fi
}

# Function to install Homebrew
install_homebrew() {
    echo ""
    echo "📦 Installing Homebrew..."
    echo "This may take a few minutes..."
    
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH
    if [ -d "/opt/homebrew/bin" ]; then
        export PATH="/opt/homebrew/bin:$PATH"
        if [ -f ~/.zshrc ]; then
            echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
        fi
    fi
    
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
    
    echo "✅ Kafka installed successfully"
}

# Main installation flow
main() {
    echo "=========================================="
    echo "Kafka Auto-Installation Script"
    echo "=========================================="
    echo ""
    
    # Step 1: Check if Kafka is already installed
    if check_kafka; then
        echo ""
        echo "✅ Kafka is already installed!"
        echo "   Location: $KAFKA_HOME"
        echo ""
        exit 0
    fi
    
    echo "Kafka not found. Proceeding with installation..."
    echo ""
    
    # Step 2: Check if Homebrew is installed
    if ! check_homebrew; then
        echo "Homebrew not found. Installing Homebrew..."
        install_homebrew
        
        # Ensure Homebrew is in PATH for this session
        if [ -d "/opt/homebrew/bin" ]; then
            export PATH="/opt/homebrew/bin:$PATH"
        fi
        if [ -d "/usr/local/bin" ]; then
            export PATH="/usr/local/bin:$PATH"
        fi
    fi
    
    # Step 3: Install Kafka
    echo ""
    echo "Installing Kafka..."
    install_kafka_brew
    
    echo ""
    echo "=========================================="
    echo "✅ Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Next step: Start Kafka with:"
    echo "  bash scripts/start_kafka.sh"
    echo ""
}

# Run main function
main

