# DECEPTINET Architecture Overview

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                         DECEPTINET Production Architecture                      │
└────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend Layer                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  React Dashboard (TypeScript + Vite)                                 │   │
│  │  - Real-time attack visualization                                    │   │
│  │  - MITRE ATT&CK heatmap                                             │   │
│  │  - ML insights (SHAP/LIME explanations)                             │   │
│  │  - Threat intelligence feed                                          │   │
│  │  - Configuration management                                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                            ↕ (Socket.IO + REST API)                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         API Gateway / Load Balancer                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Nginx Ingress Controller                                                    │
│  - TLS termination                                                           │
│  - Rate limiting                                                             │
│  - Authentication                                                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           Application Layer                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │ Deception Engine     │  │  ML Pipeline         │  │  RL Agents       │  │
│  │ (FastAPI)            │  │  (Python)            │  │  (Ray RLlib)     │  │
│  ├──────────────────────┤  ├──────────────────────┤  ├──────────────────┤  │
│  │ • REST API (15+      │  │ • XGBoost Classifier │  │ • PPO Policy     │  │
│  │   endpoints)         │  │ • CNN Sequences      │  │ • SAC Deception  │  │
│  │ • Policy Manager     │  │ • DBSCAN Profiler    │  │ • Attacker Sim   │  │
│  │ • Adaptation Scorer  │  │ • IsolationForest    │  │ • Gym Envs       │  │
│  │ • Honeypot Adapters  │  │ • LSTM Autoencoder   │  │ • Training Jobs  │  │
│  │ • Strategy Engine    │  │ • SHAP/LIME XAI      │  │                  │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
│           ↕                          ↕                          ↕            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          Integration Layer                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐   │
│  │ MISP Integration │  │ OpenCTI          │  │ Caldera (Future)        │   │
│  │ - IP enrichment  │  │ - Threat actors  │  │ - ATT&CK emulation      │   │
│  │ - Hash lookup    │  │ - Malware        │  │ - Adversary simulation  │   │
│  │ - Domain intel   │  │ - Attack patterns│  │                         │   │
│  │ - Event creation │  │ - STIX/TAXII     │  │                         │   │
│  └──────────────────┘  └──────────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          Message Queue Layer                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Apache Kafka (3 brokers)                                           │   │
│  │  Topics:                                                             │   │
│  │  • honeypot-events (raw telemetry)                                  │   │
│  │  • ml-predictions (classification results)                          │   │
│  │  • threat-intel (enriched IOCs)                                     │   │
│  │  • deception-commands (configuration updates)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                            ↕ (Producers/Consumers)                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           Honeypot Layer                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ Cowrie (SSH/Tel) │  │ Dionaea (Malware)│  │ Custom Honeypots         │  │
│  │ - Port 22, 23    │  │ - SMB, HTTP, FTP │  │ - Internal services      │  │
│  │ - Command logging│  │ - Malware capture│  │ - API endpoints          │  │
│  │ - File downloads │  │ - Multi-protocol │  │ - Database services      │  │
│  │ - Session replay │  │ - Payload storage│  │                          │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                            ↕ (Event streaming to Kafka)                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            Storage Layer                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ PostgreSQL   │  │ Elasticsearch│  │ Redis        │  │ MongoDB       │  │
│  │ - Metadata   │  │ - Events     │  │ - Cache      │  │ - Files       │  │
│  │ - Users      │  │ - Logs       │  │ - Sessions   │  │ - Malware     │  │
│  │ - Config     │  │ - Metrics    │  │ - Queue      │  │ - Artifacts   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        Monitoring & Observability                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │ Prometheus                  │  │ Grafana                              │ │
│  │ - Metrics scraping          │  │ - Dashboards (Attack rates, ML       │ │
│  │ - Alert rules               │  │   metrics, System health)            │ │
│  │ - Time-series database      │  │ - Alerting                           │ │
│  └─────────────────────────────┘  └──────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │ Kibana                      │  │ Logstash                             │ │
│  │ - Log visualization         │  │ - Log parsing                        │ │
│  │ - Attack analysis           │  │ - MITRE ATT&CK enrichment           │ │
│  │ - Search & dashboards       │  │ - Format transformation              │ │
│  └─────────────────────────────┘  └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           Security Layer                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Network Policies (namespace isolation, honeypot egress restriction)       │
│  • RBAC (3 roles: admin, ml-pipeline, readonly)                             │
│  • Pod Security Policies (restricted + honeypot)                            │
│  • Secrets Management (Kubernetes Secrets, future: HashiCorp Vault)         │
│  • TLS/mTLS (in-transit encryption)                                         │
│  • Vulnerability Scanning (Trivy, Snyk)                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          CI/CD Pipeline                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  GitHub Actions Workflows:                                                   │
│  1. CI (test, lint, format check, security scan)                            │
│  2. CD (build, push images, deploy staging → production)                    │
│  3. Security Scanning (dependency scan, container scan, SAST, secret scan)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Attack Detection Flow

