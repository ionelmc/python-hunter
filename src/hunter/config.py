import os
import sys

THREADING_SUPPORT_ALIASES = (
    "threading_support", "threads_support", "thread_support",
    "threadingsupport", "threadssupport", "threadsupport",
    "threading", "threads", "thread",
)

DEFAULTS = {}


def load_config(predicates, options):
    from . import Q, And, Or, Not, CallPrinter, CodePrinter, Debugger, VarsPrinter, When  # noqa
    try:
        config_predicates, config_options = eval("_prepare({})".format(os.environ.get("PYTHONHUNTERCONFIG", "")))
    except Exception as exc:
        sys.stderr.write("Failed to load hunter config from PYTHONHUNTERCONFIG {[PYTHONHUNTERCONFIG]!r}: {!r}\n".format(
            os.environ, exc))
        return predicates, options
    else:
        return predicates + tuple(config_predicates), dict(config_options, **options)


def _prepare(*args, **kwargs):
    from . import Q

    DEFAULTS.clear()
    DEFAULTS.update((key.lower(), val) for key, val in kwargs.items())
    options = {}
    predicates = []

    for key, value in list(DEFAULTS.items()):
        if key in THREADING_SUPPORT_ALIASES or key == 'clear_env_var':
            options[key] = DEFAULTS.pop(key)
            continue
        elif key in (
            # builtin actions config
            'klass',
            'stream',
            'force_colors',
            'force_pid',
            'filename_alignment',
            'thread_alignment',
            'pid_alignment',
            'repr_limit',
            'repr_unsafe',
            'globals',
        ):
            continue

        try:
            Q(**{key: value})
        except TypeError:
            pass
        else:
            options[key] = DEFAULTS.pop(key)
            continue

        DEFAULTS.pop(key)
        sys.stderr.write("Discarded config from PYTHONHUNTERCONFIG {}={!r}: Unknown option\n".format(
            key, value))
    for position, predicate in enumerate(args):
        if callable(predicate):
            predicates.append(predicate)
        else:
            sys.stderr.write("Discarded config from PYTHONHUNTERCONFIG {} (position {}): Not a callable\n".format(
                predicate, position))

    return predicates, options
