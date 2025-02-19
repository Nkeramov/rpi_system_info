class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            # we have not every built an instance before, so build one now
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        else:
            instance = cls._instances[cls]
            # here we are going to call the __init__ and maybe reinitialize
            if hasattr(cls, '__allow_reinitialization') and cls.__allow_reinitialization:
                # if the class allows reinitialization, then do it
                instance.__init__(*args, **kwargs)
        return instance
