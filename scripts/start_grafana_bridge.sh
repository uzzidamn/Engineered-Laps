#!/bin/bash
# Start Grafana Kafka Bridge Service

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   F1 Grafana Kafka Bridge Service${NC}"
echo -e "${GREEN}========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "\n${YELLOW}Project root:${NC} $PROJECT_ROOT"

# Check if virtual environment exists
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment found"
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo -e "${YELLOW}⚠${NC}  Virtual environment not found at $PROJECT_ROOT/venv"
    echo -e "${YELLOW}   Using system Python...${NC}"
fi

# Check if configuration exists
CONFIG_FILE="$PROJECT_ROOT/config/grafana_bridge_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}✗${NC} Configuration file not found: $CONFIG_FILE"
    exit 1
fi
echo -e "${GREEN}✓${NC} Configuration file found"

# Check if Kafka is running
echo -e "\n${YELLOW}Checking Kafka broker...${NC}"
if nc -z localhost 9092 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Kafka broker is running on localhost:9092"
else
    echo -e "${RED}✗${NC} Kafka broker is not running on localhost:9092"
    echo -e "${YELLOW}   Please start Kafka first:${NC}"
    echo -e "   ./scripts/start_kafka.sh"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC}  Flask not found. Installing required packages..."
    pip install flask flask-cors
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   Starting Bridge Service${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}Service will be available at:${NC}"
echo -e "  • Bridge API: http://localhost:5001"
echo -e "  • Stats: http://localhost:5001/stats"
echo -e "  • Drivers: http://localhost:5001/drivers"
echo -e "\n${YELLOW}Configure Grafana datasource:${NC}"
echo -e "  • Type: JSON API"
echo -e "  • URL: http://localhost:5001"
echo -e "\n${YELLOW}Press Ctrl+C to stop${NC}\n"

# Change to project root
cd "$PROJECT_ROOT"

# Start the bridge service
python scripts/grafana_kafka_bridge.py

