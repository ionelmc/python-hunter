from __future__ import absolute_import

import linecache
import os
import re
import tokenize
import weakref
from functools import partial
from os.path import basename
from os.path import splitext
from threading import current_thread

from .const import SITE_PACKAGES_PATHS
from .const import SYS_PREFIX_PATHS
from .util import cached_property

try:
    from threading import main_thread
except ImportError:
    from threading import _shutdown
    get_main_thread = weakref.ref(
        _shutdown.__self__ if hasattr(_shutdown, '__self__') else _shutdown.im_self)
    del _shutdown
else:
    get_main_thread = weakref.ref(main_thread())

__all__ = 'Event',

CYTHON_SUFFIX_RE = re.compile(r'([.].+)?[.](so|pyd)$', re.IGNORECASE)
LEADING_WHITESPACE_RE = re.compile('(^[ \t]*)(?:[^ \t\n])', re.MULTILINE)


class Event(object):
    """
    A wrapper object for Frame objects. Instances of this are passed to your custom functions or predicates.

    Provides few convenience properties.

    Args:
        frame (Frame):
        kind (str):
        arg:
        tracer (:obj:`hunter.Tracer`):
    """
    frame = None
    kind = None
    arg = None
    tracer = None
    threadid = None
    threadname = None
    depth = None
    calls = None

    def __init__(self, frame, kind, arg, tracer):
        #: The original Frame object.
        #:
        #: .. note::
        #:
        #:  Not allowed in the builtin predicates (it's the actual Thread object).
        #:  You may access it from your custom predicate though.
        self.frame = frame

        #: The kind of the event, could be one of ``"call"``, ``"line"``, ``"return"``, ``"exception"``,
        #: ``"c_call"``, ``"c_return"``, or ``"c_exception"``.
        #:
        #: :type: str
        self.kind = kind

        #: A value that depends on ``kind``
        self.arg = arg

        #: Tracing depth (increases on calls, decreases on returns)
        #:
        #: :type: int
        self.depth = tracer.depth

        #: A counter for total number of calls up to this Event.
        #:
        #: :type: int
        self.calls = tracer.calls

        #: A reference to the Tracer object.
        #:
        #: .. note::
        #:
        #:  Not allowed in the builtin predicates (it's the actual Thread object).
        #:  You may access it from your custom predicate though.
        #:
        #: :type: :obj:`hunter.Tracer`
        self.tracer = tracer

    def __eq__(self, other):
        return (
            type(self) == type(other) and
            self.kind == other.kind and
            self.depth == other.depth and
            self.function == other.function and
            self.module == other.module and
            self.filename == other.filename
        )

    @cached_property
    def threadid(self):
        """
        Current thread ident. If current thread is main thread then it returns ``None``.

        :type: int or None
        """
        current = self.thread.ident
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
        return self.thread.name

    @cached_property
    def thread(self):
        """
        Current thread object.

        .. note::

            Not allowed in the builtin predicates (it's the actual Thread object).
            You may access it from your custom predicate though.
        """
        return current_thread()

    @cached_property
    def locals(self):
        """
        A dict with local variables.

        :type: dict
        """
        return self.frame.f_locals

    @cached_property
    def globals(self):
        """
        A dict with global variables.

        :type: dict
        """
        return self.frame.f_globals

    @cached_property
    def function(self):
        """
        A string with function name.

        :type: str
        """
        return self.code.co_name

    @cached_property
    def module(self):
        """
        A string with module name (like ``"foo.bar"``).

        :type: str
        """
        module = self.frame.f_globals.get('__name__', '')
        if module is None:
            module = ''

        return module

    @cached_property
    def filename(self, exists=os.path.exists, cython_suffix_re=CYTHON_SUFFIX_RE):
        """
        A string with the path to the module's file. May be empty if ``__file__`` attribute is missing.
        May be relative if running scripts.

        :type: str
        """
        filename = self.frame.f_code.co_filename
        if not filename:
            filename = self.frame.f_globals.get('__file__')
        if not filename:
            filename = ''
        if filename.endswith(('.pyc', '.pyo')):
            filename = filename[:-1]
        elif filename.endswith('$py.class'):  # Jython
            filename = filename[:-9] + ".py"
        elif filename.endswith(('.so', '.pyd')):
            basename = cython_suffix_re.sub('', filename)
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
            return False
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
            return self._raw_fullsource
        except Exception as exc:
            return "??? NO SOURCE: {!r}".format(exc)

    @cached_property
    def source(self, getline=linecache.getline):
        """
        A string with the sourcecode for the current line (from ``linecache`` - failures are ignored).

        Fast but sometimes incomplete.

        :type: str
        """
        if self.filename.endswith(('.so', '.pyd')):
            return "??? NO SOURCE: not reading {} file".format(splitext(basename(self.filename))[1])
        try:
            return getline(self.filename, self.lineno)
        except Exception as exc:
            return "??? NO SOURCE: {!r}".format(exc)

    @cached_property
    def _raw_fullsource(self,
                        getlines=linecache.getlines,
                        getline=linecache.getline,
                        generate_tokens=tokenize.generate_tokens):
        if self.kind == 'call' and self.code.co_name != "<module>":
            lines = []
            try:
                for _, token, _, _, line in generate_tokens(partial(
                    next,
                    yield_lines(self.filename, self.lineno - 1, lines.append)
                )):
                    if token in ("def", "class", "lambda"):
                        return ''.join(lines)
            except tokenize.TokenError:
                pass

        return getline(self.filename, self.lineno)

    __getitem__ = object.__getattribute__


def yield_lines(filename, start, collector,
                limit=10,
                getlines=linecache.getlines,
                leading_whitespace_re=LEADING_WHITESPACE_RE):
    dedent = None
    amount = 0
    for line in getlines(filename)[start:start + limit]:
        if dedent is None:
            dedent = leading_whitespace_re.findall(line)
            dedent = dedent[0] if dedent else ""
            amount = len(dedent)
        elif not line.startswith(dedent):
            break
        collector(line)
        yield line[amount:]
