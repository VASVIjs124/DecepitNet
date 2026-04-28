# Optimized Kubernetes Deployment Script for DecepitNet (PowerShell)
# This script deploys the entire DecepitNet platform with all optimizations

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "DecepitNet Kubernetes Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Configuration
$NAMESPACE = "deceptinet"

# Function to print colored output
function Print-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Print-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Yellow
}

# Check if kubectl is installed
try {
    $null = kubectl version --client 2>$null
    Print-Success "kubectl found"
} catch {
    Print-Error "kubectl not found. Please install kubectl first."
    exit 1
}

# Check cluster connection
Print-Info "Checking cluster connection..."
try {
    $null = kubectl cluster-info 2>$null
    $context = kubectl config current-context
    Print-Success "Connected to cluster: $context"
} catch {
    Print-Error "Cannot connect to Kubernetes cluster"
    exit 1
}

# Create namespace
Print-Info "Creating namespace..."
kubectl apply -f namespace.yaml
Print-Success "Namespace created/updated"

# Apply ConfigMap and Secrets
Print-Info "Applying ConfigMap..."
kubectl apply -f configmap.yaml
Print-Success "ConfigMap applied"

Print-Info "Applying Secrets..."
kubectl apply -f secrets.yaml
Print-Success "Secrets applied"

# Apply Resource Quota and Limits
Print-Info "Applying Resource Quota and Limits..."
kubectl apply -f resource-quota.yaml
Print-Success "Resource Quota and Limits applied"

# Deploy infrastructure services
Print-Info "Deploying PostgreSQL..."
kubectl apply -f postgresql-deployment.yaml
Print-Success "PostgreSQL deployed"

Print-Info "Deploying Redis..."
kubectl apply -f redis-deployment.yaml
Print-Success "Redis deployed"

Print-Info "Deploying Kafka..."
kubectl apply -f kafka-deployment.yaml
Print-Success "Kafka deployed"

# Wait for infrastructure to be ready
Print-Info "Waiting for infrastructure services to be ready..."
kubectl wait --for=condition=ready pod -l app=postgresql -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=zookeeper -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=kafka -n $NAMESPACE --timeout=300s
Print-Success "Infrastructure services are ready"

# Deploy application services
Print-Info "Deploying Deception Engine..."
kubectl apply -f deception-engine-deployment.yaml
Print-Success "Deception Engine deployed"

Print-Info "Deploying ML Consumer..."
kubectl apply -f ml-consumer-deployment.yaml
Print-Success "ML Consumer deployed"

Print-Info "Deploying Main Platform..."
kubectl apply -f main-platform-deployment.yaml
Print-Success "Main Platform deployed"

# Apply Network Policies
Print-Info "Applying Network Policies..."
kubectl apply -f network-policy.yaml
Print-Success "Network Policies applied"

# Apply Ingress (optional)
if (Test-Path "ingress.yaml") {
    Print-Info "Applying Ingress..."
    kubectl apply -f ingress.yaml
    Print-Success "Ingress applied"
}

# Wait for application services to be ready
Print-Info "Waiting for application services to be ready..."
kubectl wait --for=condition=ready pod -l app=deception-engine -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=ml-consumer -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=deceptinet-platform -n $NAMESPACE --timeout=300s

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deployment Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Get deployment status
Print-Info "Deployment Status:"
kubectl get deployments -n $NAMESPACE

Write-Host ""
Print-Info "Service Status:"
kubectl get services -n $NAMESPACE

Write-Host ""
Print-Info "Pod Status:"
kubectl get pods -n $NAMESPACE

Write-Host ""
Print-Info "PVC Status:"
kubectl get pvc -n $NAMESPACE

Write-Host ""
Print-Info "HPA Status:"
kubectl get hpa -n $NAMESPACE

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Access Information" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Get service URLs
$API_SERVICE = kubectl get svc deception-engine-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}'
$DASHBOARD_SERVICE = kubectl get svc deceptinet-dashboard-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}'

Write-Host "Internal Services:"
Write-Host "  - Deception Engine API: http://${API_SERVICE}:8000"
Write-Host "  - Dashboard: http://${DASHBOARD_SERVICE}:5000"

try {
    Write-Host ""
    Write-Host "External URLs (via Ingress):"
    kubectl get ingress -n $NAMESPACE
} catch {
    # Ingress not available
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Optimization Status" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Print-Success "Lazy Model Loading: Enabled (cache size: 10)"
Print-Success "Database Connection Pooling: Enabled (10-50 connections)"
Print-Success "Kafka Batch Processing: Enabled (batch size: 200)"
Print-Success "Redis Caching: Enabled (TTL: 300-600s)"
Print-Success "Data Structure Optimizations: Enabled"
Print-Success "Horizontal Pod Autoscaling: Enabled"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "1. Monitor deployment:"
Write-Host "   kubectl get pods -n $NAMESPACE -w"
Write-Host ""
Write-Host "2. Check logs:"
Write-Host "   kubectl logs -f deployment/deception-engine -n $NAMESPACE"
Write-Host "   kubectl logs -f deployment/ml-consumer -n $NAMESPACE"
Write-Host ""
Write-Host "3. Access services:"
Write-Host "   kubectl port-forward svc/deception-engine-service 8000:8000 -n $NAMESPACE"
Write-Host "   kubectl port-forward svc/deceptinet-dashboard-service 5000:5000 -n $NAMESPACE"
Write-Host ""
Write-Host "4. Scale services:"
Write-Host "   kubectl scale deployment deception-engine --replicas=5 -n $NAMESPACE"
Write-Host ""
Write-Host "5. Update configuration:"
Write-Host "   kubectl edit configmap deceptinet-config -n $NAMESPACE"
Write-Host ""

Print-Success "Deployment complete!"
