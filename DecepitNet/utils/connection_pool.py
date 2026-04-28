"""
Optimized Database Connection Pool
Time Complexity: O(1) for connection acquisition/release
Space Complexity: O(n) where n is pool size (bounded)
"""

import asyncio
import threading
from typing import Optional, Dict, Any, Callable
from collections import deque
from contextlib import asynccontextmanager, contextmanager
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Connection statistics for monitoring"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_acquisitions: int = 0
    total_releases: int = 0
    average_wait_time: float = 0.0
    peak_usage: int = 0
    errors: int = 0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OptimizedConnectionPool:
    """
    High-performance connection pool with:
    - O(1) connection acquisition/release using deque
    - Automatic connection recycling
    - Connection health checks
    - Dynamic pool sizing
    - Thread-safe operations
    """
    
    def __init__(
        self,
        create_connection_func: Callable[[], Any],
        min_size: int = 2,
        max_size: int = 10,
        max_idle_time: int = 300,  # 5 minutes
        max_lifetime: int = 3600,  # 1 hour
        health_check_interval: int = 60  # 1 minute
    ):
        """
        Initialize connection pool
        
        Args:
            create_connection_func: Function to create new connections
            min_size: Minimum number of connections to maintain
            max_size: Maximum number of connections allowed
            max_idle_time: Maximum time (seconds) a connection can be idle
            max_lifetime: Maximum lifetime (seconds) for a connection
            health_check_interval: Interval (seconds) for health checks
        """
        self.create_connection = create_connection_func
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.max_lifetime = max_lifetime
        self.health_check_interval = health_check_interval
        
        # Use deque for O(1) append/pop operations
        self._available: deque[Any] = deque()
        self._in_use: set[int] = set()
        
        # Thread-safety
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        
        # Connection metadata
        self._connection_metadata: Dict[int, Dict[str, Any]] = {}
        
        # Statistics
        self._stats = ConnectionStats()
        self._wait_times: deque[float] = deque(maxlen=1000)  # Last 1000 wait times
        
        # Initialize pool
        self._initialize_pool()
        
        # Start background maintenance
        self._maintenance_task = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._maintenance_task.start()
    
    def _initialize_pool(self) -> None:
        """
        Initialize pool with minimum connections
        Time Complexity: O(n) where n is min_size
        """
        with self._lock:
            for _ in range(self.min_size):
                try:
                    conn = self._create_new_connection()
                    self._available.append(conn)
                except Exception as e:
                    logger.error(f"Failed to create initial connection: {e}")
    
    def _create_new_connection(self) -> Any:
        """
        Create a new connection with metadata
        Time Complexity: O(1) + connection creation time
        """
        conn = self.create_connection()
        
        # Store metadata
        self._connection_metadata[id(conn)] = {
            "created_at": time.time(),
            "last_used": time.time(),
            "use_count": 0
        }
        
        self._stats.total_connections += 1
        return conn
    
    def acquire(self, timeout: Optional[float] = 30.0) -> Any:
        """
        Acquire a connection from the pool
        Time Complexity: O(1) average case
        
        Args:
            timeout: Maximum time to wait for a connection (seconds)
            
        Returns:
            Database connection
            
        Raises:
            TimeoutError: If no connection available within timeout
        """
        start_time = time.time()
        
        with self._condition:
            while True:
                # Try to get available connection (O(1))
                if self._available:
                    conn = self._available.popleft()
                    
                    # Validate connection
                    if self._is_connection_valid(conn):
                        self._mark_as_in_use(conn)
                        wait_time = time.time() - start_time
                        self._record_acquisition(wait_time)
                        return conn
                    else:
                        # Connection invalid, create new one
                        self._cleanup_connection(conn)
                        continue
                
                # Create new connection if under max size
                if self._total_connections() < self.max_size:
                    try:
                        conn = self._create_new_connection()
                        self._mark_as_in_use(conn)
                        wait_time = time.time() - start_time
                        self._record_acquisition(wait_time)
                        return conn
                    except Exception as e:
                        logger.error(f"Failed to create connection: {e}")
                        self._stats.errors += 1
                
                # Wait for connection to become available
                elapsed = time.time() - start_time
                if timeout and elapsed >= timeout:
                    raise TimeoutError(f"Failed to acquire connection within {timeout}s")
                
                remaining = timeout - elapsed if timeout else None
                self._condition.wait(timeout=remaining)
    
    def release(self, conn: Any) -> None:
        """
        Release a connection back to the pool
        Time Complexity: O(1)
        
        Args:
            conn: Connection to release
        """
        with self._lock:
            if id(conn) not in self._connection_metadata:
                logger.warning("Attempted to release unknown connection")
                return
            
            # Remove from in-use set (O(1))
            self._in_use.discard(id(conn))
            
            # Update metadata
            metadata = self._connection_metadata[id(conn)]
            metadata["last_used"] = time.time()
            metadata["use_count"] += 1
            
            # Return to available pool (O(1))
            self._available.append(conn)
            
            self._stats.total_releases += 1
            self._stats.active_connections = len(self._in_use)
            self._stats.idle_connections = len(self._available)
            
            # Notify waiting threads
            self._condition.notify()
    
    def _mark_as_in_use(self, conn: Any) -> None:
        """Mark connection as in use"""
        conn_id = id(conn)
        self._in_use.add(conn_id)
        
        # Update stats
        self._stats.active_connections = len(self._in_use)
        self._stats.idle_connections = len(self._available)
        if len(self._in_use) > self._stats.peak_usage:
            self._stats.peak_usage = len(self._in_use)
    
    def _record_acquisition(self, wait_time: float) -> None:
        """Record acquisition metrics"""
        self._stats.total_acquisitions += 1
        self._wait_times.append(wait_time)
        
        # Update average wait time (O(1) with rolling average)
        if self._wait_times:
            self._stats.average_wait_time = sum(self._wait_times) / len(self._wait_times)
    
    def _is_connection_valid(self, conn: Any) -> bool:
        """
        Check if connection is still valid
        Time Complexity: O(1)
        """
        conn_id = id(conn)
        if conn_id not in self._connection_metadata:
            return False
        
        metadata = self._connection_metadata[conn_id]
        current_time = time.time()
        
        # Check lifetime
        if current_time - metadata["created_at"] > self.max_lifetime:
            logger.debug(f"Connection exceeded max lifetime")
            return False
        
        # Check idle time
        if current_time - metadata["last_used"] > self.max_idle_time:
            logger.debug(f"Connection exceeded max idle time")
            return False
        
        return True
    
    def _cleanup_connection(self, conn: Any) -> None:
        """Clean up and close connection"""
        try:
            if hasattr(conn, 'close'):
                conn.close()
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
        finally:
            conn_id = id(conn)
            if conn_id in self._connection_metadata:
                del self._connection_metadata[conn_id]
            self._stats.total_connections -= 1
    
    def _total_connections(self) -> int:
        """Get total number of connections"""
        return len(self._available) + len(self._in_use)
    
    def _maintenance_loop(self) -> None:
        """
        Background maintenance task
        - Remove stale connections
        - Maintain minimum pool size
        - Health checks
        """
        while True:
            try:
                time.sleep(self.health_check_interval)
                self._perform_maintenance()
            except Exception as e:
                logger.error(f"Maintenance error: {e}")
    
    def _perform_maintenance(self) -> None:
        """Perform pool maintenance"""
        with self._lock:
            # Remove invalid idle connections
            valid_connections = deque()
            while self._available:
                conn = self._available.popleft()
                if self._is_connection_valid(conn):
                    valid_connections.append(conn)
                else:
                    self._cleanup_connection(conn)
            
            self._available = valid_connections
            
            # Ensure minimum pool size
            while len(self._available) < self.min_size:
                try:
                    conn = self._create_new_connection()
                    self._available.append(conn)
                except Exception as e:
                    logger.error(f"Failed to maintain minimum pool size: {e}")
                    break
    
    @contextmanager
    def connection(self, timeout: Optional[float] = 30.0):
        """
        Context manager for connection acquisition and release
        
        Usage:
            with pool.connection() as conn:
                # Use connection
                pass
        """
        conn = self.acquire(timeout=timeout)
        try:
            yield conn
        finally:
            self.release(conn)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                "total_connections": self._stats.total_connections,
                "active_connections": self._stats.active_connections,
                "idle_connections": self._stats.idle_connections,
                "total_acquisitions": self._stats.total_acquisitions,
                "total_releases": self._stats.total_releases,
                "average_wait_time_ms": round(self._stats.average_wait_time * 1000, 2),
                "peak_usage": self._stats.peak_usage,
                "errors": self._stats.errors,
                "uptime_seconds": (datetime.now(timezone.utc) - self._stats.last_reset).total_seconds()
            }
    
    def close(self) -> None:
        """Close all connections and shut down pool"""
        with self._lock:
            # Close available connections
            while self._available:
                conn = self._available.popleft()
                self._cleanup_connection(conn)
            
            logger.info("Connection pool closed")


