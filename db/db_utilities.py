import asyncio
import functools
import sqlite3


def async_retry_on_lock(max_retries=5, delay=0.2):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e).lower():
                        if attempt < max_retries - 1:
                            await asyncio.sleep(delay * (2 ** attempt))
                        else:
                            raise sqlite3.OperationalError(
                                f"{func.__name__} failed after {max_retries} retries due to database lock."
                            )
                    else:
                        raise
        return wrapper
    return decorator
