# DECEPTINET Local Deployment Script (PowerShell)
# Deploys the platform using Docker Compose

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Green
Write-Host "DECEPTINET Local Deployment" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Check prerequisites
Write-Host "`nChecking prerequisites..." -ForegroundColor Yellow

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker is not installed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker found" -ForegroundColor Green

# Check Docker Compose
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker Compose is not installed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker Compose found" -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "Warning: .env file not found. Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "Please edit .env file with your configuration and run this script again." -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Environment configuration found" -ForegroundColor Green

# Create necessary directories
Write-Host "`nCreating directories..." -ForegroundColor Yellow
$directories = @("data", "logs", "models", "templates", "reports", "dumps", "cache")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}
Write-Host "✓ Directories created" -ForegroundColor Green

# Build Docker images
Write-Host "`nBuilding Docker images..." -ForegroundColor Yellow
docker-compose -f docker/docker-compose.yml build
Write-Host "✓ Images built successfully" -ForegroundColor Green

# Start infrastructure services
Write-Host "`nStarting infrastructure services..." -ForegroundColor Yellow
docker-compose -f docker/docker-compose.yml up -d postgres mongodb redis kafka zookeeper elasticsearch
Write-Host "✓ Infrastructure services started" -ForegroundColor Green

# Wait for services to be ready
Write-Host "`nWaiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Initialize database
Write-Host "`nInitializing platform..." -ForegroundColor Yellow
docker-compose -f docker/docker-compose.yml run --rm platform python main.py --init
Write-Host "✓ Platform initialized" -ForegroundColor Green

# Start application services
Write-Host "`nStarting application services..." -ForegroundColor Yellow
docker-compose -f docker/docker-compose.yml up -d
Write-Host "✓ Application services started" -ForegroundColor Green

# Show status
Write-Host "`nChecking service status..." -ForegroundColor Yellow
docker-compose -f docker/docker-compose.yml ps

# Show access information
Write-Host "`n=====================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host "`nAccess Information:" -ForegroundColor Yellow
Write-Host "Deception Engine API: " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Green
Write-Host "Dashboard: " -NoNewline; Write-Host "http://localhost:3000" -ForegroundColor Green
Write-Host "Grafana: " -NoNewline; Write-Host "http://localhost:3001" -ForegroundColor Green -NoNewline; Write-Host " (admin/admin)"
Write-Host "Prometheus: " -NoNewline; Write-Host "http://localhost:9090" -ForegroundColor Green
Write-Host "Kibana: " -NoNewline; Write-Host "http://localhost:5601" -ForegroundColor Green
Write-Host "`nView logs: " -NoNewline; Write-Host "docker-compose -f docker/docker-compose.yml logs -f" -ForegroundColor Yellow
Write-Host "Stop services: " -NoNewline; Write-Host "docker-compose -f docker/docker-compose.yml down" -ForegroundColor Yellow
Write-Host "Stop and remove data: " -NoNewline; Write-Host "docker-compose -f docker/docker-compose.yml down -v" -ForegroundColor Yellow
