import threading


class Singleton(type):
    _instances: dict = {}
    _lock: threading.RLock = threading.RLock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                # Build the first instance of the class
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            else:
                # An instance of the class already exists
                instance = cls._instances[cls]
                # Here we are going to call the __init__ and maybe reinitialize
                if hasattr(cls, '__allow_reinitialization') and cls.__allow_reinitialization:
                    # If the class allows reinitialization, then do it
                    instance.__init__(*args, **kwargs)
        return instance