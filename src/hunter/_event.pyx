# cython: linetrace=True, language_level=3str
from functools import partial
from linecache import getline
from linecache import getlines
from os.path import basename
from os.path import exists
from os.path import splitext
from threading import current_thread
from tokenize import TokenError
from tokenize import generate_tokens

from cpython.pythread cimport PyThread_get_thread_ident

from .const import SITE_PACKAGES_PATHS
from .const import SYS_PREFIX_PATHS
from .util import CYTHON_SUFFIX_RE
from .util import LEADING_WHITESPACE_RE
from .util import get_func_in_mro
from .util import get_main_thread
from .util import if_same_code

from ._tracer cimport Tracer

__all__ = 'Event',

cdef object UNSET = object()


cdef class Event:
    """
    A wrapper object for Frame objects. Instances of this are passed to your custom functions or predicates.

    Provides few convenience properties.

    Args:
        frame (Frame): A python `Frame <https://docs.python.org/3/reference/datamodel.html#frame-objects>`_ object.
        kind (str): A string like ``'call'``, ``'line'``, ``'return'`` or ``'exception'``.
        arg: A value that depends on ``kind``. Usually is ``None`` but for ``'return'`` or ``'exception'`` other values
            may be expected.
        tracer (:class:`hunter.tracer.Tracer`): The :class:`~hunter.tracer.Tracer` instance that created the event.
            Needed for the ``calls`` and ``depth`` fields.
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

    @property
    def threadid(self):
        cdef long current

        if self._threadidn is UNSET:
            current = PyThread_get_thread_ident()
            main = get_main_thread()
            if main is not None and current == main.ident:
                self._threadidn = None
            else:
                self._threadidn = current
        return self._threadidn

    @property
    def threadname(self):
        if self._threadname is UNSET:
            if self._thread is UNSET:
                self._thread = current_thread()
            self._threadname = self._thread.name
        return self._threadname

    @property
    def thread(self):
        if self._thread is UNSET:
            self._thread = current_thread()
        return self._thread

    @property
    def locals(self):
        return self._get_locals()

    cdef object _get_locals(self):
        PyFrame_FastToLocals(self.frame)
        return self.frame.f_locals

    @property
    def globals(self):
        return self._get_globals()

    cdef object _get_globals(self):
        return self.frame.f_globals

    @property
    def function(self):
        return self.frame.f_code.co_name

    @property
    def function_object(self):
        code = self.frame.f_code
        if code.co_name is None:
            return None
        # First, try to find the function in globals
        candidate = self.frame.f_globals.get(code.co_name, None)
        func = if_same_code(candidate, code)
        # If that failed, as will be the case with class and instance methods, try
        # to look up the function from the first argument. In the case of class/instance
        # methods, this should be the class (or an instance of the class) on which our
        # method is defined.
        if func is None and code.co_argcount >= 1:
            first_arg = self.frame.f_locals.get(code.co_varnames[0])
            func = get_func_in_mro(first_arg, code)
        # If we still can't find the function, as will be the case with static methods,
        # try looking at classes in global scope.
        if func is None:
            for v in self.frame.f_globals.values():
                if not isinstance(v, type):
                    continue
                func = get_func_in_mro(v, code)
                if func is not None:
                    break
        return func

    @property
    def module(self):
        if self._module is UNSET:
            module = self.frame.f_globals.get('__name__', '')
            if module is None:
                module = ''

            self._module = module
        return self._module

    @property
    def filename(self):
        if self._filename is UNSET:
            filename = self.frame.f_code.co_filename
            if not filename:
                filename = self.frame.f_globals.get('__file__')
            if not filename:
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

    @property
    def lineno(self):
        if self._lineno is UNSET:
            self._lineno = self.frame.f_lineno
        return self._lineno

    @property
    def code(self):
        return self.frame.f_code

    @property
    def stdlib(self):
        if self._stdlib is UNSET:
            module_parts = self.module.split('.')
            if 'pkg_resources' in module_parts:
                self._stdlib = True
            elif self.filename == '<frozen importlib._bootstrap>':
                self._stdlib = True
            elif self.filename.startswith(SITE_PACKAGES_PATHS):
                # if it's in site-packages then its definitely not stdlib
                self._stdlib = False
            elif self.filename.startswith(SYS_PREFIX_PATHS):
                self._stdlib = True
            else:
                self._stdlib = False
        return self._stdlib

    @property
    def fullsource(self):
        if self._fullsource is UNSET:
            try:
                self._fullsource = self._raw_fullsource
            except Exception as exc:
                self._fullsource = "??? NO SOURCE: {!r}".format(exc)

        return self._fullsource

    @property
    def source(self):
        if self._source is UNSET:
            if self.filename.endswith(('.so', '.pyd')):
                self._source = "??? NO SOURCE: not reading {} file".format(splitext(basename(self.filename))[1])
            try:
                self._source = getline(self.filename, self.lineno, self.frame.f_globals)
            except Exception as exc:
                self._source = "??? NO SOURCE: {!r}".format(exc)

        return self._source

    @property
    def _raw_fullsource(self):
        cdef list lines

        if self.kind == 'call' and self.code.co_name != "<module>":
            lines = []
            try:
                for _, token, _, _, line in generate_tokens(partial(
                    next,
                    yield_lines(self.filename, self.frame.f_globals, self.lineno - 1, lines)
                )):
                    if token in ("def", "class", "lambda"):
                        return ''.join(lines)
            except TokenError:
                pass

        return getline(self.filename, self.lineno, self.frame.f_globals)

    def __getitem__(self, item):
        return getattr(self, item)


def yield_lines(filename, module_globals, start, list collector,
                limit=10):
    dedent = None
    amount = 0
    for line in getlines(filename, module_globals)[start:start + limit]:
        if dedent is None:
            dedent = LEADING_WHITESPACE_RE.findall(line)
            dedent = dedent[0] if dedent else ""
            amount = len(dedent)
        elif not line.startswith(dedent):
            break
        collector.append(line)
        yield line[amount:]
