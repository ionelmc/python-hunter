cimport cython

import re
from functools import partial
from linecache import getline
from linecache import getlines
from tokenize import TokenError
from tokenize import generate_tokens

from .env import SITE_PACKAGES_PATH
from .env import SYS_PREFIX_PATHS
from ._tracer cimport *


cdef object LEADING_WHITESPACE_RE = re.compile('(^[ \t]*)(?:[^ \t\n])', re.MULTILINE)

@cython.final
cdef class Event:
    """
    Event wrapper for ``frame, kind, arg`` (the arguments the settrace function gets).

    Provides few convenience properties.
    """
    cdef:
        FrameType frame
        public str kind
        public object arg
        public Tracer tracer
        object _module
        object _filename

    def __cinit__(self, FrameType frame, str kind, object arg, Tracer tracer):
        self.frame = frame
        self.kind = kind
        self.arg = arg
        self.tracer = tracer
        self._module = None

    property locals:
        def __get__(self):
            """
            A dict with local variables.
            """
            return self.frame.f_locals

    property globals:
        def __get__(self):
            """
            A dict with global variables.
            """
            return self.frame.f_globals

    property function:
        def __get__(self):
            """
            A string with function name.
            """
            return self.code.co_name

    property module:
        """
        A string with module name (eg: ``"foo.bar"``).
        """
        def __get__(self):
            if self._module is None:
                module = self.frame.f_globals.get('__name__', '')
                if module is None:
                    module = ''

                self._module = module
            return self._module

    property filename:
        def __get__(self):
            """
            A string with absolute path to file.
            """
            if self._filename is None:
                filename = self.frame.f_globals.get('__file__', '')
                if filename is None:
                    filename = ''

                if filename.endswith(('.pyc', '.pyo')):
                    filename = filename[:-1]

                self._filename = filename
            return self._filename

    property lineno:
        def __get__(self):
            """
            An integer with line number in file.
            """
            return self.frame.f_lineno

    property code:
        def __get__(self):
            """
            A code object (not a string).
            """
            return self.frame.f_code

    property stdlib:
        def __get__(self):
            """
            A boolean flag. ``True`` if frame is in stdlib.
            """
            if self.filename.startswith(SITE_PACKAGES_PATH):
                # if it's in site-packages then its definitely not stdlib
                return False
            if self.filename.startswith(SYS_PREFIX_PATHS):
                return True

    property fullsource:
        def __get__(self):
            """
            A string with the sourcecode for the current statement (from ``linecache`` - failures are ignored).

            May include multiple lines if it's a class/function definition (will include decorators).
            """
            if self._fullsource is None:
                try:
                    self._fullsource = self._raw_fullsource
                except Exception as exc:
                    self._fullsource = "??? NO SOURCE: {!r}".format(exc)

            return self._fullsource

    property source:
        def __get__(self):
            """
            A string with the sourcecode for the current line (from ``linecache`` - failures are ignored).

            Fast but sometimes incomplete.
            """
            if self._source is None:
                try:
                    self._source = getline(self.filename, self.lineno)
                except Exception as exc:
                    self._source = "??? NO SOURCE: {!r}".format(exc)

            return self._source

    property _raw_fullsource:
        def __get__(self):
            cdef list lines

            if self.kind == 'call' and self.code.co_name != "<module>":
                lines = []
                try:
                    for _, token, _, _, line in generate_tokens(partial(
                        next,
                        yield_lines(self.filename, self.lineno - 1, lines)
                    )):
                        if token in ("def", "class", "lambda"):
                            return ''.join(lines)
                except TokenError:
                    pass

            return getline(self.filename, self.lineno)

    def __getitem__(self, item):
        return getattr(self, item)


def yield_lines(filename, start, list collector,
                limit=10):
    dedent = None
    amount = 0
    for line in getlines(filename)[start:start + limit]:
        if dedent is None:
            dedent = LEADING_WHITESPACE_RE.findall(line)
            dedent = dedent[0] if dedent else ""
            amount = len(dedent)
        elif not line.startswith(dedent):
            break
        collector.append(line)
        yield line[amount:]
