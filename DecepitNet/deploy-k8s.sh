#!/usr/bin/env bash
# DECEPTINET Kubernetes Deployment Script
# Deploys the platform to Kubernetes cluster

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
NAMESPACE="${NAMESPACE:-deceptinet}"
ENVIRONMENT="${ENVIRONMENT:-production}"

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}DECEPTINET Kubernetes Deployment${NC}"
echo -e "${GREEN}Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}Namespace: ${NAMESPACE}${NC}"
echo -e "${GREEN}=====================================${NC}"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ kubectl found${NC}"

# Check cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Connected to Kubernetes cluster${NC}"

# Create namespace if it doesn't exist
echo -e "\n${YELLOW}Setting up namespace...${NC}"
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ Namespace configured${NC}"

# Apply security policies
echo -e "\n${YELLOW}Applying security policies...${NC}"
kubectl apply -f security/rbac.yaml -n ${NAMESPACE}
kubectl apply -f security/network-policies.yaml -n ${NAMESPACE}
if kubectl api-versions | grep -q policy/v1beta1; then
    kubectl apply -f security/psp.yaml
    echo -e "${GREEN}✓ Pod Security Policies applied${NC}"
else
    echo -e "${YELLOW}! Pod Security Policies not available in this cluster${NC}"
fi

# Create secrets from .env
echo -e "\n${YELLOW}Creating secrets...${NC}"
if [ -f .env ]; then
    kubectl create secret generic deceptinet-config \
        --from-env-file=.env \
        -n ${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
    echo -e "${GREEN}✓ Secrets created${NC}"
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Deploy infrastructure components
echo -e "\n${YELLOW}Deploying infrastructure...${NC}"
kubectl apply -f deployments/kubernetes/ -n ${NAMESPACE}
echo -e "${GREEN}✓ Infrastructure deployed${NC}"

# Wait for infrastructure to be ready
echo -e "\n${YELLOW}Waiting for infrastructure to be ready...${NC}"
kubectl wait --for=condition=ready pod \
    -l app=postgres \
    -n ${NAMESPACE} \
    --timeout=300s
kubectl wait --for=condition=ready pod \
    -l app=kafka \
    -n ${NAMESPACE} \
    --timeout=300s
kubectl wait --for=condition=ready pod \
    -l app=elasticsearch \
    -n ${NAMESPACE} \
    --timeout=300s
echo -e "${GREEN}✓ Infrastructure ready${NC}"

# Initialize database
echo -e "\n${YELLOW}Initializing platform...${NC}"
kubectl run deceptinet-init \
    --image=ghcr.io/your-org/deceptinet:latest \
    --restart=Never \
    --rm -i \
    -n ${NAMESPACE} \
    --command -- python main.py --init || true
echo -e "${GREEN}✓ Platform initialized${NC}"

# Deploy application components
echo -e "\n${YELLOW}Deploying application...${NC}"
kubectl apply -f deployments/kubernetes/deceptinet-deployment.yaml -n ${NAMESPACE}
echo -e "${GREEN}✓ Application deployed${NC}"

# Wait for application to be ready
echo -e "\n${YELLOW}Waiting for application to be ready...${NC}"
kubectl wait --for=condition=ready pod \
    -l app=deceptinet \
    -n ${NAMESPACE} \
    --timeout=300s
echo -e "${GREEN}✓ Application ready${NC}"

# Show deployment status
echo -e "\n${YELLOW}Deployment status:${NC}"
kubectl get all -n ${NAMESPACE}

# Get service endpoints
echo -e "\n${YELLOW}Service endpoints:${NC}"
kubectl get svc -n ${NAMESPACE}

# Get ingress
if kubectl get ingress -n ${NAMESPACE} &> /dev/null; then
    echo -e "\n${YELLOW}Ingress:${NC}"
    kubectl get ingress -n ${NAMESPACE}
fi

echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo -e "\n${YELLOW}Useful commands:${NC}"
echo -e "View logs: ${GREEN}kubectl logs -f -l app=deceptinet -n ${NAMESPACE}${NC}"
echo -e "View pods: ${GREEN}kubectl get pods -n ${NAMESPACE}${NC}"
echo -e "Describe deployment: ${GREEN}kubectl describe deployment deceptinet -n ${NAMESPACE}${NC}"
echo -e "Port forward API: ${GREEN}kubectl port-forward svc/deceptinet-api 8000:8000 -n ${NAMESPACE}${NC}"
echo -e "Port forward Dashboard: ${GREEN}kubectl port-forward svc/deceptinet-dashboard 3000:3000 -n ${NAMESPACE}${NC}"
