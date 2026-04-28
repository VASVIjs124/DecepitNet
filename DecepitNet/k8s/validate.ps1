# Kubernetes Deployment Validation Script for DecepitNet (PowerShell)
# Validates that all resources are properly deployed and healthy

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "DecepitNet Kubernetes Validation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$NAMESPACE = "deceptinet"
$FAILED = 0

function Print-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
    $script:FAILED++
}

function Print-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Yellow
}

# Test namespace exists
Write-Host ""
Print-Info "Testing namespace..."
try {
    $null = kubectl get namespace $NAMESPACE 2>$null
    Print-Success "Namespace '$NAMESPACE' exists"
} catch {
    Print-Error "Namespace '$NAMESPACE' not found"
}

# Test ConfigMap
Write-Host ""
Print-Info "Testing ConfigMap..."
try {
    $null = kubectl get configmap deceptinet-config -n $NAMESPACE 2>$null
    Print-Success "ConfigMap exists"
} catch {
    Print-Error "ConfigMap not found"
}

# Test Secrets
Write-Host ""
Print-Info "Testing Secrets..."
try {
    $null = kubectl get secret deceptinet-secrets -n $NAMESPACE 2>$null
    Print-Success "Secrets exist"
} catch {
    Print-Error "Secrets not found"
}

# Test Deployments
Write-Host ""
Print-Info "Testing Deployments..."
$DEPLOYMENTS = @("postgresql", "redis", "kafka", "zookeeper", "deception-engine", "ml-consumer", "deceptinet-platform")

foreach ($DEPLOYMENT in $DEPLOYMENTS) {
    try {
        $ready = kubectl get deployment -l app=$DEPLOYMENT -n $NAMESPACE -o jsonpath='{.items[0].status.readyReplicas}' 2>$null
        $desired = kubectl get deployment -l app=$DEPLOYMENT -n $NAMESPACE -o jsonpath='{.items[0].status.replicas}' 2>$null
        
        if ($ready -and $desired -and $ready -eq $desired -and $ready -gt 0) {
            Print-Success "$DEPLOYMENT : $ready/$desired replicas ready"
        } else {
            Print-Error "$DEPLOYMENT : Not all replicas ready"
        }
    } catch {
        Print-Error "$DEPLOYMENT : Deployment not found"
    }
}

# Test Services
Write-Host ""
Print-Info "Testing Services..."
$SERVICES = @("postgresql-service", "redis-service", "kafka-service", "zookeeper-service", "deception-engine-service", "deceptinet-dashboard-service")

foreach ($SERVICE in $SERVICES) {
    try {
        $clusterIP = kubectl get service $SERVICE -n $NAMESPACE -o jsonpath='{.spec.clusterIP}' 2>$null
        if ($clusterIP) {
            Print-Success "$SERVICE : $clusterIP"
        } else {
            Print-Error "$SERVICE : No cluster IP"
        }
    } catch {
        Print-Error "$SERVICE : Service not found"
    }
}

# Test PVCs
Write-Host ""
Print-Info "Testing Persistent Volume Claims..."
try {
    $pvcs = kubectl get pvc -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}' 2>$null
    if ($pvcs) {
        $pvcList = $pvcs -split ' '
        foreach ($pvc in $pvcList) {
            $status = kubectl get pvc $pvc -n $NAMESPACE -o jsonpath='{.status.phase}' 2>$null
            if ($status -eq "Bound") {
                Print-Success "$pvc : $status"
            } else {
                Print-Error "$pvc : $status (should be Bound)"
            }
        }
    } else {
        Print-Error "No PVCs found"
    }
} catch {
    Print-Error "Error checking PVCs"
}

# Test HPA
Write-Host ""
Print-Info "Testing Horizontal Pod Autoscalers..."
try {
    $replicas = kubectl get hpa deception-engine-hpa -n $NAMESPACE -o jsonpath='{.status.currentReplicas}' 2>$null
    $min = kubectl get hpa deception-engine-hpa -n $NAMESPACE -o jsonpath='{.spec.minReplicas}' 2>$null
    $max = kubectl get hpa deception-engine-hpa -n $NAMESPACE -o jsonpath='{.spec.maxReplicas}' 2>$null
    Print-Success "deception-engine-hpa: $replicas replicas (min: $min, max: $max)"
} catch {
    Print-Error "deception-engine-hpa not found"
}

try {
    $replicas = kubectl get hpa ml-consumer-hpa -n $NAMESPACE -o jsonpath='{.status.currentReplicas}' 2>$null
    $min = kubectl get hpa ml-consumer-hpa -n $NAMESPACE -o jsonpath='{.spec.minReplicas}' 2>$null
    $max = kubectl get hpa ml-consumer-hpa -n $NAMESPACE -o jsonpath='{.spec.maxReplicas}' 2>$null
    Print-Success "ml-consumer-hpa: $replicas replicas (min: $min, max: $max)"
} catch {
    Print-Error "ml-consumer-hpa not found"
}

# Test Network Policies
Write-Host ""
Print-Info "Testing Network Policies..."
try {
    $npCount = (kubectl get networkpolicy -n $NAMESPACE --no-headers 2>$null | Measure-Object).Count
    if ($npCount -gt 0) {
        Print-Success "Found $npCount network policies"
    } else {
        Print-Error "No network policies found"
    }
} catch {
    Print-Error "Error checking network policies"
}

# Test Pod Health
Write-Host ""
Print-Info "Testing Pod Health..."
try {
    $pods = kubectl get pods -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}' 2>$null
    $running = 0
    $notReady = 0
    
    if ($pods) {
        $podList = $pods -split ' '
        foreach ($pod in $podList) {
            $status = kubectl get pod $pod -n $NAMESPACE -o jsonpath='{.status.phase}' 2>$null
            $ready = kubectl get pod $pod -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>$null
            
            if ($status -eq "Running" -and $ready -eq "True") {
                $running++
            } else {
                $notReady++
                Print-Error "$pod : $status (Ready: $ready)"
            }
        }
    }
    
    Print-Success "$running pods running and ready"
    if ($notReady -gt 0) {
        Print-Error "$notReady pods not ready"
    }
} catch {
    Print-Error "Error checking pod health"
}

# Test resource usage
Write-Host ""
Print-Info "Testing Resource Usage..."
try {
    $null = kubectl top nodes 2>$null
    Print-Success "Metrics server is available"
    
    Write-Host ""
    Write-Host "Node Resource Usage:"
    kubectl top nodes
    
    Write-Host ""
    Write-Host "Pod Resource Usage:"
    kubectl top pods -n $NAMESPACE
} catch {
    Print-Error "Metrics server not available (HPA may not work)"
}

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if ($FAILED -eq 0) {
    Print-Success "All validation tests passed! ✓"
    Write-Host ""
    Print-Info "Deployment is healthy and ready for production"
    exit 0
} else {
    Print-Error "$FAILED validation test(s) failed"
    Write-Host ""
    Print-Info "Please review errors above and fix issues"
    exit 1
}