# Async version for async applications
class AsyncConnectionPool:
    """
    Async version of connection pool
    Same O(1) complexity for operations
    """
    
    def __init__(
        self,
        create_connection_func,
        min_size: int = 2,
        max_size: int = 10,
        **kwargs
    ):
        self.create_connection = create_connection_func
        self.min_size = min_size
        self.max_size = max_size
        
        # Use asyncio data structures
        self._available: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._in_use: set = set()
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = ConnectionStats()
    
    async def initialize(self) -> None:
        """Initialize pool asynchronously"""
        for _ in range(self.min_size):
            try:
                conn = await self.create_connection()
                await self._available.put(conn)
                self._stats.total_connections += 1
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
    
    async def acquire(self, timeout: Optional[float] = 30.0) -> Any:
        """Acquire connection asynchronously"""
        start_time = time.time()
        
        try:
            # Try to get from queue (O(1))
            conn = await asyncio.wait_for(
                self._available.get(),
                timeout=timeout
            )
            
            async with self._lock:
                self._in_use.add(id(conn))
                self._stats.active_connections = len(self._in_use)
                self._stats.total_acquisitions += 1
            
            return conn
            
        except asyncio.TimeoutError:
            # Try to create new connection if under max
            async with self._lock:
                if self._stats.total_connections < self.max_size:
                    conn = await self.create_connection()
                    self._in_use.add(id(conn))
                    self._stats.total_connections += 1
                    self._stats.total_acquisitions += 1
                    return conn
            
            raise TimeoutError(f"Failed to acquire connection within {timeout}s")
    
    async def release(self, conn: Any) -> None:
        """Release connection back to pool"""
        async with self._lock:
            self._in_use.discard(id(conn))
            self._stats.active_connections = len(self._in_use)
            self._stats.total_releases += 1
        
        await self._available.put(conn)
    
    @asynccontextmanager
    async def connection(self, timeout: Optional[float] = 30.0):
        """Async context manager for connections"""
        conn = await self.acquire(timeout=timeout)
        try:
            yield conn
        finally:
            await self.release(conn)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            "total_connections": self._stats.total_connections,
            "active_connections": self._stats.active_connections,
            "idle_connections": self._available.qsize(),
            "total_acquisitions": self._stats.total_acquisitions,
            "total_releases": self._stats.total_releases
        }
