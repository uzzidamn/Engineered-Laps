#!/bin/bash

# Complete Pipeline Runner
# This script runs the complete F1 streaming pipeline

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🏎️ F1 Real-Time Telemetry Streaming Pipeline"
echo "=============================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Check if Kafka is running
if ! pgrep -f "kafka.Kafka" > /dev/null; then
    echo "Starting Kafka..."
    bash scripts/start_kafka.sh
    sleep 5
fi

echo ""
echo "Pipeline components ready!"
echo ""
echo "Next steps:"
echo "1. Run notebook 01_data_preparation.ipynb to prepare data"
echo "2. Run notebook 02_cache_setup.ipynb to setup cache"
echo "3. Run notebook 03_kafka_producer.ipynb to start streaming"
echo "4. Run notebook 05_kafka_consumer.ipynb in another terminal/process to consume"
echo "5. Run 'streamlit run src/dashboard.py' to view the live dashboard"
echo ""
echo "Or run notebooks sequentially:"
echo "  jupyter notebook notebooks/"

