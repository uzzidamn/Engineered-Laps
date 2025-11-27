#!/bin/bash

echo "🛑 Stopping all Kafka producers..."
echo "=================================="

# Find all producer processes
producers=$(ps aux | grep -E "simple_producer|run_producer" | grep -v grep | awk '{print $2}')

if [ -z "$producers" ]; then
    echo "✅ No producers currently running"
    exit 0
fi

# Show what we found
echo "Found producer processes:"
ps aux | grep -E "simple_producer|run_producer" | grep -v grep | awk '{printf "  PID: %s, CPU: %s%%, Runtime: %s\n", $2, $3, $10}'

echo ""
read -p "Stop these producers? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    for pid in $producers; do
        echo "Stopping PID $pid..."
        kill -SIGINT $pid 2>/dev/null
        
        # Wait up to 5 seconds for graceful shutdown
        for i in {1..5}; do
            if ! ps -p $pid > /dev/null 2>&1; then
                echo "  ✅ Process $pid stopped gracefully"
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if ps -p $pid > /dev/null 2>&1; then
            echo "  ⚠️  Process $pid didn't stop gracefully, forcing..."
            kill -9 $pid 2>/dev/null
            echo "  ✅ Process $pid force-stopped"
        fi
    done
    
    echo ""
    echo "✅ All producers stopped!"
else
    echo "❌ Cancelled"
fi

