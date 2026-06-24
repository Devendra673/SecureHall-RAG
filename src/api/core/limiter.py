from slowapi import Limiter
from slowapi.util import get_remote_address

# Global rate limiter instance (no default limits, per-route limits applied explicitly)
limiter = Limiter(key_func=get_remote_address)
