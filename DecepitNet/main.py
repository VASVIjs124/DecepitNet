#!/usr/bin/env python3
# pyright: reportUnusedFunction=false
"""
DECEPTINET: Autonomous Cyber Deception and Red Team Simulation Platform
Main entry point for the platform
"""

import argparse
import asyncio
import hmac
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from types import FrameType


class BackendRuntimeController:
    """Runtime controller for API-managed platform lifecycle."""

    def __init__(self, args: argparse.Namespace, logger: logging.Logger, cli: "DeceptiNetCLI"):
        self.args = args
        self.logger = logger
        self.cli = cli
        self.config_manager: Any = None
        self.platform: Any = None
        self.started_at = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Load configuration and optionally start the platform."""
        if self.config_manager is None:
            self.config_manager = self.cli.create_config_manager(self.args.config)
            self.cli.apply_cli_overrides(self.config_manager, self.args)

        if self.args.api_autostart:
            await self.start()

    async def start(self) -> Dict[str, Any]:
        """Start platform components if they are not already running."""
        async with self._lock:
            if self.config_manager is None:
                await self.initialize()

            if self.platform and getattr(self.platform, 'running', False):
                return {
                    'status': 'already_running',
                    'running': True
                }

            self.platform = self.cli.create_platform(self.config_manager, self.args.mode)
            await self.platform.start()

            if self.args.dashboard or self.config_manager.get('monitoring.dashboard.enabled'):
                dashboard_port: int = self.args.port or self.config_manager.get('monitoring.dashboard.port', 5000)
                await self.platform.start_dashboard(port=dashboard_port)

            self.logger.info("Platform started from backend API")
            return {
                'status': 'started',
                'running': True,
                'mode': self.args.mode
            }

    async def stop(self) -> Dict[str, Any]:
        """Stop platform components."""
        async with self._lock:
            if not self.platform:
                return {
                    'status': 'already_stopped',
                    'running': False
                }

            await self.platform.shutdown()
            self.platform = None

            self.logger.info("Platform stopped from backend API")
            return {
                'status': 'stopped',
                'running': False
            }

    async def restart(self) -> Dict[str, Any]:
        """Restart platform components."""
        await self.stop()
        return await self.start()

    def status(self) -> Dict[str, Any]:
        """Return runtime status."""
        if self.platform:
            return self.platform.get_status()

        uptime = int((datetime.now(timezone.utc) - self.started_at).total_seconds())
        return {
            'running': False,
            'mode': self.args.mode,
            'uptime_seconds': uptime,
            'start_time': None,
            'active_honeypots': 0,
            'total_interactions': 0,
            'unique_sources': 0,
            'threats_detected': 0,
            'components': {
                'honeypots': False,
                'redteam': False,
                'evasion': False,
                'intelligence': False,
                'monitoring': False,
                'deception': False,
                'dashboard': False
            }
        }

    def readiness(self) -> Dict[str, Any]:
        """Readiness details for health probes."""
        return {
            'ready': self.config_manager is not None,
            'config_loaded': self.config_manager is not None,
            'platform_running': bool(self.platform and getattr(self.platform, 'running', False))
        }


class DeceptiNetCLI:
    """Command-line interface for DECEPTINET platform"""

    def __init__(self):
        self.platform: Any = None
        self.logger = self._create_logger()

    @staticmethod
    def _create_logger() -> logging.Logger:
        """Create logger with graceful fallback if custom logger cannot load."""
        try:
            from deceptinet.core.logger import setup_logger
            return setup_logger(__name__)
        except Exception:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            )
            return logging.getLogger('DeceptiNetCLI')

    @staticmethod
    def _load_config_manager_class() -> Any:
        from deceptinet.core.config import ConfigManager
        return ConfigManager

    @staticmethod
    def _load_platform_class() -> Any:
        from deceptinet.core.platform import DeceptiNetPlatform
        return DeceptiNetPlatform

    @staticmethod
    def _load_database_manager_class() -> Any:
        from deceptinet.core.database import DatabaseManager
        return DatabaseManager

    @staticmethod
    def _load_model_manager_class() -> Any:
        from deceptinet.ml_models.model_manager import ModelManager
        return ModelManager

    def _create_config_manager(self, config_path: str) -> Any:
        config_cls = self._load_config_manager_class()
        resolved_config = self._resolve_config_path(config_path)
        return config_cls(resolved_config)

    def create_config_manager(self, config_path: str) -> Any:
        return self._create_config_manager(config_path)

    @staticmethod
    def _resolve_config_path(config_path: str) -> str:
        """Resolve config path from cwd and script directory for robust startup."""
        candidate = Path(config_path)

        if candidate.exists():
            return str(candidate)

        cwd_candidate = Path.cwd() / candidate
        if cwd_candidate.exists():
            return str(cwd_candidate)

        script_candidate = Path(__file__).resolve().parent / candidate
        if script_candidate.exists():
            return str(script_candidate)

        return str(candidate)

    def _create_platform(self, config_manager: Any, mode: str) -> Any:
        platform_cls = self._load_platform_class()
        return platform_cls(config_manager, mode=mode)

    def create_platform(self, config_manager: Any, mode: str) -> Any:
        return self._create_platform(config_manager, mode)

    def _print_banner(self) -> None:
        try:
            from deceptinet.utils.banner import print_banner
            print_banner()
        except Exception:
            self.logger.info("DECEPTINET platform startup")

    def _validate_environment(self) -> bool:
        try:
            from deceptinet.utils.validators import validate_environment
            return bool(validate_environment())
        except Exception as exc:
            self.logger.warning("Environment validation skipped: %s", exc)
            return True

    def _apply_cli_overrides(self, config_manager: Any, args: argparse.Namespace) -> None:
        """Apply CLI overrides to in-memory configuration."""
        if args.verbose:
            config_manager.set('monitoring.logging.level', 'DEBUG')

        if args.debug:
            config_manager.set('advanced.debug_mode', True)

        if args.interface:
            config_manager.set('network.interface', args.interface)

        if args.no_ai:
            config_manager.set('redteam.ai_agent.enabled', False)
            config_manager.set('evasion.ai_driven.enabled', False)

    def apply_cli_overrides(self, config_manager: Any, args: argparse.Namespace) -> None:
        self._apply_cli_overrides(config_manager, args)

    def parse_arguments(self):
        """Parse command-line arguments"""
        parser = argparse.ArgumentParser(
            description='DECEPTINET: Autonomous Cyber Deception Platform',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s --mode full                    # Start full platform
  %(prog)s --mode honeypot                # Honeypots only
  %(prog)s --mode redteam                 # Red team simulation only
    %(prog)s --mode ml                      # ML model manager only
  %(prog)s --dashboard                    # Start with web dashboard
  %(prog)s --init                         # Initialize platform
  %(prog)s --config custom_config.yaml   # Use custom config
            """
        )
        
        parser.add_argument(
            '--mode',
            choices=['full', 'honeypot', 'redteam', 'analysis', 'evasion', 'ml'],
            default='full',
            help='Platform operation mode'
        )
        
        parser.add_argument(
            '--config',
            type=str,
            default='config.yaml',
            help='Path to configuration file'
        )
        
        parser.add_argument(
            '--dashboard',
            action='store_true',
            help='Enable web dashboard'
        )
        
        parser.add_argument(
            '--init',
            action='store_true',
            help='Initialize platform (create directories, databases, etc.)'
        )
        
        parser.add_argument(
            '--verbose',
            '-v',
            action='store_true',
            help='Enable verbose output'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode'
        )
        
        parser.add_argument(
            '--port',
            type=int,
            help='Dashboard port (default: from config)'
        )
        
        parser.add_argument(
            '--interface',
            type=str,
            help='Network interface to use'
        )
        
        parser.add_argument(
            '--no-ai',
            action='store_true',
            help='Disable AI/ML features'
        )

        parser.add_argument(
            '--backend-api',
            action='store_true',
            help='Run backend REST API for platform lifecycle management'
        )

        parser.add_argument(
            '--api-host',
            type=str,
            default='0.0.0.0',
            help='Backend API host address'
        )

        parser.add_argument(
            '--api-port',
            type=int,
            default=9000,
            help='Backend API port'
        )

        parser.add_argument(
            '--api-autostart',
            action='store_true',
            help='Auto-start platform when backend API starts'
        )
        
        return parser.parse_args()

    async def initialize_platform(self, config_path: str):
        """Initialize the DECEPTINET platform"""
        self.logger.info("Initializing DECEPTINET platform...")

        # Create necessary directories
        directories = [
            'data',
            'logs',
            'models',
            'templates',
            'reports',
            'dumps',
            'cache'
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
            self.logger.info(f"Created directory: {directory}")

        # Load configuration
        config_manager = self._create_config_manager(config_path)

        # Create database tables
        database_manager_cls = self._load_database_manager_class()
        db_manager = database_manager_cls(config_manager.get('database'))
        await db_manager.initialize()
        self.logger.info("Database initialized")

        # Download/initialize ML models
        model_manager_cls = self._load_model_manager_class()
        model_manager = model_manager_cls()
        await model_manager.initialize_models()
        self.logger.info("ML models initialized")

        self.logger.info("Platform initialization complete!")
        return True

    async def start_platform(self, args: argparse.Namespace) -> int:
        """Start the DECEPTINET platform"""
        try:
            if args.mode == 'ml':
                return await self.start_ml_mode(args)

            # Load configuration
            config_manager = self._create_config_manager(args.config)
            self.apply_cli_overrides(config_manager, args)

            # Initialize platform
            self.platform = self.create_platform(config_manager, mode=args.mode)

            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            # Start the platform
            await self.platform.start()

            # Start dashboard if requested
            if args.dashboard or config_manager.get('monitoring.dashboard.enabled'):
                dashboard_port: int = args.port or config_manager.get('monitoring.dashboard.port', 5000)
                await self.platform.start_dashboard(port=dashboard_port)

            # Keep running
            await self.platform.run_forever()

        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Platform error: {e}", exc_info=True)
            return 1
        finally:
            if self.platform:
                await self.platform.shutdown()

        return 0

    async def start_ml_mode(self, args: argparse.Namespace) -> int:
        """Run dedicated ML inference pipeline mode."""
        try:
            from ml.kafka_consumer import MLKafkaConsumer
        except Exception as exc:
            self.logger.error("ML mode dependencies are missing: %s", exc)
            return 1

        try:
            config_manager = self._create_config_manager(args.config)

            consumer = MLKafkaConsumer(
                kafka_bootstrap_servers=config_manager.get('kafka.bootstrap_servers', 'localhost:9092'),
                topic=config_manager.get('kafka.topics.honeypot_events', 'honeypot-events'),
                group_id=config_manager.get('kafka.group_id', 'ml-inference-group'),
                models_dir=Path(config_manager.get('ml_models.models_dir', 'models')),
                batch_size=config_manager.get('ml.inference.batch_size', 200),
                batch_timeout=config_manager.get('ml.inference.batch_timeout', 3.0),
                max_parallel_tasks=config_manager.get('ml.inference.max_parallel_tasks', 10)
            )

            self.logger.info("Starting dedicated ML mode pipeline")
            await consumer.start()
            return 0

        except KeyboardInterrupt:
            self.logger.info("ML mode interrupted by user")
            return 0
        except Exception as exc:
            self.logger.error("ML mode pipeline error: %s", exc, exc_info=True)
            return 1

    async def run_backend_api(self, args: argparse.Namespace) -> int:
        """Run backend API server for platform lifecycle operations."""
        try:
            from contextlib import asynccontextmanager
            from fastapi import Depends, FastAPI, Header, HTTPException
            from fastapi.middleware.cors import CORSMiddleware
            import uvicorn
        except Exception as exc:
            self.logger.error("Backend API dependencies are missing: %s", exc)
            return 1

        runtime = BackendRuntimeController(args=args, logger=self.logger, cli=self)

        @asynccontextmanager
        async def app_lifespan(_: FastAPI):
            await runtime.initialize()
            try:
                yield
            finally:
                await runtime.stop()

        app = FastAPI(
            title='DECEPTINET Backend API',
            description='Control plane API for DECEPTINET platform lifecycle',
            version='1.0.0',
            lifespan=app_lifespan
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=['*'],
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*']
        )

        def _get_configured_api_key() -> str:
            if runtime.config_manager is None:
                return ''
            return str(runtime.config_manager.get('security.api_key', '') or '')

        async def require_api_key(
            x_api_key: Optional[str] = Header(default=None, alias='X-API-Key'),
            authorization: Optional[str] = Header(default=None, alias='Authorization')
        ) -> None:
            configured_api_key = _get_configured_api_key()
            if not configured_api_key:
                raise HTTPException(status_code=503, detail='Control API key is not configured')

            provided = x_api_key
            if not provided and authorization and authorization.lower().startswith('bearer '):
                provided = authorization.split(' ', 1)[1].strip()

            if not provided or not hmac.compare_digest(str(provided), configured_api_key):
                raise HTTPException(status_code=401, detail='Invalid API key')

        # Mount deception engine API if available.
        deception_engine_mounted = False
        try:
            from deception_engine.api import app as deception_engine_app
            app.mount('/deception-engine', deception_engine_app)
            deception_engine_mounted = True
        except Exception as exc:
            self.logger.warning("Deception engine API not mounted: %s", exc)

        @app.get('/')
        async def root() -> Dict[str, Any]:
            return {
                'service': 'DECEPTINET Backend API',
                'status': 'online',
                'api_docs': '/docs',
                'deception_engine_mounted': deception_engine_mounted
            }

        @app.get('/health')
        async def health() -> Dict[str, Any]:
            return {
                'status': 'alive',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        @app.get('/ready')
        async def readiness() -> Dict[str, Any]:
            return runtime.readiness()

        @app.get('/api/platform/status')
        async def platform_status(_: None = Depends(require_api_key)) -> Dict[str, Any]:
            return runtime.status()

        @app.post('/api/platform/start')
        async def platform_start(_: None = Depends(require_api_key)) -> Dict[str, Any]:
            try:
                return await runtime.start()
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        @app.post('/api/platform/stop')
        async def platform_stop(_: None = Depends(require_api_key)) -> Dict[str, Any]:
            try:
                return await runtime.stop()
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        @app.post('/api/platform/restart')
        async def platform_restart(_: None = Depends(require_api_key)) -> Dict[str, Any]:
            try:
                return await runtime.restart()
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        @app.get('/api/platform/config')
        async def platform_config(_: None = Depends(require_api_key)) -> Dict[str, Any]:
            if runtime.config_manager is None:
                return {'loaded': False, 'config': {}}

            return {
                'loaded': True,
                'config': runtime.config_manager.config
            }

        config = uvicorn.Config(
            app=app,
            host=args.api_host,
            port=args.api_port,
            log_level='debug' if args.debug else 'info'
        )
        server = uvicorn.Server(config)
        await server.serve()
        return 0

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}")
        if self.platform:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.platform.shutdown())
            except RuntimeError:
                self.logger.warning("No running event loop available for graceful shutdown")

    async def run(self) -> int:
        """Main run method"""
        args = self.parse_arguments()

        # Print banner
        self._print_banner()

        # Validate environment
        if not self._validate_environment():
            self.logger.error("Environment validation failed")
            return 1

        # Initialize if requested
        if args.init:
            await self.initialize_platform(args.config)
            return 0

        # Start backend API if requested
        if args.backend_api:
            return await self.run_backend_api(args)

        # Start platform
        return await self.start_platform(args)


def main():
    """Entry point"""
    cli = DeceptiNetCLI()

    try:
        exit_code = asyncio.run(cli.run())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
