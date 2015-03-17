import sys
import os
import linecache

DEFAULT_MIN_FILENAME_ALIGNMENT = 15

def _safe_getline(filename, lineno, getline=linecache.getline):
    try:
        return getline(filename, lineno)
    except Exception as exc:
        return "??? no source: {} ???".format(exc)


def print_code(context, frame, kind, arg, stream=sys.stderr, basename=os.path.basename, min_filename_alignment=DEFAULT_MIN_FILENAME_ALIGNMENT):
    filename = frame.f_code.co_filename or "<???>"
    alignment = context.filename_alignment = max(getattr(context, 'filename_alignment', min_filename_alignment), len(filename))
    stream.write("{:>{align}}:{:<5} {:11} {}{}{}\n".format(
        basename(filename),
        frame.f_lineno,
        kind,
        _safe_getline(filename, frame.f_lineno).rstrip(),
        "  # => " if arg else "", arg or "",
        align=alignment
    ))
    return context


def print_vars(*predicates, min_filename_alignment=DEFAULT_MIN_FILENAME_ALIGNMENT):
    def vars_printer(context, frame, kind, arg)
        , stream=sys.stderr):
    alignment = getattr(context, 'filename_alignment', min_filename_alignment)
    stream.write("{:>{align}}       {:11} {} = {}\n".format(
        "",
        "vars",
        "  # => " if arg else "", arg or "",
        align=alignment
    ))


