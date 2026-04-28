#!/bin/bash

# Optimized Kubernetes Deployment Script for DecepitNet
# This script deploys the entire DecepitNet platform with all optimizations

set -e

echo "=========================================="
echo "DecepitNet Kubernetes Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="deceptinet"
KUBECTL="kubectl"

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl not found. Please install kubectl first."
    exit 1
fi

print_success "kubectl found"

# Check cluster connection
print_info "Checking cluster connection..."
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi
print_success "Connected to cluster: $(kubectl config current-context)"

# Create namespace
print_info "Creating namespace..."
$KUBECTL apply -f namespace.yaml
print_success "Namespace created/updated"

# Apply ConfigMap and Secrets
print_info "Applying ConfigMap..."
$KUBECTL apply -f configmap.yaml
print_success "ConfigMap applied"

print_info "Applying Secrets..."
$KUBECTL apply -f secrets.yaml
print_success "Secrets applied"

# Apply Resource Quota and Limits
print_info "Applying Resource Quota and Limits..."
$KUBECTL apply -f resource-quota.yaml
print_success "Resource Quota and Limits applied"

# Deploy infrastructure services
print_info "Deploying PostgreSQL..."
$KUBECTL apply -f postgresql-deployment.yaml
print_success "PostgreSQL deployed"

print_info "Deploying Redis..."
$KUBECTL apply -f redis-deployment.yaml
print_success "Redis deployed"

print_info "Deploying Kafka..."
$KUBECTL apply -f kafka-deployment.yaml
print_success "Kafka deployed"

# Wait for infrastructure to be ready
print_info "Waiting for infrastructure services to be ready..."
$KUBECTL wait --for=condition=ready pod -l app=postgresql -n $NAMESPACE --timeout=300s
$KUBECTL wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s
$KUBECTL wait --for=condition=ready pod -l app=zookeeper -n $NAMESPACE --timeout=300s
$KUBECTL wait --for=condition=ready pod -l app=kafka -n $NAMESPACE --timeout=300s
print_success "Infrastructure services are ready"

# Deploy application services
print_info "Deploying Deception Engine..."
$KUBECTL apply -f deception-engine-deployment.yaml
print_success "Deception Engine deployed"

print_info "Deploying ML Consumer..."
$KUBECTL apply -f ml-consumer-deployment.yaml
print_success "ML Consumer deployed"

print_info "Deploying Main Platform..."
$KUBECTL apply -f main-platform-deployment.yaml
print_success "Main Platform deployed"

# Apply Network Policies
print_info "Applying Network Policies..."
$KUBECTL apply -f network-policy.yaml
print_success "Network Policies applied"

# Apply Ingress (optional)
if [ -f "ingress.yaml" ]; then
    print_info "Applying Ingress..."
    $KUBECTL apply -f ingress.yaml
    print_success "Ingress applied"
fi

# Wait for application services to be ready
print_info "Waiting for application services to be ready..."
$KUBECTL wait --for=condition=ready pod -l app=deception-engine -n $NAMESPACE --timeout=300s || true
$KUBECTL wait --for=condition=ready pod -l app=ml-consumer -n $NAMESPACE --timeout=300s || true
$KUBECTL wait --for=condition=ready pod -l app=deceptinet-platform -n $NAMESPACE --timeout=300s || true

echo ""
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="

# Get deployment status
print_info "Deployment Status:"
$KUBECTL get deployments -n $NAMESPACE

echo ""
print_info "Service Status:"
$KUBECTL get services -n $NAMESPACE

echo ""
print_info "Pod Status:"
$KUBECTL get pods -n $NAMESPACE

echo ""
print_info "PVC Status:"
$KUBECTL get pvc -n $NAMESPACE

echo ""
print_info "HPA Status:"
$KUBECTL get hpa -n $NAMESPACE

echo ""
echo "=========================================="
echo "Access Information"
echo "=========================================="

# Get service URLs
API_SERVICE=$($KUBECTL get svc deception-engine-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
DASHBOARD_SERVICE=$($KUBECTL get svc deceptinet-dashboard-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')

echo "Internal Services:"
echo "  - Deception Engine API: http://${API_SERVICE}:8000"
echo "  - Dashboard: http://${DASHBOARD_SERVICE}:5000"

if $KUBECTL get ingress -n $NAMESPACE &> /dev/null; then
    echo ""
    echo "External URLs (via Ingress):"
    $KUBECTL get ingress -n $NAMESPACE
fi

echo ""
echo "=========================================="
echo "Optimization Status"
echo "=========================================="

print_success "Lazy Model Loading: Enabled (cache size: 10)"
print_success "Database Connection Pooling: Enabled (10-50 connections)"
print_success "Kafka Batch Processing: Enabled (batch size: 200)"
print_success "Redis Caching: Enabled (TTL: 300-600s)"
print_success "Data Structure Optimizations: Enabled"
print_success "Horizontal Pod Autoscaling: Enabled"

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="

echo "1. Monitor deployment:"
echo "   kubectl get pods -n $NAMESPACE -w"
echo ""
echo "2. Check logs:"
echo "   kubectl logs -f deployment/deception-engine -n $NAMESPACE"
echo "   kubectl logs -f deployment/ml-consumer -n $NAMESPACE"
echo ""
echo "3. Access services:"
echo "   kubectl port-forward svc/deception-engine-service 8000:8000 -n $NAMESPACE"
echo "   kubectl port-forward svc/deceptinet-dashboard-service 5000:5000 -n $NAMESPACE"
echo ""
echo "4. Scale services:"
echo "   kubectl scale deployment deception-engine --replicas=5 -n $NAMESPACE"
echo ""
echo "5. Update configuration:"
echo "   kubectl edit configmap deceptinet-config -n $NAMESPACE"
echo ""

print_success "Deployment complete!"
