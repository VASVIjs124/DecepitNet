# ==============================================================================
# DECEPTINET INFRASTRUCTURE QUICKSTART
# Complete setup guide for production deployment
# ==============================================================================

## Prerequisites

Before deploying DECEPTINET infrastructure, ensure you have:

### Required Software
- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Kubernetes** 1.24+ (for K8s deployment)
- **kubectl** configured and connected to your cluster
- **Helm** 3.0+
- **Python** 3.8+ (for local development)

### System Requirements
- **Minimum**: 32GB RAM, 8 CPU cores, 500GB storage
- **Recommended**: 64GB RAM, 16 CPU cores, 1TB SSD storage
- **Network**: Static IP addresses for honeypots, firewall access

---

## Option 1: Quick Start with Docker Compose (Development)

### Step 1: Clone and Navigate
```bash
cd infrastructure/docker
```

### Step 2: Set Environment Variables
```bash
# Create .env file
cat > .env << EOF
POSTGRES_PASSWORD=securepassword123
MONGO_PASSWORD=securepassword456
REDIS_PASSWORD=securepassword789
RABBITMQ_PASSWORD=securepassword101
GRAFANA_PASSWORD=admin123
EOF
```

### Step 3: Start All Services
```bash
# Start entire stack
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 4: Verify Services
```bash
# Elasticsearch (should return cluster health)
curl http://localhost:9200/_cluster/health

# Kibana (opens in browser)
open http://localhost:5601

# Grafana (login: admin / admin123)
open http://localhost:3000

# Prometheus
open http://localhost:9090
```

### Step 5: Test Honeypot Integration
```bash
# Send test log to Logstash
echo '{"source_ip":"192.168.1.100","protocol":"ssh","payload":"test"}' | \
  nc localhost 5000

# Check Elasticsearch
curl "http://localhost:9200/deceptinet-honeypot-*/_search?pretty&size=1"
```

---

## Option 2: Production Deployment on Kubernetes

### Step 1: Create Namespaces
```bash
kubectl apply -f kubernetes/namespace.yaml
```

### Step 2: Deploy ELK Stack
```bash
# Create ConfigMaps
kubectl create configmap elasticsearch-config \
  --from-file=elk/elasticsearch/config/elasticsearch.yml \
  -n deceptinet

kubectl create configmap logstash-config \
  --from-file=elk/logstash/config/logstash.yml \
  -n deceptinet

kubectl create configmap logstash-pipeline \
  --from-file=elk/logstash/pipeline/honeypot-pipeline.conf \
  -n deceptinet

# Deploy Elasticsearch
kubectl apply -f kubernetes/elk/elasticsearch-deployment.yaml

# Wait for Elasticsearch to be ready
kubectl wait --for=condition=ready pod -l app=elasticsearch -n deceptinet --timeout=5m

# Deploy Logstash
kubectl apply -f kubernetes/elk/logstash-deployment.yaml

# Deploy Kibana
kubectl apply -f kubernetes/elk/kibana-deployment.yaml
```

### Step 3: Deploy Kafka
```bash
kubectl apply -f kubernetes/kafka/zookeeper-deployment.yaml
kubectl wait --for=condition=ready pod -l app=zookeeper -n deceptinet --timeout=3m

kubectl apply -f kubernetes/kafka/kafka-deployment.yaml
kubectl wait --for=condition=ready pod -l app=kafka -n deceptinet --timeout=3m
```

### Step 4: Deploy Honeypots
```bash
# Deploy Cowrie SSH/Telnet honeypot
kubectl apply -f kubernetes/honeypots/cowrie-deployment.yaml

# Deploy Dionaea malware honeypot
kubectl apply -f kubernetes/honeypots/dionaea-deployment.yaml

# Verify honeypots are running
kubectl get pods -n deceptinet-honeypots
kubectl logs -f -n deceptinet-honeypots deployment/cowrie
```

### Step 5: Deploy Monitoring Stack
```bash
# Create Prometheus ConfigMap
kubectl create configmap prometheus-config \
  --from-file=monitoring/prometheus/prometheus.yml \
  --from-file=monitoring/prometheus/alerts/ \
  -n deceptinet-monitoring

# Deploy Prometheus
kubectl apply -f kubernetes/monitoring/prometheus-deployment.yaml

# Deploy Grafana
kubectl apply -f kubernetes/monitoring/grafana-deployment.yaml

# Get Grafana URL
kubectl get svc grafana -n deceptinet-monitoring
```

### Step 6: Configure Kibana Dashboards
```bash
# Port-forward Kibana
kubectl port-forward svc/kibana 5601:5601 -n deceptinet

