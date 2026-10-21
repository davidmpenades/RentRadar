from collections.abc import Callable

from django.db import OperationalError


def wait_until_available(
    check: Callable[[], object],
    clock: Callable[[], float],
    sleep: Callable[[float], object],
    timeout: float = 60.0,
    interval: float = 1.0,
) -> bool:
    deadline = clock() + timeout
    while True:
        try:
            check()
        except OperationalError:
            # No se conserva la excepción: su texto puede incluir host y usuario
            pass
        else:
            return True
        if clock() >= deadline:
            return False
        sleep(interval)
