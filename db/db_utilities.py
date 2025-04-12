import asyncio
from sqlite3 import OperationalError
from functools import wraps


def async_retry_on_lock(max_retries=5, delay=0.2):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e).lower():
                        await asyncio.sleep(delay * (2 ** attempt))  # exponential backoff
                    else:
                        raise
            raise OperationalError(f"Failed after {max_retries} retries due to database lock.")
        return wrapper
    return decorator
