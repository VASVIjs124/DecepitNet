#!/bin/bash

# Kubernetes Deployment Validation Script for DecepitNet
# Validates that all resources are properly deployed and healthy

set -e

echo "=========================================="
echo "DecepitNet Kubernetes Validation"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

NAMESPACE="deceptinet"
FAILED=0

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    FAILED=$((FAILED + 1))
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Test namespace exists
echo ""
print_info "Testing namespace..."
if kubectl get namespace $NAMESPACE &> /dev/null; then
    print_success "Namespace '$NAMESPACE' exists"
else
    print_error "Namespace '$NAMESPACE' not found"
fi

# Test ConfigMap
echo ""
print_info "Testing ConfigMap..."
if kubectl get configmap deceptinet-config -n $NAMESPACE &> /dev/null; then
    print_success "ConfigMap exists"
    CONFIG_COUNT=$(kubectl get configmap deceptinet-config -n $NAMESPACE -o jsonpath='{.data}' | jq 'keys | length')
    print_info "  Found $CONFIG_COUNT configuration entries"
else
    print_error "ConfigMap not found"
fi

# Test Secrets
echo ""
print_info "Testing Secrets..."
if kubectl get secret deceptinet-secrets -n $NAMESPACE &> /dev/null; then
    print_success "Secrets exist"
    SECRET_COUNT=$(kubectl get secret deceptinet-secrets -n $NAMESPACE -o jsonpath='{.data}' | jq 'keys | length')
    print_info "  Found $SECRET_COUNT secret entries"
else
    print_error "Secrets not found"
fi

# Test Deployments
echo ""
print_info "Testing Deployments..."
DEPLOYMENTS=("postgresql" "redis" "kafka" "zookeeper" "deception-engine" "ml-consumer" "deceptinet-platform")

for DEPLOYMENT in "${DEPLOYMENTS[@]}"; do
    if kubectl get deployment $DEPLOYMENT -n $NAMESPACE &> /dev/null 2>&1 || kubectl get deployment | grep -q $DEPLOYMENT; then
        READY=$(kubectl get deployment -l app=$DEPLOYMENT -n $NAMESPACE -o jsonpath='{.items[0].status.readyReplicas}' 2>/dev/null || echo "0")
        DESIRED=$(kubectl get deployment -l app=$DEPLOYMENT -n $NAMESPACE -o jsonpath='{.items[0].status.replicas}' 2>/dev/null || echo "0")
        
        if [ "$READY" -eq "$DESIRED" ] && [ "$READY" -gt "0" ]; then
            print_success "$DEPLOYMENT: $READY/$DESIRED replicas ready"
        else
            print_error "$DEPLOYMENT: $READY/$DESIRED replicas ready (not all ready)"
        fi
    else
        print_error "$DEPLOYMENT: Deployment not found"
    fi
done

# Test Services
echo ""
print_info "Testing Services..."
SERVICES=("postgresql-service" "redis-service" "kafka-service" "zookeeper-service" "deception-engine-service" "deceptinet-dashboard-service")

