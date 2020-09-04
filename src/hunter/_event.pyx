# cython: linetrace=True, language_level=3str, c_string_encoding=ascii
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
from cpython.ref cimport Py_XINCREF
from cpython.ref cimport PyObject
from libc.stdlib cimport malloc

from ._tracer cimport Tracer
from .vendor._cymem.cymem cimport Pool

from .const import SITE_PACKAGES_PATHS
from .const import SYS_PREFIX_PATHS
from .util import CYTHON_SUFFIX_RE
from .util import LEADING_WHITESPACE_RE
from .util import MISSING
from .util import get_func_in_mro
from .util import get_main_thread
from .util import if_same_code

__all__ = 'Event',

cdef object UNSET = object()

cdef Pool mem = Pool()
cdef PyObject** KIND_NAMES = make_kind_names(['call', 'exception', 'line', 'return', 'call', 'exception', 'return'])

cdef PyObject** make_kind_names(list strings):
    cdef PyObject** array = <PyObject**>mem.alloc(len(strings), sizeof(PyObject*))
    cdef object name
    for i, string in enumerate(strings):
        name = intern(string)
        Py_XINCREF(<PyObject*>name)
        array[i] = <PyObject*>name
    return <PyObject**>array


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
    def __init__(self, FrameType frame, int kind, object arg, Tracer tracer=None, object depth=None, object calls=None,
                 object threading_support=MISSING):
        if tracer is None:
            if depth is None:
                raise TypeError('Missing argument: depth (required because tracer was not given).')
            if calls is None:
                raise TypeError('Missing argument: calls (required because tracer was not given).')
            if threading_support is MISSING:
                raise TypeError('Missing argument: threading_support (required because tracer was not given).')
        else:
            depth = tracer.depth
            calls = tracer.calls
            threading_support = tracer.threading_support

        self.arg = arg
        self.frame = frame
        self.kind = <str>KIND_NAMES[kind]
        self.depth = depth
        self.calls = calls
        self.threading_support = threading_support
        self.detached = False
        self.builtin = kind > 3

        self._code = UNSET
        self._filename = UNSET
        self._fullsource = UNSET
        self._function_object = UNSET
        self._function = UNSET
        self._globals = UNSET
        self._lineno = UNSET
        self._locals = UNSET
        self._module = UNSET
        self._source = UNSET
        self._stdlib = UNSET
        self._threadidn = UNSET
        self._threadname = UNSET
        self._thread = UNSET
        self._instruction = UNSET

    def detach(self, value_filter=None):
        return fast_detach(self, value_filter)

    def clone(self):
        return fast_clone(self)

    cdef instruction_getter(self):
        if self._instruction is UNSET:
            if self.frame.f_lasti >= 0 and self.frame.f_code.co_code:
                self._instruction = self.frame.f_code.co_code[self.frame.f_lasti]
            else:
                self._instruction = None
        return self._instruction

    @property
    def instruction(self):
        return self.instruction_getter()

    cdef threadid_getter(self):
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
    def threadid(self):
        return self.threadid_getter()

    cdef threadname_getter(self):
        if self._threadname is UNSET:
            if self._thread is UNSET:
                self._thread = current_thread()
            self._threadname = self._thread.name
        return self._threadname

    @property
    def threadname(self):
        return self.threadname_getter()

    cdef locals_getter(self):
        if self._locals is UNSET:
            if self.builtin:
                self._locals = {}
            else:
                PyFrame_FastToLocals(self.frame)
                self._locals = self.frame.f_locals
        return self._locals

    @property
    def locals(self):
        return self.locals_getter()

    cdef globals_getter(self):
        if self._globals is UNSET:
            if self.builtin:
                self._locals = {}
            else:
                self._globals = self.frame.f_globals
        return self._globals

    @property
    def globals(self):
        return self.globals_getter()

    cdef function_getter(self):
        if self._function is UNSET:
            if self.builtin:
                self._function = self.arg.__name__
            else:
                self._function = self.frame.f_code.co_name
        return self._function

    @property
    def function(self):
        return self.function_getter()

    @property
    def function_object(self):
        if self.builtin:
            return self.builtin
        elif self._function_object is UNSET:
            code = self.code
            if code.co_name is None:
                return None
            # First, try to find the function in globals
            candidate = self.globals.get(code.co_name, None)
            func = if_same_code(candidate, code)
            # If that failed, as will be the case with class and instance methods, try
            # to look up the function from the first argument. In the case of class/instance
            # methods, this should be the class (or an instance of the class) on which our
            # method is defined.
            if func is None and code.co_argcount >= 1:
                first_arg = self.locals.get(code.co_varnames[0])
                func = get_func_in_mro(first_arg, code)
            # If we still can't find the function, as will be the case with static methods,
            # try looking at classes in global scope.
            if func is None:
                for v in self.globals.values():
                    if not isinstance(v, type):
                        continue
                    func = get_func_in_mro(v, code)
                    if func is not None:
                        break
            self._function_object = func
        return self._function_object

    cdef module_getter(self):
        if self._module is UNSET:
            if self.builtin:
                module = self.arg.__module__
            else:
                module = self.frame.f_globals.get('__name__', '')
                if module is None:
                    module = ''

            self._module = module
        return self._module

    @property
    def module(self):
        return self.module_getter()

    cdef filename_getter(self):
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
    def filename(self):
        return self.filename_getter()

    cdef lineno_getter(self):
        if self._lineno is UNSET:
            self._lineno = self.frame.f_lineno
        return self._lineno

    @property
    def lineno(self):
        return self.lineno_getter()

    cdef code_getter(self):
        if self._code is UNSET:
            return self.frame.f_code
        else:
            return self._code

    @property
    def code(self):
        return self.code_getter()

    cdef stdlib_getter(self):
        if self._stdlib is UNSET:
            module_parts = self.module.split('.')
            if 'pkg_resources' in module_parts:
                # skip this over-vendored module
                self._stdlib = True
            elif self.filename == '<string>' and (self.module.startswith('namedtuple_') or self.module == 'site'):
                # skip namedtuple exec garbage
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
    def stdlib(self):
        return self.stdlib_getter()

    cdef fullsource_getter(self):
        cdef list lines

        if self._fullsource is UNSET:
            try:
                self._fullsource = None

                if self.kind == 'call' and self.frame.f_code.co_name != "<module>":
                    lines = []
                    try:
                        for _, token, _, _, line in generate_tokens(partial(
                                next,
                                yield_lines(self.filename, self.frame.f_globals, self.lineno - 1, lines)
                        )):
                            if token in ("def", "class", "lambda"):
                                self._fullsource = ''.join(lines)
                                break
                    except TokenError:
                        pass
                if self._fullsource is None:
                    self._fullsource = getline(self.filename, self.lineno, self.frame.f_globals)
            except Exception as exc:
                self._fullsource = "??? NO SOURCE: {!r}".format(exc)
        return self._fullsource

    @property
    def fullsource(self):
        return self.fullsource_getter()

    cdef source_getter(self):
        if self._source is UNSET:
            if self.filename.endswith(('.so', '.pyd')):
                self._source = "??? NO SOURCE: not reading {} file".format(splitext(basename(self.filename))[1])
            try:
                self._source = getline(self.filename, self.lineno, self.frame.f_globals)
            except Exception as exc:
                self._source = "??? NO SOURCE: {!r}".format(exc)

        return self._source

    @property
    def source(self):
        return self.source_getter()

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


