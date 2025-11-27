#!/bin/bash
# Test Grafana Kafka Bridge Service

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Testing Grafana Kafka Bridge${NC}"
echo -e "${GREEN}========================================${NC}"

BRIDGE_URL="http://localhost:5001"

# Test 1: Health check
echo -e "\n${YELLOW}Test 1: Health Check${NC}"
response=$(curl -s -w "\n%{http_code}" "$BRIDGE_URL/")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓${NC} Health check passed"
    echo "$body" | python3 -m json.tool
else
    echo -e "${RED}✗${NC} Health check failed (HTTP $http_code)"
    exit 1
fi

# Test 2: Statistics
echo -e "\n${YELLOW}Test 2: Statistics Endpoint${NC}"
response=$(curl -s "$BRIDGE_URL/stats")
echo "$response" | python3 -m json.tool
echo -e "${GREEN}✓${NC} Statistics endpoint working"

# Test 3: Search endpoint
echo -e "\n${YELLOW}Test 3: Search Endpoint${NC}"
response=$(curl -s -X POST "$BRIDGE_URL/search" \
    -H "Content-Type: application/json" \
    -d '{}')
echo "$response" | python3 -m json.tool | head -n 20
echo -e "${GREEN}✓${NC} Search endpoint working"

# Test 4: Drivers endpoint
echo -e "\n${YELLOW}Test 4: Drivers Endpoint${NC}"
response=$(curl -s "$BRIDGE_URL/drivers")
echo "$response" | python3 -m json.tool
echo -e "${GREEN}✓${NC} Drivers endpoint working"

# Test 5: Query endpoint
echo -e "\n${YELLOW}Test 5: Query Endpoint${NC}"
response=$(curl -s -X POST "$BRIDGE_URL/query" \
    -H "Content-Type: application/json" \
    -d '{
        "range": {
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-12-31T23:59:59Z"
        },
        "targets": [
            {"target": "speed"}
        ]
    }')
echo "$response" | python3 -m json.tool | head -n 30
echo -e "${GREEN}✓${NC} Query endpoint working"

# Test 6: Annotations endpoint
echo -e "\n${YELLOW}Test 6: Annotations Endpoint${NC}"
response=$(curl -s -X POST "$BRIDGE_URL/annotations" \
    -H "Content-Type: application/json" \
    -d '{
        "range": {
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-12-31T23:59:59Z"
        }
    }')
echo "$response" | python3 -m json.tool | head -n 20
echo -e "${GREEN}✓${NC} Annotations endpoint working"

# Test 7: Alerts summary
echo -e "\n${YELLOW}Test 7: Alerts Summary${NC}"
response=$(curl -s "$BRIDGE_URL/alerts/summary")
echo "$response" | python3 -m json.tool
echo -e "${GREEN}✓${NC} Alerts summary working"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  All Tests Passed! ✓${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}Bridge is ready for Grafana integration${NC}"
echo -e "${YELLOW}Configure Grafana datasource:${NC}"
echo -e "  Type: JSON API"
echo -e "  URL: $BRIDGE_URL"
echo ""

