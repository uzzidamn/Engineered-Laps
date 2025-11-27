#!/bin/bash

cd "$(dirname "$0")/.."

echo "🏎️  Starting F1 Kafka Producer (Single Race)"
echo "============================================="
echo ""

# Check if Kafka is running
if ! nc -z localhost 9092 2>/dev/null; then
    echo "❌ Kafka is not running on localhost:9092"
    echo ""
    echo "Start Kafka first:"
    echo "  /opt/homebrew/bin/kafka-server-start /opt/homebrew/etc/kafka/server.properties"
    exit 1
fi

echo "✅ Kafka is running"
echo ""

# Stop any existing producers
if ps aux | grep -E "simple_producer|run_producer" | grep -v grep > /dev/null; then
    echo "⚠️  Another producer is already running"
    echo ""
    read -p "Stop it and start new one? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./scripts/stop_producer.sh
    else
        echo "❌ Cancelled"
        exit 1
    fi
fi

# Activate venv and run
if [ -f "venv/bin/activate" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found"
    echo "Create it first: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "🚀 Starting single-race producer..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python scripts/simple_producer_once.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Producer finished!"
echo ""
echo "📊 View results:"
echo "   • Grafana: http://localhost:3000"
echo "   • Check consumer lag:"
echo "     /opt/homebrew/bin/kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group grafana_bridge"

