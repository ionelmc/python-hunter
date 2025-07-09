# cython: linetrace=True, language_level=3str, c_string_encoding=ascii, freethreading_compatible=True
cimport cython

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
from cpython.ref cimport PyObject

from .const import SITE_PACKAGES_PATHS
from .const import SYS_PREFIX_PATHS
from .util import CYTHON_SUFFIX_RE
from .util import LEADING_WHITESPACE_RE
from .util import get_func_in_mro
from .util import get_main_thread
from .util import if_same_code

__all__ = 'Event',

cdef object UNSET = object()


cdef str CALL = 'call'
cdef str EXCEPTION = 'exception'
cdef str LINE = 'line'
cdef str RETURN = 'return'

cdef const PyObject** KIND_NAMES = [
    <PyObject*>CALL,
    <PyObject*>EXCEPTION,
    <PyObject*>LINE,
    <PyObject*>RETURN,
    <PyObject*>CALL,
    <PyObject*>EXCEPTION,
    <PyObject*>RETURN,
]


@cython.auto_pickle(False)
cdef class Event:
    """
    A wrapper object for Frame objects. Instances of this are passed to your custom functions or predicates.

    Provides few convenience properties.

    Args:
        frame (Frame): A python `Frame <https://docs.python.org/3/reference/datamodel.html#frame-objects>`_ object.
        kind (str): A string like ``'call'``, ``'line'``, ``'return'`` or ``'exception'``.
        arg: A value that depends on ``kind``. Usually is ``None`` but for ``'return'`` or ``'exception'`` other values
            may be expected.
    """
    def __init__(self, FrameType frame, int kind, object arg, int depth, int calls, bint threading_support):
        self.arg = arg
        self.frame = frame
        self.kind = <str> KIND_NAMES[kind]
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

    def __repr__(self):
        return '<Event kind=%r function=%r module=%r filename=%r lineno=%s>' % (
            self.kind, self.function, self.module, self.filename, self.lineno
        )

    def __eq__(self, other):
        return self is other

    def detach(self, value_filter=None):
        return fast_detach(self, value_filter)

    def clone(self):
        return fast_clone(self)

    cdef inline instruction_getter(self):
        cdef int position

        if self._instruction is UNSET:
            position = Hunter_PyFrame_GetLasti(self.frame)
            co_code = PyCode_GetCode(self.code_getter())
            if co_code and len(co_code) > position >= 0:
                self._instruction = co_code[position]
            else:
                self._instruction = None
        return self._instruction

    @property
    def instruction(self):
        return self.instruction_getter()

    cdef inline threadid_getter(self):
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

    cdef inline threadname_getter(self):
        if self._threadname is UNSET:
            if self._thread is UNSET:
                self._thread = current_thread()
            self._threadname = self._thread.name
        return self._threadname

    @property
    def threadname(self):
        return self.threadname_getter()

    cdef inline locals_getter(self):
        if self._locals is UNSET:
            if self.builtin:
                self._locals = {}
            else:
                self._locals = Hunter_PyFrame_GetLocals(self.frame)
        return self._locals

    @property
    def locals(self):
        return self.locals_getter()

    cdef inline globals_getter(self):
        if self._globals is UNSET:
            if self.builtin:
                self._locals = {}
            else:
                self._globals = Hunter_PyFrame_GetGlobals(self.frame)
        return self._globals

    @property
    def globals(self):
        return self.globals_getter()

    cdef inline function_getter(self):
        if self._function is UNSET:
            if self.builtin:
                self._function = self.arg.__name__
            else:
                self._function = self.code_getter().co_name
        return self._function

    @property
    def function(self):
        return self.function_getter()

    @property
    def function_object(self):
        cdef CodeType code
        if self.builtin:
            return self.builtin
        elif self._function_object is UNSET:
            code = self.code_getter()
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
                first_arg = self.locals.get(PyCode_GetVarnames(code)[0])
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

    cdef inline module_getter(self):
        if self._module is UNSET:
            if self.builtin:
                module = self.arg.__module__
            else:
                module = self.globals.get('__name__', '')
            if module is None:
                module = '?'
            self._module = module
        return self._module

    @property
    def module(self):
        return self.module_getter()

    cdef inline filename_getter(self):
        cdef CodeType code
        if self._filename is UNSET:
            code = self.code_getter()
            filename = code.co_filename
            if not filename:
                filename = self.globals.get('__file__')
            if not filename:
                filename = '?'
            elif filename.endswith(('.pyc', '.pyo')):
                filename = filename[:-1]
            elif filename.endswith(('.so', '.pyd')):
                cybasename = CYTHON_SUFFIX_RE.sub('', filename)
                for ext in ('.pyx', '.py'):
                    cyfilename = cybasename + ext
                    if exists(cyfilename):
                        filename = cyfilename
                        break

            self._filename = filename
        return self._filename

    @property
    def filename(self):
        return self.filename_getter()

    cdef inline lineno_getter(self):
        if self._lineno is UNSET:
            self._lineno = Hunter_PyFrame_GetLineNumber(self.frame)
        return self._lineno

    @property
    def lineno(self):
        return self.lineno_getter()

    cdef inline CodeType code_getter(self):
        if self._code is UNSET:
            return Hunter_PyFrame_GetCode(self.frame)
        else:
            return self._code

    @property
    def code(self):
        return self.code_getter()

    cdef inline stdlib_getter(self):
        if self._stdlib is UNSET:
            module_parts = self.module.split('.')
            if 'pkg_resources' in module_parts:
                # skip this over-vendored module
                self._stdlib = True
            elif self.filename == '<string>' and (self.module.startswith('namedtuple_') or self.module == 'site'):
                # skip namedtuple exec garbage
                self._stdlib = True
            elif self.filename.startswith(SITE_PACKAGES_PATHS):
                # if in site-packages then definitely not stdlib
                self._stdlib = False
            elif self.filename.startswith(SYS_PREFIX_PATHS):
                self._stdlib = True
            else:
                self._stdlib = False
        return self._stdlib

    @property
    def stdlib(self):
        return self.stdlib_getter()

    cdef inline fullsource_getter(self):
        cdef list lines
        cdef CodeType code

        if self._fullsource is UNSET:
            try:
                self._fullsource = None
                code = self.code_getter()
                if self.kind == 'call' and code.co_name != '<module>':
                    lines = []
                    try:
                        for _, token, _, _, _ in generate_tokens(
                            partial(
                                next,
                                yield_lines(
                                    self.filename,
                                    self.frame.f_globals,
                                    self.lineno - 1,
                                    lines,
                                ),
                            )
                        ):
                            if token in ('def', 'class', 'lambda'):
                                self._fullsource = ''.join(lines)
                                break
                    except TokenError:
                        pass
                if self._fullsource is None:
                    self._fullsource = getline(self.filename, self.lineno, self.globals)
            except Exception as exc:
                self._fullsource = f'??? NO SOURCE: {exc!r}'
        return self._fullsource

    @property
    def fullsource(self):
        return self.fullsource_getter()

    cdef inline source_getter(self):
        if self._source is UNSET:
            if self.filename.endswith(('.so', '.pyd')):
                self._source = f'??? NO SOURCE: not reading binary {splitext(basename(self.filename))[1]} file'
            try:
                self._source = getline(self.filename, self.lineno, self.globals)
            except Exception as exc:
                self._source = f'??? NO SOURCE: {exc!r}'

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
            dedent = dedent[0] if dedent else ''
            amount = len(dedent)
        elif not line.startswith(dedent):
            break
        collector.append(line)
        yield line[amount:]


cdef inline Event fast_detach(Event self, object value_filter):
    event = <Event> Event.__new__(Event)

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
    event = <Event> Event.__new__(Event)
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
