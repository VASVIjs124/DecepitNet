"""
Web Dashboard for DECEPTINET
"""

import asyncio
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from threading import Thread

from ..core.logger import setup_logger


class Dashboard:
    """Web dashboard for monitoring"""
    
    def __init__(self, config, platform, port=5000):
        self.config = config
        self.platform = platform
        self.port = port
        self.logger = setup_logger('Dashboard')
        
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>DECEPTINET Dashboard</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
                    .header { background: #2a2a2a; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
                    .stat-card { background: #2a2a2a; padding: 20px; border-radius: 5px; border-left: 4px solid #00ff00; }
                    .stat-value { font-size: 32px; font-weight: bold; color: #00ff00; }
                    .stat-label { color: #888; margin-top: 5px; }
                    h1 { margin: 0; color: #00ff00; }
                    .subtitle { color: #888; margin-top: 5px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🛡️ DECEPTINET</h1>
                    <div class="subtitle">Autonomous Cyber Deception Platform</div>
                </div>
                <div id="stats" class="stats"></div>
                
                <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
                <script>
                    const socket = io();
                    
                    function updateStats(data) {
                        document.getElementById('stats').innerHTML = `
                            <div class="stat-card">
                                <div class="stat-value">${data.total_interactions || 0}</div>
                                <div class="stat-label">Total Interactions</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${data.unique_sources || 0}</div>
                                <div class="stat-label">Unique Sources</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${data.uptime_seconds || 0}s</div>
                                <div class="stat-label">Uptime</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${data.mode || 'N/A'}</div>
                                <div class="stat-label">Mode</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${data.active_honeypots || 0}</div>
                                <div class="stat-label">Active Honeypots</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${data.threats_detected || 0}</div>
                                <div class="stat-label">Threats Detected</div>
                            </div>
                        `;
                    }
                    
                    socket.on('stats_update', updateStats);
                    
                    // Initial load and periodic updates
                    function fetchStats() {
                        fetch('/api/stats')
                            .then(r => r.json())
                            .then(data => {
                                updateStats(data);
                            })
                            .catch(err => console.error('Error fetching stats:', err));
                    }
                    
                    fetchStats(); // Load immediately
                    setInterval(fetchStats, 5000); // Update every 5 seconds
                </script>
            </body>
            </html>
            """
        
        @self.app.route('/api/stats')
        def api_stats():
            status = self.platform.get_status()
            return jsonify(status)
    
    async def start(self):
        """Start dashboard"""
        def run_flask():
            self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        
        thread = Thread(target=run_flask, daemon=True)
        thread.start()
        
        self.logger.info(f"Dashboard started at http://0.0.0.0:{self.port}")
    
    async def stop(self):
        """Stop dashboard"""
        self.logger.info("Dashboard stopped")