```
Attacker → Honeypot → Kafka (raw event) → Logstash → Elasticsearch
                         ↓
                    ML Pipeline
                         ↓
            ┌────────────┴────────────┐
            ↓                         ↓
    Classification              Profiling
    (XGBoost + CNN)         (DBSCAN + IsolForest)
            ↓                         ↓
    ┌───────┴─────────┬───────────────┴──────┐
    ↓                 ↓                      ↓
Prediction      Explanation              Anomaly
(attack type)   (SHAP/LIME)            (yes/no)
    ↓                 ↓                      ↓
    └─────────────────┴──────────────────────┘
                      ↓
            Threat Intel Enrichment
            (MISP + OpenCTI lookup)
                      ↓
            Kafka (ml-predictions)
                      ↓
        ┌─────────────┴─────────────┐
        ↓                           ↓
   Elasticsearch              Deception Engine
   (storage)                  (adaptive config)
        ↓                           ↓
   Dashboard                   Honeypot Update
   (visualization)             (new strategy)
```

### RL Training Flow

```
Honeypot Events → Feature Extraction → RL Environment State
                                              ↓
                                        RL Agent (PPO/SAC)
                                              ↓
                                      Action (config change)
                                              ↓
                                    Deception Engine API
                                              ↓
                                    Honeypot Reconfiguration
                                              ↓
                                        New Events
                                              ↓
                                    Reward Calculation
                                              ↓
                                    Model Update (training)
```

## Component Details

### Deception Engine
- **Language**: Python with FastAPI
- **Endpoints**: 15+ REST endpoints
- **Components**:
  - Policy Manager (4 policies)
  - Adaptation Scorer (5-component algorithm)
  - Honeypot Adapters (Cowrie, Dionaea, Custom)
  - Strategy Engine (3 default strategies)

### ML Pipeline
- **Models**: 5 total (XGBoost, CNN, DBSCAN, IsolationForest, LSTM)
- **Features**: 11 tabular + sequence data
- **Processing**: Batch (50 events) + real-time
- **Explainability**: SHAP + LIME

### RL Agents
- **Algorithms**: PPO (deception + attacker), SAC (deception alternative)
- **Environments**: HoneypotEnvironment, AttackerSimEnvironment
- **Training**: Stable-Baselines3 with TensorBoard
- **Deployment**: Kubernetes CronJobs

### Threat Intelligence
- **Platforms**: MISP, OpenCTI
- **Enrichment**: IP, hash, domain lookup
- **Automation**: Event creation from honeypot detections
- **Standards**: STIX 2, TAXII 2, MITRE ATT&CK

## Deployment Topology

### Development
- Docker Compose with 12 services
- Local Kubernetes (minikube/kind)
- Hot-reload for development

### Staging
- AWS EKS or Azure AKS
- 3-node cluster
- Auto-scaling enabled
- Limited external access

### Production
- Multi-region Kubernetes
- High availability (3+ replicas)
- Geo-distributed honeypots
- DDoS protection
- WAF (Web Application Firewall)

## Scalability

- **Horizontal**: Kubernetes HPA scales pods based on CPU/memory
- **Vertical**: Configurable resource requests/limits
- **Data**: Elasticsearch sharding, Kafka partitioning
- **ML**: Batch inference, model serving on GPUs
- **RL**: Distributed training with Ray

## High Availability

- **Database**: PostgreSQL replication, Redis Sentinel
- **Messaging**: Kafka 3-broker cluster with replication
- **Application**: Multiple replicas with anti-affinity
- **Storage**: Persistent Volumes with replication
- **Monitoring**: Prometheus HA, Grafana clustering

## Disaster Recovery

- **Backups**: Daily snapshots of databases, weekly model backups
- **Retention**: 30 days of events, 90 days of models
- **RTO**: <1 hour
- **RPO**: <15 minutes
- **Testing**: Quarterly DR drills

---

**Last Updated**: 2024
