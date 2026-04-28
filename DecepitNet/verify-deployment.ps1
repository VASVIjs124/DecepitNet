# DECEPTINET Deployment Verification Script (PowerShell)
# Runs smoke tests to verify deployment success

$ErrorActionPreference = "Stop"

# Configuration
$API_URL = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8000" }
$DASHBOARD_URL = if ($env:DASHBOARD_URL) { $env:DASHBOARD_URL } else { "http://localhost:3000" }
$MAX_RETRIES = 30
$RETRY_INTERVAL = 10

Write-Host "=====================================" -ForegroundColor Green
Write-Host "DECEPTINET Deployment Verification" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Function to check endpoint
function Test-Endpoint {
    param(
        [string]$Url,
        [string]$Name
    )
    
    Write-Host "`nChecking $Name..." -ForegroundColor Yellow
    
    $retries = 0
    while ($retries -lt $MAX_RETRIES) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "✓ $Name is responding" -ForegroundColor Green
                return $true
            }
        }
        catch {
            $retries++
            Write-Host "Attempt $retries/$MAX_RETRIES - waiting ${RETRY_INTERVAL}s..." -ForegroundColor Yellow
            Start-Sleep -Seconds $RETRY_INTERVAL
        }
    }
    
    Write-Host "✗ $Name failed to respond" -ForegroundColor Red
    return $false
}

# Function to check health endpoint
function Test-Health {
    param(
        [string]$Url,
        [string]$Name
    )
    
    Write-Host "`nChecking $Name health..." -ForegroundColor Yellow
    
    try {
        $response = Invoke-RestMethod -Uri $Url -Method Get
        $status = $response.status
        
        if ($status -in @("alive", "healthy", "ready")) {
            Write-Host "✓ $Name health check passed" -ForegroundColor Green
            $response | ConvertTo-Json -Depth 3
            return $true
        }
        else {
            Write-Host "✗ $Name health check failed" -ForegroundColor Red
            $response | ConvertTo-Json -Depth 3
            return $false
        }
    }
    catch {
        Write-Host "✗ $Name health check failed: $_" -ForegroundColor Red
        return $false
    }
}

# Check infrastructure services
Write-Host "`n=== Checking Infrastructure Services ===" -ForegroundColor Yellow

# Check API root
Test-Endpoint -Url "$API_URL/" -Name "Deception Engine Root"

# Check API health
Test-Health -Url "$API_URL/health" -Name "Deception Engine"

# Check API readiness
Test-Health -Url "$API_URL/ready" -Name "Deception Engine Readiness"

# Check API detailed health
Test-Health -Url "$API_URL/api/health" -Name "Deception Engine (detailed)"

# Test API functionality
Write-Host "`n=== Testing API Functionality ===" -ForegroundColor Yellow

# List honeypots
Write-Host "`nListing honeypots..." -ForegroundColor Yellow
try {
    $honeypots = Invoke-RestMethod -Uri "$API_URL/api/honeypots" -Method Get
    Write-Host "✓ Honeypots endpoint working" -ForegroundColor Green
    $honeypots | ConvertTo-Json -Depth 3
}
catch {
    Write-Host "✗ Failed to list honeypots: $_" -ForegroundColor Red
}

# List strategies
Write-Host "`nListing deception strategies..." -ForegroundColor Yellow
try {
    $strategies = Invoke-RestMethod -Uri "$API_URL/api/strategies" -Method Get
    Write-Host "✓ Strategies endpoint working" -ForegroundColor Green
    Write-Host "Found $($strategies.Count) strategies"
}
catch {
    Write-Host "✗ Failed to list strategies: $_" -ForegroundColor Red
}

# Check metrics
Write-Host "`nChecking metrics..." -ForegroundColor Yellow
try {
    $metrics = Invoke-RestMethod -Uri "$API_URL/api/metrics" -Method Get
    Write-Host "✓ Metrics endpoint working" -ForegroundColor Green
    $metrics | ConvertTo-Json -Depth 3
}
catch {
    Write-Host "✗ Failed to get metrics: $_" -ForegroundColor Red
}

# Check dashboard (if available)
if ($DASHBOARD_URL) {
    Write-Host "`n=== Checking Dashboard ===" -ForegroundColor Yellow
    Test-Endpoint -Url $DASHBOARD_URL -Name "React Dashboard"
}

# Summary
Write-Host "`n=====================================" -ForegroundColor Green
Write-Host "Verification Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

Write-Host "`nAPI Endpoints:" -ForegroundColor Yellow
Write-Host "Root: " -NoNewline; Write-Host "$API_URL/" -ForegroundColor Green
Write-Host "Health: " -NoNewline; Write-Host "$API_URL/health" -ForegroundColor Green
Write-Host "Ready: " -NoNewline; Write-Host "$API_URL/ready" -ForegroundColor Green
Write-Host "Docs: " -NoNewline; Write-Host "$API_URL/api/docs" -ForegroundColor Green
Write-Host "Honeypots: " -NoNewline; Write-Host "$API_URL/api/honeypots" -ForegroundColor Green
Write-Host "Strategies: " -NoNewline; Write-Host "$API_URL/api/strategies" -ForegroundColor Green
Write-Host "Metrics: " -NoNewline; Write-Host "$API_URL/api/metrics" -ForegroundColor Green

if ($DASHBOARD_URL) {
    Write-Host "`nDashboard:" -ForegroundColor Yellow
    Write-Host "URL: " -NoNewline; Write-Host "$DASHBOARD_URL" -ForegroundColor Green
}

Write-Host "`nDeployment verification successful!" -ForegroundColor Green
