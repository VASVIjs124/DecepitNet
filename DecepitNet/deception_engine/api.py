"""
FastAPI Deception Engine
RESTful API for adaptive honeypot configuration and deception orchestration
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import asyncio
import logging
from datetime import datetime, timezone
import numpy as np
import os
import hmac

from .adapters import HoneypotAdapter, CowrieAdapter, DionaeaAdapter
from .policy_manager import DeceptionPolicyManager
from .scoring import AdaptationScorer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DECEPTINET Deception Engine",
    description="Adaptive honeypot configuration and deception orchestration API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for health tracking
app_state = {
    "startup_time": datetime.now(timezone.utc),
    "ready": False,
    "adapters_initialized": False
}

# Pydantic models
class HoneypotConfig(BaseModel):
    honeypot_id: str = Field(..., description="Unique honeypot identifier")
    honeypot_type: str = Field(..., description="Type: cowrie, dionaea, custom")
    enabled_services: List[str] = Field(default=[], description="Active protocols")
    decoy_files: List[Dict[str, str]] = Field(default=[], description="Fake files")
    fake_credentials: List[Dict[str, str]] = Field(default=[], description="Credentials")
    response_delay_ms: int = Field(default=0, description="Artificial delay")
    logging_level: str = Field(default="info", description="Log verbosity")

class AdaptationRequest(BaseModel):
    honeypot_id: str
    recent_activity: List[Dict[str, Any]] = Field(default=[])
    threat_level: str = Field(default="low")
    adaptation_strategy: str = Field(default="auto", description="auto, aggressive, passive")

class DeceptionStrategy(BaseModel):
    strategy_id: str
    name: str
    description: str
    target_techniques: List[str] = Field(default=[], description="MITRE ATT&CK techniques")
    configuration: Dict[str, Any]

class TelemetryEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_ip: str
    protocol: str
    payload: Optional[str] = None
    threat_score: float = Field(ge=0, le=100)
    mitre_techniques: List[str] = Field(default=[])

# Global instances
policy_manager = DeceptionPolicyManager()
adaptation_scorer = AdaptationScorer()
honeypot_adapters: Dict[str, HoneypotAdapter] = {}


def _configured_api_key() -> str:
    """Resolve control API key from environment variables."""
    return str(
        os.getenv("DECEPTINET_API_KEY")
        or os.getenv("DECEPTINET_CONTROL_API_KEY")
        or os.getenv("API_KEY")
        or ""
    )


async def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None, alias="Authorization")
) -> None:
    configured = _configured_api_key()
    if not configured:
        raise HTTPException(status_code=503, detail="Control API key is not configured")

    provided = x_api_key
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization.split(" ", 1)[1].strip()

    if not provided or not hmac.compare_digest(str(provided), configured):
        raise HTTPException(status_code=401, detail="Invalid API key")


class DeceptionEngineAPI:
    """Main API class for deception engine operations"""
    
    def __init__(self):
        self.active_honeypots: Dict[str, HoneypotConfig] = {}
        self.strategies: Dict[str, DeceptionStrategy] = {}
        self.adaptation_history: List[Dict] = []
    
    async def initialize(self):
        """Initialize adapters and strategies"""
        logger.info("Initializing Deception Engine...")
        
        # Initialize default adapters
        honeypot_adapters['cowrie'] = CowrieAdapter()
        honeypot_adapters['dionaea'] = DionaeaAdapter()
        
        # Load default strategies
        await self._load_default_strategies()
        
        logger.info(f"Deception Engine initialized with {len(honeypot_adapters)} adapters")
    
    async def _load_default_strategies(self):
        """Load predefined deception strategies"""
        default_strategies = [
            DeceptionStrategy(
                strategy_id="aggressive_ssh",
                name="Aggressive SSH Deception",
                description="High-interaction SSH honeypot with realistic filesystem",
                target_techniques=["T1110", "T1078", "T1021.004"],
                configuration={
                    "enabled_services": ["ssh", "sftp"],
                    "decoy_files": [
                        {"path": "/etc/shadow", "content": "fake_hashes"},
                        {"path": "/root/.ssh/id_rsa", "content": "fake_private_key"},
                        {"path": "/home/admin/.bash_history", "content": "sudo su\ncd /var/www"}
                    ],
                    "fake_credentials": [
                        {"username": "root", "password": "toor"},
                        {"username": "admin", "password": "admin123"}
                    ],
                    "response_delay_ms": 500
                }
            ),
            DeceptionStrategy(
                strategy_id="malware_collection",
                name="Malware Collection Strategy",
                description="Optimized for capturing malware samples",
                target_techniques=["T1105", "T1203", "T1059"],
                configuration={
                    "enabled_services": ["http", "ftp", "smb"],
                    "download_enabled": True,
                    "max_file_size_mb": 100,
                    "auto_sandbox": True
                }
            ),
            DeceptionStrategy(
                strategy_id="reconnaissance_detection",
                name="Reconnaissance Detection",
                description="Detect scanning and enumeration activities",
                target_techniques=["T1595", "T1046", "T1590"],
                configuration={
                    "port_scan_detection": True,
                    "service_enumeration_alerts": True,
                    "decoy_services": ["mysql", "mssql", "mongodb", "redis"]
                }
            )
        ]
        
        for strategy in default_strategies:
            self.strategies[strategy.strategy_id] = strategy
        
        logger.info(f"Loaded {len(self.strategies)} default strategies")

# Global API instance
deception_api = DeceptionEngineAPI()


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    await deception_api.initialize()
    app_state["adapters_initialized"] = True
    app_state["ready"] = True
    logger.info("Deception Engine started and ready")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "DECEPTINET Deception Engine",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health():
    """
    Kubernetes liveness probe endpoint
    Returns 200 if the application is running (even if not ready)
    """
    uptime = (datetime.now(timezone.utc) - app_state["startup_time"]).total_seconds()
    return {
        "status": "alive",
        "service": "deception-engine",
        "uptime_seconds": round(uptime, 2)
    }


@app.get("/ready")
async def readiness():
    """
    Kubernetes readiness probe endpoint
    Returns 200 only when the application is ready to serve traffic
    """
    if not app_state["ready"]:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    if not app_state["adapters_initialized"]:
        raise HTTPException(status_code=503, detail="Adapters not initialized")
    
    uptime = (datetime.now(timezone.utc) - app_state["startup_time"]).total_seconds()
    return {
        "status": "ready",
        "service": "deception-engine",
        "uptime_seconds": round(uptime, 2),
        "active_honeypots": len(deception_api.active_honeypots),
        "available_adapters": [*honeypot_adapters]  # Unpacking is faster than list(dict.keys())
    }


@app.get("/api/health")
async def health_check():
    """Detailed health status with metrics"""
    uptime = (datetime.utcnow() - app_state["startup_time"]).total_seconds()
    return {
        "status": "healthy",
        "active_honeypots": len(deception_api.active_honeypots),
        "available_adapters": [*honeypot_adapters],  # Unpacking faster than list(keys())
        "loaded_strategies": len(deception_api.strategies),
        "uptime_seconds": round(uptime, 2),
        "ready": app_state["ready"]
    }


@app.get("/api/honeypots", response_model=List[HoneypotConfig])
async def list_honeypots():
    """List all registered honeypots"""
    return [*deception_api.active_honeypots.values()]  # Unpacking faster than list()


@app.post("/api/honeypots/register", response_model=Dict[str, str])
async def register_honeypot(config: HoneypotConfig, _: None = Depends(require_api_key)):
    """Register a new honeypot"""
    if config.honeypot_id in deception_api.active_honeypots:
        raise HTTPException(status_code=400, detail="Honeypot already registered")
    
    # Validate honeypot type
    if config.honeypot_type not in honeypot_adapters:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown honeypot type. Available: {[*honeypot_adapters]}"  # Unpacking
        )
    
    deception_api.active_honeypots[config.honeypot_id] = config
    logger.info(f"Registered honeypot: {config.honeypot_id} ({config.honeypot_type})")
    
    return {
        "status": "registered",
        "honeypot_id": config.honeypot_id,
        "message": "Honeypot successfully registered"
    }


@app.get("/api/honeypots/{honeypot_id}", response_model=HoneypotConfig)
async def get_honeypot(honeypot_id: str):
    """Get honeypot configuration"""
    if honeypot_id not in deception_api.active_honeypots:
        raise HTTPException(status_code=404, detail="Honeypot not found")
    
    return deception_api.active_honeypots[honeypot_id]


@app.put("/api/honeypots/{honeypot_id}/configure")
async def configure_honeypot(honeypot_id: str, config: HoneypotConfig, _: None = Depends(require_api_key)):
    """Update honeypot configuration"""
    if honeypot_id not in deception_api.active_honeypots:
        raise HTTPException(status_code=404, detail="Honeypot not found")
    
    # Apply configuration through adapter
    honeypot = deception_api.active_honeypots[honeypot_id]
    adapter = honeypot_adapters.get(honeypot.honeypot_type)
    
    if adapter:
        success = await adapter.apply_configuration(honeypot_id, config.dict())
        if success:
            deception_api.active_honeypots[honeypot_id] = config
            return {"status": "configured", "honeypot_id": honeypot_id}
    
    raise HTTPException(status_code=500, detail="Configuration failed")


@app.post("/api/adapt")
async def request_adaptation(
    request: AdaptationRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_api_key)
):
    """Request adaptive configuration based on recent activity"""
    if request.honeypot_id not in deception_api.active_honeypots:
        raise HTTPException(status_code=404, detail="Honeypot not found")
    
    # Calculate adaptation score
    score = await adaptation_scorer.calculate_score(
        request.recent_activity,
        request.threat_level
    )
    
    # Get recommended configuration
    recommended_config = await policy_manager.get_adaptive_configuration(
        honeypot_id=request.honeypot_id,
        activity=request.recent_activity,
        strategy=request.adaptation_strategy,
        adaptation_score=score
    )
    
    # Store adaptation event
    adaptation_event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "honeypot_id": request.honeypot_id,
        "adaptation_score": score,
        "strategy": request.adaptation_strategy,
        "threat_level": request.threat_level,
        "recommended_config": recommended_config
    }
    deception_api.adaptation_history.append(adaptation_event)
    
    # Apply configuration in background
    background_tasks.add_task(
        _apply_adaptive_configuration,
        request.honeypot_id,
        recommended_config
    )
    
    return {
        "status": "adaptation_scheduled",
        "honeypot_id": request.honeypot_id,
        "adaptation_score": round(score, 2),
        "recommended_changes": recommended_config
    }


async def _apply_adaptive_configuration(honeypot_id: str, config: Dict[str, Any]):
    """Background task to apply adaptive configuration"""
    try:
        honeypot = deception_api.active_honeypots[honeypot_id]
        adapter = honeypot_adapters.get(honeypot.honeypot_type)
        
        if adapter:
            await adapter.apply_configuration(honeypot_id, config)
            logger.info(f"Applied adaptive configuration to {honeypot_id}")
    except Exception as e:
        logger.error(f"Failed to apply adaptive configuration: {e}")


@app.get("/api/strategies", response_model=List[DeceptionStrategy])
async def list_strategies():
    """List available deception strategies"""
    return [*deception_api.strategies.values()]  # Unpacking faster than list()


@app.get("/api/strategies/{strategy_id}", response_model=DeceptionStrategy)
async def get_strategy(strategy_id: str):
    """Get specific deception strategy"""
    if strategy_id not in deception_api.strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return deception_api.strategies[strategy_id]


@app.post("/api/strategies/{strategy_id}/apply")
async def apply_strategy(
    strategy_id: str,
    honeypot_id: str,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_api_key)
):
    """Apply deception strategy to honeypot"""
    if strategy_id not in deception_api.strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if honeypot_id not in deception_api.active_honeypots:
        raise HTTPException(status_code=404, detail="Honeypot not found")
    
    strategy = deception_api.strategies[strategy_id]
    
    # Apply strategy configuration in background
    background_tasks.add_task(
        _apply_adaptive_configuration,
        honeypot_id,
        strategy.configuration
    )
    
    return {
        "status": "strategy_applied",
        "strategy_id": strategy_id,
        "honeypot_id": honeypot_id,
        "target_techniques": strategy.target_techniques
    }


@app.post("/api/telemetry/ingest")
async def ingest_telemetry(events: List[TelemetryEvent], _: None = Depends(require_api_key)):
    """Ingest telemetry events for analysis"""
    # Process events for potential adaptations
    high_threat_events = [e for e in events if e.threat_score > 75]
    
    if high_threat_events:
        logger.warning(f"Received {len(high_threat_events)} high-threat events")
        # TODO: Trigger automatic adaptation
    
    return {
        "status": "ingested",
        "event_count": len(events),
        "high_threat_count": len(high_threat_events)
    }


@app.get("/api/metrics")
async def get_metrics():
    """Get deception engine metrics"""
    # Optimize: Use len() directly instead of list comprehension
    total_honeypots = len(deception_api.active_honeypots)
    
    # Optimize: Use generator expression for memory efficiency
    one_hour_ago = datetime.now(timezone.utc).timestamp() - 3600
    recent_count = sum(
        1 for a in deception_api.adaptation_history
        if datetime.fromisoformat(a['timestamp']).timestamp() > one_hour_ago
    )
    
    return {
        "total_honeypots": total_honeypots,
        "active_honeypots": total_honeypots,  # Simpler: all registered are active
        "total_adaptations": len(deception_api.adaptation_history),
        "recent_adaptations": recent_count,
        "available_strategies": len(deception_api.strategies),
        "adapters": [*honeypot_adapters]  # Unpacking faster than list()
    }


@app.get("/api/adaptation-history")
async def get_adaptation_history(limit: int = 100):
    """Get recent adaptation history"""
    return {
        "total_adaptations": len(deception_api.adaptation_history),
        "history": deception_api.adaptation_history[-limit:]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
