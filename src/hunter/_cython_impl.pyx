import os
from _csv import field_size_limit
from distutils.sysconfig import get_python_lib

cimport cython
import sys
from cpython cimport pystate

from .actions import CodePrinter
from .env import SITE_PACKAGES_PATH
from .env import SYS_PREFIX_PATHS


cdef extern from "frameobject.h":
    ctypedef struct PyObject

    ctypedef class types.CodeType[object PyCodeObject]:
        cdef object co_filename
        cdef int co_firstlineno

    ctypedef class types.FrameType[object PyFrameObject]:
        cdef CodeType f_code
        cdef PyObject *f_back
        cdef PyObject *f_trace
        cdef int f_lineno

    void PyEval_SetTrace(pystate.Py_tracefunc func, PyObject*obj)



cdef tuple kind_names = ("call", "exception", "line", "return", "c_call", "c_exception", "c_return")

cdef int trace_func(Tracer self, FrameType frame, int kind, object arg) except -1:
    frame.f_trace = <PyObject*> self;

    if self._handler is None:
        raise RuntimeError("Tracer is not started.")

    print('self._handler(Event', (frame, kind_names[kind], arg, self))

    if self._previous_tracer:
        self._previous_tracer(frame, kind, arg)

@cython.final
cdef class Tracer:
    """
    Tracer object.

    """
    cdef:
        public object _handler
        public object _previous_tracer

    def __cinit__(self):
        self._handler = None
        self._previous_tracer = None

    def __str__(self):
        return "Tracer(_handler={}, _previous_tracer={})".format(
            "<not started>" if self._handler is None else self._handler,
            self._previous_tracer,
        )

    def __call__(self, frame, kind, arg):
        """
        The settrace function.

        .. note::

            This always returns self (drills down) - as opposed to only drilling down when predicate(event) is True
            because it might
            match further inside.
        """
        trace_func(self, frame, kind_names.index(kind), arg)
        return self

    def trace(self, *predicates, **options):
        """
        Starts tracing. Can be used as a context manager (with slightly incorrect semantics - it starts tracing
        before ``__enter__`` is
        called).

        Args:
            predicates (:class:`hunter.Q` instances): Runs actions if any of the given predicates match.
            options: Keyword arguments that are passed to :class:`hunter.Q`, for convenience.
        """
        if "action" not in options and "actions" not in options:
            options["action"] = CodePrinter
        merge = options.pop("merge", True)
        clear_env_var = options.pop("clear_env_var", False)
        # predicate = Q(*predicates, **options)

        if clear_env_var:
            os.environ.pop("PYTHONHUNTER", None)

        previous_tracer = sys.gettrace()
        if previous_tracer is self:
            pass
            # if merge:
            #     self._handler |= predicate
        else:
            PyEval_SetTrace(<pystate.Py_tracefunc> trace_func, <PyObject*> self)

            self._previous_tracer = previous_tracer
            self._handler = True  #predicate
        return self

    def stop(self):
        """
        Stop tracing. Restores previous tracer (if any).
        """
        sys.settrace(self._previous_tracer)
        self._previous_tracer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

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
            try:
                return self._raw_fullsource
            except Exception as exc:
                return "??? NO SOURCE: {!r}".format(exc)

    def source(self, getline=linecache.getline):
        """
        A string with the sourcecode for the current line (from ``linecache`` - failures are ignored).

        Fast but sometimes incomplete.
        """
        try:
            return getline(self.filename, self.lineno)
        except Exception as exc:
            return "??? NO SOURCE: {!r}".format(exc)

    def _raw_fullsource(self, getlines=linecache.getlines, getline=linecache.getline):
        if self.kind == 'call' and self.code.co_name != "<module>":
            lines = []
            try:
                for _, token, _, _, line in tokenize.generate_tokens(partial(
                    next,
                    yield_lines(self.filename, self.lineno - 1, lines.append)
                )):
                    if token in ("def", "class", "lambda"):
                        return ''.join(lines)
            except tokenize.TokenError:
                pass

        return getline(self.filename, self.lineno)

    __getitem__ = object.__getattribute__
