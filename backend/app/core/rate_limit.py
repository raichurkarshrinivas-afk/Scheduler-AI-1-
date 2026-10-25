import abc
import time
import threading
from collections import defaultdict
from typing import Tuple


class BaseRateLimiter(abc.ABC):
    """
    Abstract rate-limiting interface for API request throttling.
    
    Subclasses provide concrete persistence backends (e.g., local memory for
    single-node, or distributed Redis/KeyDB for multi-instance deployments).
    """

    @abc.abstractmethod
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int, int]:
        """
        Evaluates whether a request with the given key is permitted.
        
        Args:
            key: Unique identifier for the rate-limit bucket (e.g. "login:ip:identifier").
            max_requests: Maximum allowed attempts in the window.
            window_seconds: Duration of the sliding window in seconds.
            
        Returns:
            Tuple of:
                allowed (bool): True if request is under limit, False if throttled.
                remaining (int): Remaining requests allowed in current window.
                retry_after (int): Seconds until oldest request in window expires.
        """
        pass

    @abc.abstractmethod
    def reset(self, key: str) -> None:
        """Clears rate limit state for a key (e.g. upon successful authentication)."""
        pass


class InMemorySlidingWindowRateLimiter(BaseRateLimiter):
    """
    Thread-safe, sliding-window rate limiter implemented in process memory.

    ### Architecture & Multi-Instance Limitations:
    - **Single-Instance Deployment**: Fully thread-safe using a mutual exclusion lock (`threading.Lock`).
      Accurately meters requests with millisecond resolution without race conditions within a single process.
    - **Multi-Instance / Clustered Limitations**:
      This implementation stores attempt timestamps in the local Python process heap.
      In a multi-process (e.g. multi-worker Uvicorn `workers > 1`) or multi-container
      (e.g. Kubernetes, AWS ECS, multi-node Docker Compose) deployment behind a load balancer,
      rate-limit buckets are isolated per process. An attacker could rotate requests across workers
      or replicas without sharing state unless sticky sessions or a distributed Redis-backed
      implementation (`RedisRateLimiter`) is configured.
    """

    def __init__(self) -> None:
        self._buckets = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int, int]:
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Evict expired timestamps
            timestamps = [ts for ts in self._buckets[key] if ts > cutoff]
            self._buckets[key] = timestamps

            if len(timestamps) >= max_requests:
                oldest = timestamps[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                return False, 0, retry_after

            # Record current attempt
            timestamps.append(now)
            remaining = max_requests - len(timestamps)
            return True, remaining, 0

    def reset(self, key: str) -> None:
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]


# Global single-instance rate limiter
login_rate_limiter = InMemorySlidingWindowRateLimiter()
