#!/usr/bin/env bash
# DECEPTINET Deployment Verification Script
# Runs smoke tests to verify deployment success

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:3000}"
MAX_RETRIES=30
RETRY_INTERVAL=10

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}DECEPTINET Deployment Verification${NC}"
echo -e "${GREEN}=====================================${NC}"

# Function to check endpoint
check_endpoint() {
    local url=$1
    local name=$2
    local retries=0
    
    echo -e "\n${YELLOW}Checking ${name}...${NC}"
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -f -s "${url}" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ ${name} is responding${NC}"
            return 0
        fi
        
        retries=$((retries + 1))
        echo -e "${YELLOW}Attempt ${retries}/${MAX_RETRIES} - waiting ${RETRY_INTERVAL}s...${NC}"
        sleep $RETRY_INTERVAL
    done
    
    echo -e "${RED}✗ ${name} failed to respond${NC}"
    return 1
}

# Function to check health endpoint
check_health() {
    local url=$1
    local name=$2
    
    echo -e "\n${YELLOW}Checking ${name} health...${NC}"
    
    response=$(curl -s "${url}")
    status=$(echo "$response" | jq -r '.status' 2>/dev/null || echo "unknown")
    
    if [ "$status" = "alive" ] || [ "$status" = "healthy" ] || [ "$status" = "ready" ]; then
        echo -e "${GREEN}✓ ${name} health check passed${NC}"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
        return 0
    else
        echo -e "${RED}✗ ${name} health check failed${NC}"
        echo "$response"
        return 1
    fi
}

# Check infrastructure services
echo -e "\n${YELLOW}=== Checking Infrastructure Services ===${NC}"

# Check API root
check_endpoint "${API_URL}/" "Deception Engine Root"

# Check API health
check_health "${API_URL}/health" "Deception Engine"

# Check API readiness
check_health "${API_URL}/ready" "Deception Engine Readiness"

# Check API detailed health
check_health "${API_URL}/api/health" "Deception Engine (detailed)"

# Test API functionality
echo -e "\n${YELLOW}=== Testing API Functionality ===${NC}"

# List honeypots
echo -e "\n${YELLOW}Listing honeypots...${NC}"
response=$(curl -s "${API_URL}/api/honeypots")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Honeypots endpoint working${NC}"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
else
    echo -e "${RED}✗ Failed to list honeypots${NC}"
fi

# List strategies
echo -e "\n${YELLOW}Listing deception strategies...${NC}"
response=$(curl -s "${API_URL}/api/strategies")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Strategies endpoint working${NC}"
    count=$(echo "$response" | jq '. | length' 2>/dev/null || echo "0")
    echo -e "Found ${count} strategies"
else
    echo -e "${RED}✗ Failed to list strategies${NC}"
fi

# Check metrics
echo -e "\n${YELLOW}Checking metrics...${NC}"
response=$(curl -s "${API_URL}/api/metrics")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Metrics endpoint working${NC}"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
else
    echo -e "${RED}✗ Failed to get metrics${NC}"
fi

# Check dashboard (if available)
if [ ! -z "$DASHBOARD_URL" ]; then
    echo -e "\n${YELLOW}=== Checking Dashboard ===${NC}"
    check_endpoint "${DASHBOARD_URL}" "React Dashboard"
fi

# Summary
echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}Verification Complete!${NC}"
echo -e "${GREEN}=====================================${NC}"

echo -e "\n${YELLOW}API Endpoints:${NC}"
echo -e "Root: ${GREEN}${API_URL}/${NC}"
echo -e "Health: ${GREEN}${API_URL}/health${NC}"
echo -e "Ready: ${GREEN}${API_URL}/ready${NC}"
echo -e "Docs: ${GREEN}${API_URL}/api/docs${NC}"
echo -e "Honeypots: ${GREEN}${API_URL}/api/honeypots${NC}"
echo -e "Strategies: ${GREEN}${API_URL}/api/strategies${NC}"
echo -e "Metrics: ${GREEN}${API_URL}/api/metrics${NC}"

if [ ! -z "$DASHBOARD_URL" ]; then
    echo -e "\n${YELLOW}Dashboard:${NC}"
    echo -e "URL: ${GREEN}${DASHBOARD_URL}${NC}"
fi

echo -e "\n${GREEN}Deployment verification successful!${NC}"
