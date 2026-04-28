# 🚀 DecepitNet - Optimized Kubernetes Deployment

Complete Kubernetes deployment manifests for DecepitNet with all performance optimizations enabled.

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Ingress Controller                      │
│              (nginx, SSL termination, routing)              │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴────────────────┐
        │                                │
┌───────▼────────┐              ┌───────▼────────┐
│  Deception     │              │   Dashboard    │
│  Engine API    │              │   Service      │
│  (3-10 pods)   │              │   (2 pods)     │
└───────┬────────┘              └───────┬────────┘
        │                                │
        └───────────────┬────────────────┘
                        │
        ┌───────────────┼────────────────┐
        │               │                │
┌───────▼────────┐ ┌───▼─────┐  ┌──────▼──────┐
│   PostgreSQL   │ │  Redis  │  │    Kafka    │
│   (Database)   │ │ (Cache) │  │  (Streaming)│
└────────────────┘ └─────────┘  └──────┬──────┘
                                        │
                                ┌───────▼────────┐
                                │  ML Consumer   │
                                │  (2-8 pods)    │
                                └────────────────┘
```

## ✨ Optimization Features

### 1. **Horizontal Pod Autoscaling (HPA)**
- **Deception Engine**: 3-10 pods based on CPU/Memory
- **ML Consumer**: 2-8 pods based on load
- Automatic scaling based on metrics

### 2. **Resource Management**
- **Request/Limit Ratios**: Optimized for burst capacity
- **QoS Classes**: Guaranteed for critical components
- **Resource Quotas**: Namespace-level controls

### 3. **High Availability**
- **Pod Anti-Affinity**: Distribute across nodes
- **Rolling Updates**: Zero-downtime deployments
- **Health Checks**: Liveness and readiness probes

### 4. **Performance Optimizations**
- ✅ Lazy Model Loading (cache size: 10)
- ✅ Database Connection Pooling (10-50 connections)
- ✅ Kafka Batch Processing (batch size: 200)
- ✅ Redis Caching (TTL: 300-600s)
- ✅ Optimized Data Structures

### 5. **Security**
- **Network Policies**: Default deny with explicit allows
- **RBAC**: Role-based access control
- **Secrets Management**: Encrypted credentials
- **Pod Security**: Non-root users

## 📁 Files

| File | Description |
|------|-------------|
| `namespace.yaml` | Namespace definition |
| `configmap.yaml` | Configuration parameters |
| `secrets.yaml` | Sensitive credentials |
| `postgresql-deployment.yaml` | PostgreSQL database |
| `redis-deployment.yaml` | Redis cache |
| `kafka-deployment.yaml` | Kafka + Zookeeper |
| `deception-engine-deployment.yaml` | Deception Engine API + HPA |
| `ml-consumer-deployment.yaml` | ML Consumer + HPA |
| `main-platform-deployment.yaml` | Main platform service |
| `ingress.yaml` | Ingress routing |
| `network-policy.yaml` | Network security |
| `resource-quota.yaml` | Resource limits |
| `deploy.sh` | Linux/Mac deployment script |
| `deploy.ps1` | Windows deployment script |

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes Cluster** (1.28+)
   - Minikube, Kind, EKS, GKE, AKS, etc.
   - At least 3 nodes recommended

2. **kubectl** installed and configured

3. **Ingress Controller** (optional)
   ```bash
   # Install nginx ingress controller
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
   ```

4. **Metrics Server** (for HPA)
   ```bash
   kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
   ```

### Deployment

#### Linux/Mac

```bash
cd k8s
chmod +x deploy.sh
./deploy.sh
```

#### Windows

```powershell
cd k8s
.\deploy.ps1
```

#### Manual Deployment

```bash
# 1. Create namespace
kubectl apply -f namespace.yaml

# 2. Apply configuration
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f resource-quota.yaml

# 3. Deploy infrastructure
kubectl apply -f postgresql-deployment.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f kafka-deployment.yaml

# Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=postgresql -n deceptinet --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n deceptinet --timeout=300s
kubectl wait --for=condition=ready pod -l app=kafka -n deceptinet --timeout=300s

# 4. Deploy applications
kubectl apply -f deception-engine-deployment.yaml
kubectl apply -f ml-consumer-deployment.yaml
kubectl apply -f main-platform-deployment.yaml

# 5. Apply network policies
kubectl apply -f network-policy.yaml

# 6. Apply ingress (optional)
kubectl apply -f ingress.yaml
```

## 🔧 Configuration

### Edit ConfigMap

```bash
kubectl edit configmap deceptinet-config -n deceptinet
```

**Key Parameters:**

```yaml
# Model caching
MODEL_CACHE_SIZE: "10"  # Number of ML models to cache

