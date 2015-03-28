# -*- encoding: utf-8 -*-
if __name__ == "__main__":
    import functools

    def deco(opt):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args):
                return func(*args)
            return wrapper
        return decorator

    @deco(1)
    @deco(2)
    @deco(3)
    def foo(*args):
        return args

    foo(
        'a',
        'b'
    )
    try:
        None(
            'a',
            'b'
        )  # doh!
    except:
        pass
