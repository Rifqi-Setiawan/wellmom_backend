"""In-memory rate limiter for chatbot requests."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for MVP."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[int, list] = {}  # user_id -> list of timestamps
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, user_id: int) -> Tuple[bool, int]:
        """
        Check if user is allowed to make request.
        
        Args:
            user_id: User ID to check
        
        Returns:
            tuple: (is_allowed, seconds_until_reset)
        """
        async with self._lock:
            now = datetime.utcnow()
            cutoff_time = now - timedelta(seconds=self.window_seconds)
            
            # Get user's request history
            if user_id not in self._requests:
                self._requests[user_id] = []
            
            # Remove old requests outside the window
            user_requests = self._requests[user_id]
            user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff_time]
            
            # Check if under limit
            if len(user_requests) < self.max_requests:
                return (True, 0)
            
            # Calculate seconds until oldest request expires
            if user_requests:
                oldest_request = min(user_requests)
                seconds_until_reset = int((oldest_request + timedelta(seconds=self.window_seconds) - now).total_seconds())
                seconds_until_reset = max(0, seconds_until_reset)
            else:
                seconds_until_reset = 0
            
            return (False, seconds_until_reset)
    
    async def record_request(self, user_id: int):
        """Record a request for the user."""
        async with self._lock:
            now = datetime.utcnow()
            
            if user_id not in self._requests:
                self._requests[user_id] = []
            
            self._requests[user_id].append(now)
            
            # Clean up old entries periodically (keep last 100 requests per user)
            if len(self._requests[user_id]) > 100:
                cutoff_time = now - timedelta(seconds=self.window_seconds)
                self._requests[user_id] = [
                    req_time for req_time in self._requests[user_id]
                    if req_time > cutoff_time
                ]


# Singleton instance - will be initialized with settings
rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get or create rate limiter instance with settings."""
    global rate_limiter
    if rate_limiter is None:
        from app.config import settings
        rate_limiter = InMemoryRateLimiter(
            max_requests=settings.CHATBOT_RATE_LIMIT_PER_MINUTE,
            window_seconds=60
        )
    return rate_limiter
