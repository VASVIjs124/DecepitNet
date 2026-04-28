# DECEPTINET Deployment Guide

## 🚀 Complete Deployment Instructions

This guide provides step-by-step instructions for deploying DECEPTINET in various environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Local)](#quick-start-local)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Production Deployment](#production-deployment)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Python 3.10+** - Application runtime
- **Docker 20.10+** - Containerization
- **Docker Compose 2.0+** - Local orchestration
- **kubectl 1.28+** - Kubernetes CLI (for K8s deployment)
- **Node.js 18+** - React dashboard (optional)

### Recommended Resources

**Minimum (Development/Testing):**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB

**Production:**
- CPU: 16 cores
- RAM: 32 GB
- Storage: 500 GB SSD
- Network: 1 Gbps

---

## Quick Start (Local)

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/deceptinet.git
cd deceptinet

# Create environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your favorite editor
```

### 2. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# React dashboard (optional)
cd dashboards/react
npm install
cd ../..
```

### 3. Initialize Platform

```bash
python main.py --init
```

### 4. Run Locally

```bash
# Full platform
python main.py --mode full --dashboard

# Or specific modes
python main.py --mode honeypot    # Honeypots only
python main.py --mode redteam     # Red team simulation
python main.py --mode analysis    # Analysis only
```

### 5. Access Services

- **Deception Engine API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Dashboard**: http://localhost:3000

---

## Docker Deployment

### Using PowerShell (Windows)

```powershell
# Deploy
.\deploy-local.ps1

# Verify
.\verify-deployment.ps1

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop
docker-compose -f docker/docker-compose.yml down
```

### Using Bash (Linux/Mac)

```bash
# Make scripts executable
chmod +x deploy-local.sh verify-deployment.sh

# Deploy
./deploy-local.sh

# Verify
./verify-deployment.sh

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop
docker-compose -f docker/docker-compose.yml down
```

### Manual Docker Compose

```bash
# Start infrastructure only
docker-compose -f docker/docker-compose.yml up -d postgres mongodb redis kafka elasticsearch

# Wait for services (30-60 seconds)
sleep 60

# Initialize
docker-compose -f docker/docker-compose.yml run --rm platform python main.py --init

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose -f docker/docker-compose.yml ps
```

---

## Kubernetes Deployment

### Prerequisites

1. **Kubernetes cluster** (1.28+)
2. **kubectl** configured
3. **Container registry** access (GHCR, Docker Hub, ACR, etc.)

### 1. Build and Push Images

```bash
# Set your registry
export DOCKER_REGISTRY=ghcr.io/your-org
export IMAGE_TAG=v1.0.0

# Build images
docker build -t ${DOCKER_REGISTRY}/deceptinet:${IMAGE_TAG} -f Dockerfile .
docker build -t ${DOCKER_REGISTRY}/deceptinet-deception:${IMAGE_TAG} -f Dockerfile.deception .
docker build -t ${DOCKER_REGISTRY}/deceptinet-ml:${IMAGE_TAG} -f Dockerfile.ml .

# Push images
docker push ${DOCKER_REGISTRY}/deceptinet:${IMAGE_TAG}
docker push ${DOCKER_REGISTRY}/deceptinet-deception:${IMAGE_TAG}
docker push ${DOCKER_REGISTRY}/deceptinet-ml:${IMAGE_TAG}
```

### 2. Configure Environment

```bash
# Update image references in deployments
sed -i "s|ghcr.io/your-org|${DOCKER_REGISTRY}|g" deployments/kubernetes/*.yaml
sed -i "s|latest|${IMAGE_TAG}|g" deployments/kubernetes/*.yaml
```

### 3. Deploy to Kubernetes

```bash
# Using deployment script
export NAMESPACE=deceptinet
export ENVIRONMENT=production
./deploy-k8s.sh

# Or manually
kubectl create namespace deceptinet
kubectl create secret generic deceptinet-config --from-env-file=.env -n deceptinet
kubectl apply -f security/ -n deceptinet
kubectl apply -f deployments/kubernetes/ -n deceptinet
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n deceptinet

# Check services
kubectl get svc -n deceptinet

# Check logs
kubectl logs -f deployment/deceptinet-deception -n deceptinet

# Port forward for testing
kubectl port-forward svc/deceptinet-api 8000:8000 -n deceptinet
```

### 5. Access Services

```bash
# Get service URLs
kubectl get ingress -n deceptinet

# Or use port forwarding
kubectl port-forward svc/deceptinet-api 8000:8000 -n deceptinet &
kubectl port-forward svc/deceptinet-dashboard 3000:3000 -n deceptinet &
```

---

## Production Deployment

### AWS EKS Deployment

```bash
# 1. Create EKS cluster
eksctl create cluster \
  --name deceptinet-prod \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.2xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10

# 2. Configure kubectl
aws eks update-kubeconfig --region us-east-1 --name deceptinet-prod

# 3. Deploy using script
export NAMESPACE=deceptinet
export ENVIRONMENT=production
./deploy-k8s.sh

# 4. Configure ingress with ALB
kubectl apply -f deployments/kubernetes/ingress-aws.yaml
```

### Azure AKS Deployment

```bash
# 1. Create AKS cluster
az aks create \
  --resource-group deceptinet-rg \
  --name deceptinet-prod \
  --node-count 3 \
  --node-vm-size Standard_D8s_v3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# 2. Get credentials
az aks get-credentials --resource-group deceptinet-rg --name deceptinet-prod

# 3. Deploy using script
export NAMESPACE=deceptinet
export ENVIRONMENT=production
./deploy-k8s.sh
```

### GCP GKE Deployment

```bash
# 1. Create GKE cluster
gcloud container clusters create deceptinet-prod \
  --zone us-central1-a \
  --machine-type n1-standard-8 \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10

# 2. Get credentials
gcloud container clusters get-credentials deceptinet-prod --zone us-central1-a

# 3. Deploy using script
export NAMESPACE=deceptinet
export ENVIRONMENT=production
./deploy-k8s.sh
```

---

## Verification

### Automated Verification

```bash
# PowerShell
.\verify-deployment.ps1

# Bash
./verify-deployment.sh
```

### Manual Verification

```bash
# Check health
curl http://localhost:8000/health

# Check readiness
curl http://localhost:8000/ready

# List honeypots
curl http://localhost:8000/api/honeypots

# Check metrics
curl http://localhost:8000/api/metrics
```

### Expected Output

**Health Endpoint:**
```json
{
  "status": "alive",
  "service": "deception-engine",
  "uptime_seconds": 42.5
}
```

**Readiness Endpoint:**
```json
{
  "status": "ready",
  "service": "deception-engine",
  "active_honeypots": 0,
  "available_adapters": ["cowrie", "dionaea", "custom"]
}
```

---

## Troubleshooting

### Common Issues

#### 1. Services Not Starting

```bash
# Check logs
docker-compose -f docker/docker-compose.yml logs

# Or in Kubernetes
kubectl logs -f deployment/deceptinet-deception -n deceptinet
```

#### 2. Database Connection Failed

```bash
# Check if PostgreSQL is running
docker-compose -f docker/docker-compose.yml ps postgres

# Test connection
docker-compose -f docker/docker-compose.yml exec postgres psql -U deceptinet_user -d deceptinet
```

#### 3. Kafka Not Ready

```bash
# Wait longer (Kafka takes 60-90 seconds)
sleep 90

# Check Kafka
docker-compose -f docker/docker-compose.yml logs kafka
```

#### 4. Out of Memory

```bash
# Increase Docker memory limit (Docker Desktop)
# Settings -> Resources -> Memory -> 8GB+

# Or adjust resource limits in docker-compose.yml
```

#### 5. Port Already in Use

```bash
# Find process using port
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/Mac

# Kill process or change port in .env
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database
docker-compose exec postgres pg_isready

# Kafka
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Elasticsearch
curl http://localhost:9200/_cluster/health
```

### Performance Tuning

#### Increase Workers

```bash
# In .env
DECEPTION_ENGINE_WORKERS=8
ML_BATCH_SIZE=100

# Restart services
docker-compose restart
```

#### Scale Kubernetes Deployment

```bash
kubectl scale deployment deceptinet-deception --replicas=5 -n deceptinet
```

---

## Monitoring

### Prometheus Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_errors_total[5m])

# Response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Grafana Dashboards

- Navigate to http://localhost:3001
- Login: admin/admin
- Import dashboards from `infrastructure/grafana/dashboards/`

---

## Backup and Recovery

### Backup

```bash
# Database backup
docker-compose exec postgres pg_dump -U deceptinet_user deceptinet > backup.sql

# Models backup
tar -czf models-backup.tar.gz models/

# Configuration backup
tar -czf config-backup.tar.gz .env config.yaml
```

### Restore

```bash
# Database restore
docker-compose exec -T postgres psql -U deceptinet_user deceptinet < backup.sql

# Models restore
tar -xzf models-backup.tar.gz

# Configuration restore
tar -xzf config-backup.tar.gz
```

---

## Security Hardening

### 1. Update Default Passwords

```bash
# In .env file, change ALL passwords:
POSTGRES_PASSWORD=<strong-random-password>
REDIS_PASSWORD=<strong-random-password>
GRAFANA_ADMIN_PASSWORD=<strong-random-password>
```

### 2. Enable TLS

```bash
# Generate certificates
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Update .env
TLS_ENABLED=true
TLS_CERT_PATH=/etc/ssl/certs/deceptinet.crt
TLS_KEY_PATH=/etc/ssl/private/deceptinet.key
```

### 3. Network Policies

```bash
# Apply network policies (Kubernetes)
kubectl apply -f security/network-policies.yaml -n deceptinet
```

### 4. RBAC

```bash
# Apply RBAC policies (Kubernetes)
kubectl apply -f security/rbac.yaml -n deceptinet
```

---

## Next Steps

1. **Train ML Models**: `python ml/model_trainer.py`
2. **Configure Honeypots**: Edit `config.yaml`
3. **Set up Threat Intelligence**: Add MISP/OpenCTI API keys
4. **Configure Alerts**: Set up Prometheus alerting rules
5. **Train SOC Team**: Review documentation and dashboards

---

## Support

- **Documentation**: See `docs/` directory
- **Issues**: https://github.com/your-org/deceptinet/issues
- **Security**: security@your-domain.com

---

**Deployment Complete! 🎉**

Your DECEPTINET platform is now ready for production use.
