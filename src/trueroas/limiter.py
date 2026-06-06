from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance to be used across all routers
limiter = Limiter(key_func=get_remote_address)