cdef inline Event fast_detach(Event self, object value_filter):
    event = <Event>Event.__new__(Event)

    event._code = self.code_getter()
    event._filename = self.filename_getter()
    event._fullsource = self.fullsource_getter()
    event._function_object = self._function_object
    event._function = self.function_getter()
    event._lineno = self.lineno_getter()
    event._module = self.module_getter()
    event._source = self.source_getter()
    event._stdlib = self.stdlib_getter()
    event._threadidn = self.threadid_getter()
    event._threadname = self.threadname_getter()
    event._instruction = self.instruction_getter()

    if value_filter:
        event._globals = {key: value_filter(value) for key, value in self.globals.items()}
        event._locals = {key: value_filter(value) for key, value in self.locals.items()}
        event.arg = value_filter(self.arg)
    else:
        event._globals = {}
        event._locals = {}
        event.arg = None

    event.builtin = self.builtin
    event.calls = self.calls
    event.depth = self.depth
    event.detached = True
    event.kind = self.kind
    event.threading_support = self.threading_support

    return event

cdef inline Event fast_clone(Event self):
    event = <Event>Event.__new__(Event)
    event.arg = self.arg
    event.builtin = self.builtin
    event.calls = self.calls
    event.depth = self.depth
    event.detached = False
    event.frame = self.frame
    event.kind = self.kind
    event.threading_support = self.threading_support
    event._code = self._code
    event._filename = self._filename
    event._fullsource = self._fullsource
    event._function_object = self._function_object
    event._function = self._function
    event._globals = self._globals
    event._lineno = self._lineno
    event._locals = self._locals
    event._module = self._module
    event._source = self._source
    event._stdlib = self._stdlib
    event._threadidn = self._threadidn
    event._threadname = self._threadname
    event._thread = self._thread
    event._instruction = self._instruction
    return event