for SERVICE in "${SERVICES[@]}"; do
    if kubectl get service $SERVICE -n $NAMESPACE &> /dev/null; then
        CLUSTER_IP=$(kubectl get service $SERVICE -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
        print_success "$SERVICE: $CLUSTER_IP"
    else
        print_error "$SERVICE: Service not found"
    fi
done

# Test PVCs
echo ""
print_info "Testing Persistent Volume Claims..."
PVCS=$(kubectl get pvc -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}')

if [ -n "$PVCS" ]; then
    for PVC in $PVCS; do
        STATUS=$(kubectl get pvc $PVC -n $NAMESPACE -o jsonpath='{.status.phase}')
        if [ "$STATUS" == "Bound" ]; then
            print_success "$PVC: $STATUS"
        else
            print_error "$PVC: $STATUS (should be Bound)"
        fi
    done
else
    print_error "No PVCs found"
fi

# Test HPA
echo ""
print_info "Testing Horizontal Pod Autoscalers..."
if kubectl get hpa deception-engine-hpa -n $NAMESPACE &> /dev/null; then
    REPLICAS=$(kubectl get hpa deception-engine-hpa -n $NAMESPACE -o jsonpath='{.status.currentReplicas}')
    MIN=$(kubectl get hpa deception-engine-hpa -n $NAMESPACE -o jsonpath='{.spec.minReplicas}')
    MAX=$(kubectl get hpa deception-engine-hpa -n $NAMESPACE -o jsonpath='{.spec.maxReplicas}')
    print_success "deception-engine-hpa: $REPLICAS replicas (min: $MIN, max: $MAX)"
else
    print_error "deception-engine-hpa not found"
fi

if kubectl get hpa ml-consumer-hpa -n $NAMESPACE &> /dev/null; then
    REPLICAS=$(kubectl get hpa ml-consumer-hpa -n $NAMESPACE -o jsonpath='{.status.currentReplicas}')
    MIN=$(kubectl get hpa ml-consumer-hpa -n $NAMESPACE -o jsonpath='{.spec.minReplicas}')
    MAX=$(kubectl get hpa ml-consumer-hpa -n $NAMESPACE -o jsonpath='{.spec.maxReplicas}')
    print_success "ml-consumer-hpa: $REPLICAS replicas (min: $MIN, max: $MAX)"
else
    print_error "ml-consumer-hpa not found"
fi

# Test Network Policies
echo ""
print_info "Testing Network Policies..."
NP_COUNT=$(kubectl get networkpolicy -n $NAMESPACE --no-headers 2>/dev/null | wc -l)
if [ "$NP_COUNT" -gt "0" ]; then
    print_success "Found $NP_COUNT network policies"
else
    print_error "No network policies found"
fi

# Test Pod Health
echo ""
print_info "Testing Pod Health..."
PODS=$(kubectl get pods -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}')

RUNNING=0
NOT_READY=0

for POD in $PODS; do
    STATUS=$(kubectl get pod $POD -n $NAMESPACE -o jsonpath='{.status.phase}')
    READY=$(kubectl get pod $POD -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
    
    if [ "$STATUS" == "Running" ] && [ "$READY" == "True" ]; then
        RUNNING=$((RUNNING + 1))
    else
        NOT_READY=$((NOT_READY + 1))
        print_error "$POD: $STATUS (Ready: $READY)"
    fi
done

print_success "$RUNNING pods running and ready"
if [ "$NOT_READY" -gt "0" ]; then
    print_error "$NOT_READY pods not ready"
fi

# Test API Endpoints (if accessible)
echo ""
print_info "Testing API Endpoints..."

# Try to access deception engine health endpoint
API_POD=$(kubectl get pods -n $NAMESPACE -l app=deception-engine -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$API_POD" ]; then
    if kubectl exec $API_POD -n $NAMESPACE -- curl -s -f http://localhost:8000/health &> /dev/null; then
        print_success "Deception Engine health endpoint responding"
    else
        print_error "Deception Engine health endpoint not responding"
    fi
fi

# Test resource usage
echo ""
print_info "Testing Resource Usage..."
if kubectl top nodes &> /dev/null; then
    print_success "Metrics server is available"
    
    echo ""
    echo "Node Resource Usage:"
    kubectl top nodes
    
    echo ""
    echo "Pod Resource Usage:"
    kubectl top pods -n $NAMESPACE
else
    print_error "Metrics server not available (HPA may not work)"
fi

# Summary
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="

if [ "$FAILED" -eq "0" ]; then
    print_success "All validation tests passed! ✓"
    echo ""
    print_info "Deployment is healthy and ready for production"
    exit 0
else
    print_error "$FAILED validation test(s) failed"
    echo ""
    print_info "Please review errors above and fix issues"
    exit 1
fi
