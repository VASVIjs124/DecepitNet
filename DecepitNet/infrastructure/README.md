# Infrastructure Directory
# Production-grade deployment configurations for DECEPTINET

This directory contains all infrastructure-as-code for deploying DECEPTINET in production environments.

## Structure

```
infrastructure/
├── kubernetes/         # Kubernetes manifests
├── helm/              # Helm charts
├── elk/               # ELK stack (Elasticsearch, Logstash, Kibana)
├── kafka/             # Apache Kafka message broker
├── honeypots/         # Production honeypot deployments
├── monitoring/        # Prometheus & Grafana
├── vault/             # HashiCorp Vault secrets
└── docker/            # Docker and Docker Compose files
```

## Deployment Options

### Option 1: Kubernetes (Recommended for Production)
```bash
kubectl apply -f kubernetes/namespace.yaml
helm install deceptinet ./helm/deceptinet
```

### Option 2: Docker Compose (Development/Testing)
```bash
docker-compose -f docker/docker-compose.yml up -d
```

## Prerequisites

- Kubernetes 1.24+ (for K8s deployment)
- Docker 20.10+ & Docker Compose 2.0+
- Helm 3.0+
- At least 32GB RAM, 8 CPU cores
- 500GB storage for logs

## Quick Start

See individual subdirectories for specific deployment instructions.
