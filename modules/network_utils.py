import time
import logging
from functools import wraps

def retry(exceptions, tries=3, delay=5, backoff=2, logger=None):
    """
    Decorator do ponawiania próby wykonania funkcji w przypadku wystąpienia określonych wyjątków.

    :param exceptions: Krotka wyjątków, które mają być przechwytywane.
    :param tries: Maksymalna liczba prób.
    :param delay: Początkowe opóźnienie między próbami w sekundach.
    :param backoff: Mnożnik opóźnienia po każdej kolejnej próbie.
    :param logger: Logger do zapisywania informacji o ponowieniu próby.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(f"Błąd w '{func.__name__}': {e}. Ponawiam próbę za {mdelay}s... ({tries - mtries + 1}/{tries})")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return func(*args, **kwargs) # Ostatnia próba
        return wrapper
    return decorator
