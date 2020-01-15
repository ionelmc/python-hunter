class Default(object):
    def __init__(self, key, fallback_value):
        self.key = key
        self.fallback_value = fallback_value

    def resolve(self):
        from . import _default_config
        return _default_config.get(self.key, self.fallback_value)

    def __str__(self):
        return str(self.fallback_value)

    def __repr__(self):
        return repr(self.fallback_value)


def resolve(value):
    if isinstance(value, Default):
        return value.resolve()
    else:
        return value
