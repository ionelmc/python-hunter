from __future__ import absolute_import

import linecache
import tokenize
from functools import partial
from os.path import basename
from os.path import exists
from os.path import splitext
from threading import current_thread

from .const import SITE_PACKAGES_PATHS
from .const import SYS_PREFIX_PATHS
from .util import CYTHON_SUFFIX_RE
from .util import LEADING_WHITESPACE_RE
from .util import MISSING
from .util import PY2
from .util import cached_property
from .util import get_func_in_mro
from .util import get_main_thread
from .util import if_same_code

__all__ = 'Event',


class Event(object):
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
    frame = None
    kind = None
    arg = None
    depth = None
    calls = None
    builtin = None

    def __init__(self, frame, kind, arg, tracer=None, depth=None, calls=None, threading_support=MISSING):
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

        #: The original Frame object.
        #:
        #: .. note::
        #:
        #:  Not allowed in the builtin predicates (it's the actual Frame object).
        #:  You may access it from your custom predicate though.
        self.frame = frame

        if kind.startswith('c_'):
            kind = kind[2:]
            builtin = True
        else:
            builtin = False

        #: If kind of the event is one of ``'c_call'``, ``'c_return'``, or ``'c_exception'`` then this will be True.
        #:
        #: :type: bool
        self.builtin = builtin

        #: The kind of the event, could be one of ``'call'``, ``'line'``, ``'return'``, ``'exception'``.
        #:
        #: :type: str
        self.kind = kind

        #: A value that depends on ``kind``
        self.arg = arg

        #: Tracing depth (increases on calls, decreases on returns).
        #:
        #: :type: int
        self.depth = depth

        #: A counter for total number of calls up to this Event.
        #:
        #: :type: int
        self.calls = calls

        #: A copy of the :attr:`hunter.tracer.Tracer.threading_support` flag.
        #:
        #: .. note::
        #:
        #:  Not allowed in the builtin predicates. You may access it from your custom predicate though.
        #:
        #: :type: bool or None
        self.threading_support = threading_support

        #: Flag that is ``True`` if the event was created with :meth:`~hunter.event.Event.detach`.
        #:
        #: :type: bool
        self.detached = False

    def __repr__(self):
        return '<Event kind=%r function=%r module=%r filename=%r lineno=%s>' % (
            self.kind, self.function, self.module, self.filename, self.lineno
        )

    def __eq__(self, other):
        return (
            type(self) == type(other) and
            self.kind == other.kind and
            self.depth == other.depth and
            self.function == other.function and
            self.module == other.module and
            self.filename == other.filename
        )

    def detach(self, value_filter=None):
        """
        Return a copy of the event with references to live objects (like the frame) removed. You should use this if you
        want to store or use the event outside the handler.

        You should use this if you want to avoid memory leaks or side-effects when storing the events.

        Args:
            value_filter:
                Optional callable that takes one argument: ``value``.

                If not specified then the ``arg``, ``globals`` and ``locals`` fields will be ``None``.

        Example usage in a :class:`~hunter.actions.ColorStreamAction` subclass:

        .. sourcecode:: python

            def __call__(self, event):
                self.events = [event.detach(lambda field, value: self.try_repr(value))]

        """
        event = Event.__new__(Event)

        event.__dict__['code'] = self.code
        event.__dict__['filename'] = self.filename
        event.__dict__['fullsource'] = self.fullsource
        event.__dict__['function'] = self.function
        event.__dict__['lineno'] = self.lineno
        event.__dict__['module'] = self.module
        event.__dict__['source'] = self.source
        event.__dict__['stdlib'] = self.stdlib
        event.__dict__['threadid'] = self.threadid
        event.__dict__['threadname'] = self.threadname
        event.__dict__['instruction'] = self.instruction

        if value_filter:
            event.__dict__['arg'] = value_filter(self.arg)
            event.__dict__['globals'] = {key: value_filter(value) for key, value in self.globals.items()}
            event.__dict__['locals'] = {key: value_filter(value) for key, value in self.locals.items()}
        else:
            event.__dict__['globals'] = {}
            event.__dict__['locals'] = {}
            event.__dict__['arg'] = None

        event.threading_support = self.threading_support
        event.calls = self.calls
        event.depth = self.depth
        event.kind = self.kind
        event.builtin = self.builtin

        event.detached = True

        return event

    def clone(self):
        event = Event.__new__(Event)
        event.__dict__ = dict(self.__dict__)
        return event

    @cached_property
    def instruction(self):
        """
        Last byte instruction. If no bytecode was used (Cython code) then it returns ``None``.
        Depending on Python version it might be an int or a single char string.

        :type: int or single char string or None
        """
        if self.frame.f_lasti >= 0 and self.frame.f_code.co_code:
            return self.frame.f_code.co_code[self.frame.f_lasti]

    @cached_property
    def threadid(self):
        """
        Current thread ident. If current thread is main thread then it returns ``None``.

        :type: int or None
        """
        current = self._thread.ident
        main = get_main_thread()
        if main is None:
            return current
        else:
            return current if current != main.ident else None

    @cached_property
    def threadname(self):
        """
        Current thread name.

        :type: str
        """
        return self._thread.name

    @cached_property
    def _thread(self):
        return current_thread()

    @cached_property
    def locals(self):
        """
        A dict with local variables.

        :type: dict
        """
        if self.builtin:
            return {}

        return self.frame.f_locals

    @cached_property
    def globals(self):
        """
        A dict with global variables.

        :type: dict
        """
        if self.builtin:
            return {}

        return self.frame.f_globals

    @cached_property
    def function(self):
        """
        A string with function name.

        :type: str
        """
        if self.builtin:
            return self.arg.__name__
        else:
            return self.code.co_name

    @cached_property
    def function_object(self):
        """
        The function instance.

        .. warning:: Use with prudence.

            * Will be ``None`` for decorated functions on Python 2 (methods may still work tho).
            * May be ``None`` if tracing functions or classes not defined at module level.
            * May be very slow if tracing modules with lots of variables.

        :type: function or None
        """
        # Based on MonkeyType's get_func
        if self.builtin:
            return self.builtin

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
        return func

    @cached_property
    def module(self):
        """
        A string with module name (like ``'foo.bar'``).

        :type: str
        """
        if self.builtin:
            module = self.arg.__module__
        else:
            module = self.frame.f_globals.get('__name__', '')
        if module is None:
            module = '?'
        if PY2:
            module = module.encode('ascii', 'replace')
        return module

    @cached_property
    def filename(self):
        """
        A string with the path to the module's file. May be empty if ``__file__`` attribute is missing.
        May be relative if running scripts.

        :type: str
        """
        # if self.builtin:
        #     return '<builtin>'
        # if self.builtin:
        #     return '<builtin>'
        filename = self.frame.f_code.co_filename
        if not filename:
            filename = self.frame.f_globals.get('__file__')
        if not filename:
            filename = '?'
        if filename.endswith(('.pyc', '.pyo')):
            filename = filename[:-1]
        elif filename.endswith('$py.class'):  # Jython
            filename = filename[:-9] + '.py'
        elif filename.endswith(('.so', '.pyd')):
            basename = CYTHON_SUFFIX_RE.sub('', filename)
            for ext in ('.pyx', '.py'):
                cyfilename = basename + ext
                if exists(cyfilename):
                    filename = cyfilename
                    break
        return filename

    @cached_property
    def lineno(self):
        """
        An integer with line number in file.

        :type: int
        """
        return self.frame.f_lineno

    @cached_property
    def code(self):
        """
        A code object (not a string).
        """
        return self.frame.f_code

    @cached_property
    def stdlib(self):
        """
        A boolean flag. ``True`` if frame is in stdlib.

        :type: bool
        """
        module_parts = self.module.split('.')
        if 'pkg_resources' in module_parts:
            # skip this over-vendored module
            return True
        elif self.filename == '<string>' and (self.module.startswith('namedtuple_') or self.module == 'site'):
            # skip namedtuple exec garbage
            return True
        elif self.filename.startswith(SITE_PACKAGES_PATHS):
            # if it's in site-packages then its definitely not stdlib
            return False
        elif self.filename.startswith(SYS_PREFIX_PATHS):
            return True
        else:
            return False

    @cached_property
    def fullsource(self):
        """
        A string with the sourcecode for the current statement (from ``linecache`` - failures are ignored).

        May include multiple lines if it's a class/function definition (will include decorators).

        :type: str
        """
        try:
            if self.kind == 'call' and self.code.co_name != '<module>':
                lines = []
                try:
                    for _, token, _, _, line in tokenize.generate_tokens(partial(
                        next,
                        yield_lines(self.filename, self.frame.f_globals, self.lineno - 1, lines.append)
                    )):
                        if token in ('def', 'class', 'lambda'):
                            return ''.join(lines)
                except tokenize.TokenError:
                    pass

            return linecache.getline(self.filename, self.lineno, self.frame.f_globals)
        except Exception as exc:
            return '??? NO SOURCE: {!r}'.format(exc)

    @cached_property
    def source(self):
        """
        A string with the sourcecode for the current line (from ``linecache`` - failures are ignored).

        Fast but sometimes incomplete.

        :type: str
        """
        if self.filename.endswith(('.so', '.pyd')):
            return '??? NO SOURCE: not reading binary {} file'.format(splitext(basename(self.filename))[1])
        try:
            return linecache.getline(self.filename, self.lineno, self.frame.f_globals)
        except Exception as exc:
            return '??? NO SOURCE: {!r}'.format(exc)

    __getitem__ = object.__getattribute__


def yield_lines(filename, module_globals, start, collector,
                limit=10,
                leading_whitespace_re=LEADING_WHITESPACE_RE):
    dedent = None
    amount = 0
    for line in linecache.getlines(filename, module_globals)[start:start + limit]:
        if dedent is None:
            dedent = leading_whitespace_re.findall(line)
            dedent = dedent[0] if dedent else ''
            amount = len(dedent)
        elif not line.startswith(dedent):
            break
        collector(line)
        yield line[amount:]