# Open browser to http://localhost:5601
# Navigate to Management > Stack Management > Index Patterns
# Create index pattern: deceptinet-honeypot-*
```

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        INTERNET                               │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ Attacker Traffic
             ▼
┌────────────────────────────────────────────────────────────────┐
│                   HONEYPOT LAYER (K8s Pods)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Cowrie  │  │ Dionaea  │  │  Honeyd  │  │  Custom  │      │
│  │ SSH/Tel  │  │ Malware  │  │ Network  │  │ Honeypots│      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │              │             │            │
│       └─────────────┴──────────────┴─────────────┘            │
│                     │                                         │
│                     │ Logs via Filebeat                       │
│                     ▼                                         │
└────────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────────┐
│                    TELEMETRY PIPELINE                          │
│  ┌─────────────┐      ┌──────────────┐      ┌─────────────┐  │
│  │  Filebeat   │ ───▶ │  Logstash    │ ───▶ │Elasticsearch│  │
│  │ Log Shipper │      │  Processor   │      │   Storage   │  │
│  └─────────────┘      └──────┬───────┘      └─────────────┘  │
│                              │                                │
│                              │ Enriched Events                │
│                              ▼                                │
│                       ┌─────────────┐                         │
│                       │    Kafka    │                         │
│                       │ Message Bus │                         │
│                       └──────┬──────┘                         │
└──────────────────────────────┼─────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                    ML/AI PROCESSING LAYER                      │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   XGBoost     │  │  CNN Model   │  │  RL Agents (PPO) │   │
│  │ Classifier    │  │  Sequence    │  │  Deception Opt   │   │
│  └───────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                    VISUALIZATION LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │    Kibana    │  │   Grafana    │  │    React     │        │
│  │  (Telemetry) │  │  (Metrics)   │  │  Dashboard   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────┘
```

---

## Service Endpoints

| Service | URL | Credentials |
|---------|-----|-------------|
| **Kibana** | http://localhost:5601 | None (dev) |
| **Grafana** | http://localhost:3000 | admin / admin123 |
| **Prometheus** | http://localhost:9090 | None |
| **Elasticsearch** | http://localhost:9200 | None (dev) |
| **RabbitMQ Management** | http://localhost:15672 | deceptinet / changeme |
| **Cowrie SSH** | localhost:22 | See userdb.txt |

---

## Data Flow

1. **Attack Traffic** → Honeypots (Cowrie, Dionaea, Custom)
2. **Honeypot Logs** → Filebeat → Logstash
3. **Logstash** → 
   - Elasticsearch (storage & search)
   - Kafka (ML streaming)
4. **Kafka** → ML Models (XGBoost, CNN, RL agents)
5. **ML Predictions** → DeceptionEngine → Honeypot Adaptation
6. **Visualization**:
   - Kibana (raw telemetry, MITRE ATT&CK mapping)
   - Grafana (metrics, alerts, system health)
   - React Dashboard (SOC interface, XAI insights)

---

## Troubleshooting

### Elasticsearch Won't Start
```bash
# Increase vm.max_map_count (Linux)
sudo sysctl -w vm.max_map_count=262144

# Make permanent
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

### Kafka Connection Refused
```bash
# Verify Zookeeper is running
docker-compose ps zookeeper

# Check Kafka logs
docker-compose logs kafka

# Test connection
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

### No Logs in Elasticsearch
```bash
# Check Filebeat status
docker-compose logs filebeat

# Check Logstash pipeline
docker-compose logs logstash | grep ERROR

# Manually test Logstash
echo '{"test":"message"}' | nc localhost 5000
```

### Honeypot Not Accessible
```bash
# Check port bindings
docker-compose ps
netstat -tulpn | grep <port>

# Check firewall
sudo ufw allow 22/tcp  # For Cowrie SSH
sudo ufw allow 445/tcp # For Dionaea SMB
```

---

## Next Steps

1. **Configure Kibana Dashboards**
   - Import pre-built dashboards from `monitoring/kibana/dashboards/`
   - Create MITRE ATT&CK heatmap visualization

2. **Set Up Grafana Alerts**
   - Configure alert channels (email, Slack, PagerDuty)
   - Import Prometheus alert rules

3. **Deploy ML Models** (Sprint 3-5)
   - Train XGBoost classifier on collected data
   - Deploy CNN for sequence analysis
   - Initialize RL agents

4. **Integrate Threat Intelligence** (Sprint 6-8)
   - Connect MISP for IOC enrichment
   - Configure OpenCTI for CTI

5. **Build Production Dashboard** (Sprint 9)
   - Deploy React frontend
   - Configure Socket.IO for real-time updates

---

## Security Hardening

⚠️ **IMPORTANT**: Default configuration is for DEVELOPMENT only.

### Production Checklist
- [ ] Enable Elasticsearch X-Pack security
- [ ] Configure TLS/SSL for all services
- [ ] Change all default passwords
- [ ] Implement network segmentation
- [ ] Enable firewall rules (egress filtering)
- [ ] Configure HashiCorp Vault for secrets
- [ ] Enable audit logging
- [ ] Implement rate limiting
- [ ] Set up backup and disaster recovery

---

## Support

For issues, questions, or contributions:
- GitHub Issues: [Create Issue]
- Documentation: See `/docs` directory
- Sprint Progress: See `IMPLEMENTATION_ROADMAP.md`

---

**Status**: Sprint 1-2 Infrastructure Foundation ✅ COMPLETE
**Next**: Sprint 3-5 ML/AI Components
