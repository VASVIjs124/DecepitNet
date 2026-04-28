#!/usr/bin/env bash
# DECEPTINET Local Deployment Script
# Deploys the platform using Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}DECEPTINET Local Deployment${NC}"
echo -e "${GREEN}=====================================${NC}"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env file with your configuration and run this script again.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Environment configuration found${NC}"

# Create necessary directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p data logs models templates reports dumps cache
echo -e "${GREEN}✓ Directories created${NC}"

# Build Docker images
echo -e "\n${YELLOW}Building Docker images...${NC}"
docker-compose -f docker/docker-compose.yml build
echo -e "${GREEN}✓ Images built successfully${NC}"

# Start infrastructure services
echo -e "\n${YELLOW}Starting infrastructure services...${NC}"
docker-compose -f docker/docker-compose.yml up -d postgres mongodb redis kafka zookeeper elasticsearch
echo -e "${GREEN}✓ Infrastructure services started${NC}"

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 30

# Initialize database
echo -e "\n${YELLOW}Initializing platform...${NC}"
docker-compose -f docker/docker-compose.yml run --rm platform python main.py --init
echo -e "${GREEN}✓ Platform initialized${NC}"

# Start application services
echo -e "\n${YELLOW}Starting application services...${NC}"
docker-compose -f docker/docker-compose.yml up -d
echo -e "${GREEN}✓ Application services started${NC}"

# Show status
echo -e "\n${YELLOW}Checking service status...${NC}"
docker-compose -f docker/docker-compose.yml ps

# Show access information
echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo -e "\n${YELLOW}Access Information:${NC}"
echo -e "Deception Engine API: ${GREEN}http://localhost:8000${NC}"
echo -e "Dashboard: ${GREEN}http://localhost:3000${NC}"
echo -e "Grafana: ${GREEN}http://localhost:3001${NC} (admin/admin)"
echo -e "Prometheus: ${GREEN}http://localhost:9090${NC}"
echo -e "Kibana: ${GREEN}http://localhost:5601${NC}"
echo -e "\n${YELLOW}View logs:${NC} docker-compose -f docker/docker-compose.yml logs -f"
echo -e "${YELLOW}Stop services:${NC} docker-compose -f docker/docker-compose.yml down"
echo -e "${YELLOW}Stop and remove data:${NC} docker-compose -f docker/docker-compose.yml down -v"
