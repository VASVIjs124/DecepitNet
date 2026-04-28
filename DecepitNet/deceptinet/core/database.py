"""
Database Manager for DECEPTINET
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json


class DatabaseManager:
    """Manages database operations"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database manager
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.db_type = config.get('type', 'sqlite')
        self.db_path = config.get('path', 'data/deceptinet.db')
        self.connection = None
    
    async def initialize(self) -> None:
        """Initialize database and create tables"""
        if self.db_type == 'sqlite':
            await self._initialize_sqlite()
        else:
            raise NotImplementedError(f"Database type {self.db_type} not yet implemented")
    
    async def _initialize_sqlite(self) -> None:
        """Initialize SQLite database"""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create connection
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        
        # Create tables
        await self._create_tables()
    
    async def _create_tables(self) -> None:
        """Create database tables"""
        cursor = self.connection.cursor()
        
        # Honeypot interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS honeypot_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source_ip TEXT NOT NULL,
                source_port INTEGER,
                destination_ip TEXT NOT NULL,
                destination_port INTEGER,
                protocol TEXT,
                service_type TEXT,
                interaction_type TEXT,
                payload TEXT,
                metadata TEXT,
                threat_level TEXT,
                session_id TEXT
            )
        """)
        
        # Attack patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attack_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                pattern_type TEXT NOT NULL,
                source_ip TEXT,
                target_service TEXT,
                attack_vector TEXT,
                signature TEXT,
                severity TEXT,
                indicators TEXT,
                mitre_tactic TEXT,
                mitre_technique TEXT
            )
        """)
        
        # Threat intelligence table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threat_intelligence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ioc_type TEXT NOT NULL,
                ioc_value TEXT NOT NULL,
                confidence REAL,
                severity TEXT,
                source TEXT,
                tags TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                occurrences INTEGER DEFAULT 1
            )
        """)
        
        # Red team simulation logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS redteam_simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                campaign_id TEXT NOT NULL,
                tactic TEXT,
                technique TEXT,
                target_ip TEXT,
                target_port INTEGER,
                success BOOLEAN,
                evasion_used BOOLEAN,
                detection_rate REAL,
                metadata TEXT
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_ip TEXT,
                description TEXT,
                indicators TEXT,
                acknowledged BOOLEAN DEFAULT FALSE,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at DATETIME
            )
        """)
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                source_ip TEXT,
                service_type TEXT,
                interactions_count INTEGER DEFAULT 0,
                data_collected TEXT
            )
        """)
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_honeypot_timestamp ON honeypot_interactions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_honeypot_source_ip ON honeypot_interactions(source_ip)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attacks_timestamp ON attack_patterns(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_threat_ioc ON threat_intelligence(ioc_value)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
        
        self.connection.commit()
    
    async def insert_interaction(self, data: Dict[str, Any]) -> int:
        """Insert honeypot interaction"""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO honeypot_interactions 
            (source_ip, source_port, destination_ip, destination_port, protocol, 
             service_type, interaction_type, payload, metadata, threat_level, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('source_ip'),
            data.get('source_port'),
            data.get('destination_ip'),
            data.get('destination_port'),
            data.get('protocol'),
            data.get('service_type'),
            data.get('interaction_type'),
            data.get('payload'),
            json.dumps(data.get('metadata', {})),
            data.get('threat_level'),
            data.get('session_id')
        ))
        self.connection.commit()
        return cursor.lastrowid
    
    async def insert_alert(self, data: Dict[str, Any]) -> int:
        """Insert alert"""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO alerts 
            (alert_type, severity, source_ip, description, indicators)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get('alert_type'),
            data.get('severity'),
            data.get('source_ip'),
            data.get('description'),
            json.dumps(data.get('indicators', []))
        ))
        self.connection.commit()
        return cursor.lastrowid
    
    async def get_recent_interactions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent honeypot interactions"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM honeypot_interactions 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    async def get_threat_statistics(self) -> Dict[str, Any]:
        """Get threat statistics"""
        cursor = self.connection.cursor()
        
        stats = {}
        
        # Total interactions
        cursor.execute("SELECT COUNT(*) as count FROM honeypot_interactions")
        stats['total_interactions'] = cursor.fetchone()['count']
        
        # Unique source IPs
        cursor.execute("SELECT COUNT(DISTINCT source_ip) as count FROM honeypot_interactions")
        stats['unique_sources'] = cursor.fetchone()['count']
        
        # Alerts by severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count 
            FROM alerts 
            GROUP BY severity
        """)
        stats['alerts_by_severity'] = {row['severity']: row['count'] for row in cursor.fetchall()}
        
        return stats
    
    async def close(self) -> None:
        """Close database connection"""
        if self.connection:
            self.connection.close()
