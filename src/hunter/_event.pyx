# cython: linetrace=True
import re
import weakref
from functools import partial
from linecache import getline
from linecache import getlines
from os.path import exists
from threading import current_thread
from tokenize import TokenError
from tokenize import generate_tokens

from cpython.pythread cimport PyThread_get_thread_ident

from .const import SITE_PACKAGES_PATHS
from .const import SYS_PREFIX_PATHS
from .event import CYTHON_SUFFIX_RE
from .event import LEADING_WHITESPACE_RE
from ._tracer cimport *

try:
    from threading import main_thread
except ImportError:
    from threading import _shutdown
    get_main_thread = weakref.ref(
        _shutdown.__self__ if hasattr(_shutdown, '__self__') else _shutdown.im_self)
    del _shutdown
else:
    get_main_thread = weakref.ref(main_thread())


cdef object UNSET = object()

cdef class Event:
    """
    Event wrapper for ``frame, kind, arg`` (the arguments the settrace function gets). This objects is passed to your
    custom functions or predicates.

    Provides few convenience properties.

    .. warning::

        **Users do not instantiate this directly.**
    """
    def __cinit__(self, FrameType frame, str kind, object arg, Tracer tracer):
        self.arg = arg
        self.frame = frame
        self.kind = kind
        self.depth = tracer.depth
        self.calls = tracer.calls
        self.tracer = tracer

        self._filename = UNSET
        self._fullsource = UNSET
        self._lineno = UNSET
        self._module = UNSET
        self._source = UNSET
        self._stdlib = UNSET
        self._thread = UNSET
        self._threadidn = UNSET
        self._threadname = UNSET

    property threadid:
        def __get__(self):
            """
            Current thread ident. If current thread is main thread then it returns ``None``.
            """
            cdef long current

            if self._threadidn is UNSET:
                current = PyThread_get_thread_ident()
                main = get_main_thread()
                if main is not None and current == main.ident:
                    self._threadidn = None
                else:
                    self._threadidn = current
            return self._threadidn

    property threadname:
        def __get__(self):
            """
            Current thread name.
            """
            if self._threadname is UNSET:
                if self._thread is UNSET:
                    self._thread = current_thread()
                self._threadname = self._thread.name
            return self._threadname

    property thread:
        def __get__(self):
            """
            Current thread object.
            """
            if self._thread is UNSET:
                self._thread = current_thread()
            return self._thread


    property locals:
        def __get__(self):
            """
            A dict with local variables.
            """
            return self._get_locals()

    cdef object _get_locals(self):
        PyFrame_FastToLocals(self.frame)
        return self.frame.f_locals

    property globals:
        def __get__(self):
            """
            A dict with global variables.
            """
            return self._get_globals()

    cdef object _get_globals(self):
        return self.frame.f_globals

    property function:
        def __get__(self):
            """
            A string with function name.
            """
            return self.frame.f_code.co_name

    property module:
        """
        A string with module name (eg: ``"foo.bar"``).
        """
        def __get__(self):
            if self._module is UNSET:
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
            if self._filename is UNSET:
                filename = self.frame.f_globals.get('__file__', '')
                if filename is None:
                    filename = ''
                elif filename.endswith(('.pyc', '.pyo')):
                    filename = filename[:-1]
                elif filename.endswith(('.so', '.pyd')):
                    basename = CYTHON_SUFFIX_RE.sub('', filename)
                    for ext in ('.pyx', '.py'):
                        cyfilename = basename + ext
                        if exists(cyfilename):
                            filename = cyfilename
                            break

                self._filename = filename
            return self._filename

    property lineno:
        def __get__(self):
            """
            An integer with line number in file.
            """
            if self._lineno is UNSET:
                self._lineno = self.frame.f_lineno
            return self._lineno

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
            if self._stdlib is UNSET:
                if self.filename.startswith(SITE_PACKAGES_PATHS):
                    # if it's in site-packages then its definitely not stdlib
                    self._stdlib = False
                elif self.filename.startswith(SYS_PREFIX_PATHS):
                    self._stdlib = True
                else:
                    self._stdlib = False
            return self._stdlib

    property fullsource:
        def __get__(self):
            """
            A string with the sourcecode for the current statement (from ``linecache`` - failures are ignored).

            May include multiple lines if it's a class/function definition (will include decorators).
            """
            if self._fullsource is UNSET:
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
            if self._source is UNSET:
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
