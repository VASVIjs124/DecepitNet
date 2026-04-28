"""
Example: Quick Start DECEPTINET Demo
This script demonstrates basic usage of the DECEPTINET platform
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from deceptinet.core.config import ConfigManager
from deceptinet.core.platform import DeceptiNetPlatform
from deceptinet.core.logger import setup_logger


async def main():
    """Main demo function"""
    logger = setup_logger('Demo', level='INFO')
    
    logger.info("=" * 60)
    logger.info("DECEPTINET Platform Demo")
    logger.info("=" * 60)
    
    # Load configuration
    logger.info("Loading configuration...")
    config = ConfigManager('config.yaml')
    
    # Create platform instance
    logger.info("Creating platform instance...")
    platform = DeceptiNetPlatform(config, mode='full')
    
    # Initialize platform
    logger.info("Starting DECEPTINET platform...")
    await platform.start()
    
    # Show status
    status = platform.get_status()
    logger.info(f"\nPlatform Status:")
    logger.info(f"  Mode: {status['mode']}")
    logger.info(f"  Running: {status['running']}")
    logger.info(f"  Components: {status['components']}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Platform is running. Press Ctrl+C to stop.")
    logger.info("=" * 60 + "\n")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(10)
            
            # Get and display statistics every 10 seconds
            if platform.system_monitor:
                metrics = await platform.system_monitor.get_metrics()
                logger.info(f"Interactions: {metrics.get('total_interactions', 0)} | "
                           f"Unique IPs: {metrics.get('unique_sources', 0)} | "
                           f"CPU: {metrics.get('cpu_percent', 0):.1f}%")
    
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
    
    finally:
        await platform.shutdown()
        logger.info("Platform stopped. Goodbye!")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