# Database pooling
DB_POOL_MIN_SIZE: "10"  # Minimum connections
DB_POOL_MAX_SIZE: "50"  # Maximum connections

# Kafka optimization
KAFKA_BATCH_SIZE: "200"     # Events per batch
KAFKA_BATCH_TIMEOUT: "3.0"  # Batch timeout (seconds)

# Redis caching
REDIS_CACHE_TTL_API: "300"  # API cache TTL (5 min)
REDIS_CACHE_TTL_ML: "600"   # ML cache TTL (10 min)
```

### Update Secrets

```bash
# Create from literal values
kubectl create secret generic deceptinet-secrets \
  --from-literal=POSTGRES_PASSWORD='your-strong-password' \
  --from-literal=MISP_API_KEY='your-misp-key' \
  --from-literal=OPENCTI_TOKEN='your-opencti-token' \
  --namespace=deceptinet \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Scale Services

```bash
# Manual scaling
kubectl scale deployment deception-engine --replicas=5 -n deceptinet
kubectl scale deployment ml-consumer --replicas=4 -n deceptinet

# Check HPA status
kubectl get hpa -n deceptinet

# Edit HPA
kubectl edit hpa deception-engine-hpa -n deceptinet
```

## 📊 Monitoring

### Check Status

```bash
# All resources
kubectl get all -n deceptinet

# Deployments
kubectl get deployments -n deceptinet

# Pods
kubectl get pods -n deceptinet -o wide

# Services
kubectl get services -n deceptinet

# PVCs
kubectl get pvc -n deceptinet

# HPA
kubectl get hpa -n deceptinet
```

### Watch Resources

```bash
# Watch pods
kubectl get pods -n deceptinet -w

# Watch HPA
kubectl get hpa -n deceptinet -w

# Watch events
kubectl get events -n deceptinet --sort-by='.lastTimestamp'
```

### View Logs

```bash
# Deception Engine
kubectl logs -f deployment/deception-engine -n deceptinet

# ML Consumer
kubectl logs -f deployment/ml-consumer -n deceptinet

# Specific pod
kubectl logs -f <pod-name> -n deceptinet

# Previous logs
kubectl logs --previous <pod-name> -n deceptinet

# All pods in deployment
kubectl logs -f -l app=deception-engine -n deceptinet
```

### Debug Pods

```bash
# Exec into pod
kubectl exec -it <pod-name> -n deceptinet -- /bin/bash

# Port forward
kubectl port-forward svc/deception-engine-service 8000:8000 -n deceptinet
kubectl port-forward svc/deceptinet-dashboard-service 5000:5000 -n deceptinet

# Describe resources
kubectl describe pod <pod-name> -n deceptinet
kubectl describe deployment deception-engine -n deceptinet
```

## 🌐 Access Services

### Internal Access (within cluster)

```bash
# From another pod
curl http://deception-engine-service.deceptinet.svc.cluster.local:8000/health
curl http://redis-service.deceptinet.svc.cluster.local:6379
```

### Port Forwarding

```bash
# Deception Engine API
kubectl port-forward svc/deception-engine-service 8000:8000 -n deceptinet
# Access at http://localhost:8000

# Dashboard
kubectl port-forward svc/deceptinet-dashboard-service 5000:5000 -n deceptinet
# Access at http://localhost:5000

# PostgreSQL
kubectl port-forward svc/postgresql-service 5432:5432 -n deceptinet

# Redis
kubectl port-forward svc/redis-service 6379:6379 -n deceptinet
```

### External Access (via Ingress)

Update `ingress.yaml` with your domain:

```yaml
rules:
- host: api.deceptinet.yourdomain.com
- host: dashboard.deceptinet.yourdomain.com
```

Then access:
- API: https://api.deceptinet.yourdomain.com
- Dashboard: https://dashboard.deceptinet.yourdomain.com

## 🔒 Security Considerations

### 1. Update Secrets

**CRITICAL**: Change default passwords in `secrets.yaml`

```bash
# Generate strong password
openssl rand -base64 32

# Update secret
kubectl create secret generic deceptinet-secrets \
  --from-literal=POSTGRES_PASSWORD='<strong-password>' \
  --namespace=deceptinet \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 2. Enable TLS

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 3. Network Policies

Network policies are applied by default:
- Default deny all ingress
- Explicit allows for required traffic
- Review `network-policy.yaml` for details

### 4. RBAC

Create service accounts and roles:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: deceptinet-sa
  namespace: deceptinet
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deceptinet-role
  namespace: deceptinet
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
```

## 📈 Performance Tuning

### Resource Allocation

**Current Settings:**

| Component | Requests | Limits |
|-----------|----------|--------|
| Deception Engine | 1 CPU, 2Gi | 2 CPU, 4Gi |
| ML Consumer | 2 CPU, 4Gi | 4 CPU, 8Gi |
| PostgreSQL | 1 CPU, 2Gi | 2 CPU, 4Gi |
| Redis | 500m, 1Gi | 1 CPU, 2Gi |
| Kafka | 1 CPU, 2Gi | 2 CPU, 4Gi |

**Adjust based on load:**

```yaml
resources:
  requests:
    memory: "4Gi"  # Increase for heavy load
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

### HPA Tuning

```yaml
# Edit HPA
kubectl edit hpa deception-engine-hpa -n deceptinet

# Adjust thresholds
spec:
  minReplicas: 5      # Increase minimum
  maxReplicas: 20     # Increase maximum
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60  # Lower threshold = scale sooner
```

### Storage Performance

For production, use SSD storage:

```yaml
# Update storage class in all PVC definitions
storageClassName: fast-ssd  # or premium-ssd, gp3, etc.
```

## 🧪 Testing

### Load Testing

```bash
# Port forward API
kubectl port-forward svc/deception-engine-service 8000:8000 -n deceptinet

# Run load test (using hey, ab, or wrk)
hey -n 10000 -c 100 http://localhost:8000/health

# Watch HPA during load
kubectl get hpa -n deceptinet -w
```

### Health Checks

```bash
# Check all health endpoints
kubectl port-forward svc/deception-engine-service 8000:8000 -n deceptinet

# In another terminal
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/health
```

## 🔄 Updates & Rollbacks

### Update Image

```bash
# Update image
kubectl set image deployment/deception-engine \
  deception-engine=deceptinet/deception-engine:v1.1.0 \
  -n deceptinet

# Check rollout status
kubectl rollout status deployment/deception-engine -n deceptinet

# View rollout history
kubectl rollout history deployment/deception-engine -n deceptinet
```

### Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/deception-engine -n deceptinet

# Rollback to specific revision
kubectl rollout undo deployment/deception-engine --to-revision=2 -n deceptinet
```

## 🗑️ Cleanup

### Delete Everything

```bash
# Delete namespace (removes all resources)
kubectl delete namespace deceptinet

# Or delete individually
kubectl delete -f ingress.yaml
kubectl delete -f main-platform-deployment.yaml
kubectl delete -f ml-consumer-deployment.yaml
kubectl delete -f deception-engine-deployment.yaml
kubectl delete -f kafka-deployment.yaml
kubectl delete -f redis-deployment.yaml
kubectl delete -f postgresql-deployment.yaml
kubectl delete -f network-policy.yaml
kubectl delete -f resource-quota.yaml
kubectl delete -f secrets.yaml
kubectl delete -f configmap.yaml
kubectl delete -f namespace.yaml
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [HPA Documentation](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)

## 🆘 Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n deceptinet

# Common issues:
# - ImagePullBackOff: Image not found or authentication issue
# - CrashLoopBackOff: Application crashing, check logs
# - Pending: Insufficient resources or PVC issues
```

### HPA Not Scaling

```bash
# Check metrics server
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml

# Check HPA status
kubectl describe hpa deception-engine-hpa -n deceptinet

# Ensure metrics are available
kubectl top pods -n deceptinet
```

### Network Issues

```bash
# Test connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n deceptinet -- sh

# Inside pod
curl http://deception-engine-service:8000/health
curl http://postgresql-service:5432
```

### Storage Issues

```bash
# Check PVC status
kubectl get pvc -n deceptinet

# Describe PVC
kubectl describe pvc <pvc-name> -n deceptinet

# Check storage class
kubectl get storageclass
```

## 🎯 Production Checklist

- [ ] Update all secrets with strong passwords
- [ ] Configure proper storage class (SSD)
- [ ] Enable TLS/SSL certificates
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backup strategy for PostgreSQL
- [ ] Test disaster recovery procedures
- [ ] Review and adjust resource limits
- [ ] Configure log aggregation (ELK/Loki)
- [ ] Set up alerting rules
- [ ] Document runbooks
- [ ] Test HPA behavior under load
- [ ] Verify network policies
- [ ] Enable pod security policies
- [ ] Configure node affinity/anti-affinity
- [ ] Set up CI/CD pipelines

---

**Version:** 1.0.0  
**Last Updated:** 2025-01-22  
**Status:** Production Ready ✅
