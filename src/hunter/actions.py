from __future__ import absolute_import

import collections
import opcode
import os
import threading
from collections import defaultdict
from itertools import islice
from os import getpid

from . import config
from .util import BUILTIN_SYMBOLS
from .util import CALL_COLORS
from .util import CODE_COLORS
from .util import MISSING
from .util import OTHER_COLORS
from .util import PY3
from .util import StringType
from .util import builtins
from .util import frame_iterator
from .util import get_arguments
from .util import iter_symbols
from .util import safe_repr
from .vendor.colorama import AnsiToWin32

try:
    from threading import get_ident
except ImportError:
    from thread import get_ident

__all__ = ['Action', 'Debugger', 'Manhole', 'CodePrinter', 'CallPrinter', 'VarsPrinter']

BUILTIN_REPR_FUNCS = {
    'repr': repr,
    'safe_repr': safe_repr
}


class Action(object):
    def __call__(self, event):
        raise NotImplementedError()


class LazyImportPdb(object):
    def __repr__(self):
        return "<class 'pdb.Pdb'>"

    __str__ = __repr__

    def __call__(self, **kwargs):
        from pdb import Pdb
        return Pdb(**kwargs)


class Debugger(Action):
    """
    An action that starts ``pdb``.
    """

    def __init__(self, klass=config.Default('klass', LazyImportPdb()), **kwargs):
        self.klass = config.resolve(klass)
        self.kwargs = kwargs

    def __eq__(self, other):
        return (
            type(self) is type(other) and
            self.klass == other.klass and
            self.kwargs == other.kwargs
        )

    def __str__(self):
        return '{0.__class__.__name__}(klass={0.klass}, kwargs={0.kwargs})'.format(self)

    def __repr__(self):
        return '{0.__class__.__name__}(klass={0.klass!r}, kwargs={0.kwargs!r})'.format(self)

    def __call__(self, event):
        """
        Runs a ``pdb.set_trace`` at the matching frame.
        """
        self.klass(**self.kwargs).set_trace(event.frame)


class Manhole(Action):
    def __init__(self, **options):
        self.options = options

    def __eq__(self, other):
        return type(self) is type(other) and self.options == other.options

    def __str__(self):
        return '{0.__class__.__name__}(options={0.options})'.format(self)

    def __repr__(self):
        return '{0.__class__.__name__}(options={0.options!r})'.format(self)

    def __call__(self, event):
        import manhole
        inst = manhole.install(strict=False, thread=False, **self.options)
        inst.handle_oneshot()


class ColorStreamAction(Action):
    """
    Baseclass for your custom action. Just implement your own ``__call__``.
    """
    _stream_cache = {}
    _stream = None
    _tty = None
    _repr_func = None

    OTHER_COLORS = OTHER_COLORS
    EVENT_COLORS = CODE_COLORS

    def __init__(self,
                 stream=config.Default('stream', None),
                 force_colors=config.Default('force_colors', False),
                 force_pid=config.Default('force_pid', False),
                 filename_alignment=config.Default('filename_alignment', 40),
                 thread_alignment=config.Default('thread_alignment', 12),
                 pid_alignment=config.Default('pid_alignment', 9),
                 repr_limit=config.Default('repr_limit', 1024),
                 repr_func=config.Default('repr_func', 'safe_repr')):
        self.force_colors = config.resolve(force_colors)
        self.force_pid = config.resolve(force_pid)
        stream = config.resolve(stream)
        if stream is None:
            from . import _default_stream as stream
        self.stream = stream
        self.filename_alignment = config.resolve(filename_alignment)
        self.thread_alignment = config.resolve(thread_alignment)
        self.pid_alignment = config.resolve(pid_alignment)
        self.repr_limit = config.resolve(repr_limit)
        self.repr_func = config.resolve(repr_func)
        self.seen_threads = set()
        self.seen_pid = getpid()

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self.stream == other.stream
            and self.force_colors == other.force_colors
            and self.filename_alignment == other.filename_alignment
            and self.thread_alignment == other.thread_alignment
            and self.pid_alignment == other.pid_alignment
            and self.repr_limit == other.repr_limit
            and self.repr_func == other.repr_func
        )

    def __str__(self):
        return '{0.__class__.__name__}(stream={0.stream}, force_colors={0.force_colors}, ' \
               'filename_alignment={0.filename_alignment}, thread_alignment={0.thread_alignment}, ' \
               'pid_alignment={0.pid_alignment} repr_limit={0.repr_limit}, ' \
               'repr_func={0.repr_func})'.format(self)

    def __repr__(self):
        return '{0.__class__.__name__}(stream={0.stream!r}, force_colors={0.force_colors!r}, ' \
               'filename_alignment={0.filename_alignment!r}, thread_alignment={0.thread_alignment!r}, ' \
               'pid_alignment={0.pid_alignment!r} repr_limit={0.repr_limit!r}, ' \
               'repr_func={0.repr_func!r})'.format(self)

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, value):
        if isinstance(value, StringType):
            if value in self._stream_cache:
                value = self._stream_cache[value]
            else:
                value = self._stream_cache[value] = open(value, 'a', buffering=0)

        isatty = getattr(value, 'isatty', None)
        if self.force_colors or (isatty and isatty() and os.name != 'java'):
            self._stream = AnsiToWin32(value, strip=False)
            self._tty = True
            self.event_colors = self.EVENT_COLORS
            self.other_colors = self.OTHER_COLORS
        else:
            self._tty = False
            self._stream = value
            self.event_colors = {key: '' for key in self.EVENT_COLORS}
            self.other_colors = {key: '' for key in self.OTHER_COLORS}

    @property
    def repr_func(self):
        return self._repr_func

    @repr_func.setter
    def repr_func(self, value):
        if callable(value):
            self._repr_func = value
        elif value in BUILTIN_REPR_FUNCS:
            self._repr_func = BUILTIN_REPR_FUNCS[value]
        else:
            raise TypeError('Expected a callable or either "repr" or "safe_repr" strings, not {!r}.'.format(value))

    def try_str(self, obj):
        """
        Safely call ``str(obj)``. Failures will have special colored output and output is trimmed according
        to ``self.repr_limit``.

        Only used when dumping detached events.

        Returns: string
        """
        limit = self.repr_limit
        try:
            s = str(obj)
            s = s.replace('\n', r'\n')
            if len(s) > limit:
                cutoff = limit // 2
                return '{} {CONT}[...]{RESET} {}'.format(s[:cutoff], s[-cutoff:], **self.other_colors)
            else:
                return s
        except Exception as exc:
            return '{INTERNAL-FAILURE}!!! FAILED REPR: {INTERNAL-DETAIL}{!r}{RESET}'.format(exc, **self.other_colors)

    def try_repr(self, obj):
        """
        Safely call ``self.repr_func(obj)``. Failures will have special colored output and output is trimmed according
        to ``self.repr_limit``.

        Returns: string

        """
        limit = self.repr_limit
        try:
            s = self.repr_func(obj)
            s = s.replace('\n', r'\n')
            if len(s) > limit:
                cutoff = limit // 2
                return '{} {CONT}[...]{RESET} {}'.format(s[:cutoff], s[-cutoff:], **self.other_colors)
            else:
                return s
        except Exception as exc:
            return '{INTERNAL-FAILURE}!!! FAILED REPR: {INTERNAL-DETAIL}{!r}{RESET}'.format(exc, **self.other_colors)

    def try_source(self, event, full=False):
        """
        Get a failure-colorized source for the given ``event``.

        Return: string
        """
        source = event.fullsource if full else event.source
        if source.startswith('??? NO SOURCE: '):
            return '{SOURCE-FAILURE}??? NO SOURCE: {SOURCE-DETAIL}{}'.format(source[15:], **self.other_colors)
        elif source:
            return source
        else:
            return '{SOURCE-FAILURE}??? NO SOURCE: {SOURCE-DETAIL}Source code string for {!r} is empty.'.format(
                event.filename, **self.other_colors)

    def filename_prefix(self, event=None):
        """
        Get an aligned and trimmed filename prefix for the given ``event``.

        Returns: string
        """
        if event:
            filename = event.filename
            if filename == '?':
                filename = '{SOURCE-FAILURE}?'.format(**self.other_colors)
            lineno = '{COLON}:{LINENO}{:<5}'.format(event.lineno, **self.other_colors)

            if len(filename) > self.filename_alignment:
                filename = '[...]{}'.format(filename[5 - self.filename_alignment:])
            return '{:>{}}{} '.format(
                filename, self.filename_alignment, lineno, **self.other_colors)
        else:
            return '{:>{}}       '.format('', self.filename_alignment)

    def pid_prefix(self):
        """
        Get an aligned and trimmed pid prefix.
        """
        pid = getpid()
        if self.force_pid or self.seen_pid != pid:
            pid = '[{}]'.format(pid)
            pid_align = self.pid_alignment
        else:
            pid = pid_align = ''
        return '{:{}}'.format(pid, pid_align)

    def thread_prefix(self, event):
        """
        Get an aligned and trimmed thread prefix for the given ``event``.
        """
        self.seen_threads.add(get_ident())
        if event.threading_support is False:
            threading_support = False
        elif event.threading_support:
            threading_support = True
        else:
            threading_support = len(self.seen_threads) > 1
        thread_name = threading.current_thread().name if threading_support else ''
        thread_align = self.thread_alignment if threading_support else ''
        return '{:{}}'.format(thread_name, thread_align)

    def output(self, format_str, *args, **kwargs):
        """
        Write ``format_str.format(*args, **ANSI_COLORS, **kwargs)`` to ``self.stream``.

        For ANSI coloring you can place these in the ``format_str``:

        * ``{BRIGHT}``
        * ``{DIM}``
        * ``{NORMAL}``
        * ``{RESET}``
        * ``{fore(BLACK)}``
        * ``{fore(RED)}``
        * ``{fore(GREEN)}``
        * ``{fore(YELLOW)}``
        * ``{fore(BLUE)}``
        * ``{fore(MAGENTA)}``
        * ``{fore(CYAN)}``
        * ``{fore(WHITE)}``
        * ``{fore(RESET)}``
        * ``{back(BLACK)}``
        * ``{back(RED)}``
        * ``{back(GREEN)}``
        * ``{back(YELLOW)}``
        * ``{back(BLUE)}``
        * ``{back(MAGENTA)}``
        * ``{back(CYAN)}``
        * ``{back(WHITE)}``
        * ``{back(RESET)}``

        Args:
            format_str: a PEP-3101 format string
            *args:
            **kwargs:

        Returns: string
        """
        self.stream.write(format_str.format(
            *args,
            **dict(self.other_colors, **kwargs)
        ))

    def cleanup(self):
        pass


class CodePrinter(ColorStreamAction):
    """
    An action that just prints the code being executed.

    Args:
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        force_colors (bool): Force coloring. Default: ``False``.
        repr_limit (bool): Limit length of ``repr()`` output. Default: ``512``.
        repr_func (string or callable): Function to use instead of ``repr``.
            If string must be one of 'repr' or 'safe_repr'. Default: ``'safe_repr'``.
    """

    def __call__(self, event):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also
        prints values.
        """
        lines = self.try_source(event, full=True).splitlines()
        pid_prefix = self.pid_prefix()
        thread_prefix = self.thread_prefix(event)
        filename_prefix = self.filename_prefix(event)

        self.output(
            '{}{}{}{KIND}{:9} {COLOR}{}{RESET}\n',
            pid_prefix,
            thread_prefix,
            filename_prefix,
            event.kind,
            lines[0],
            COLOR=self.event_colors.get(event.kind),
        )
        if len(lines) > 1:
            empty_filename_prefix = self.filename_prefix()
            for line in lines[1:-1]:
                self.output(
                    '{}{}{}{KIND}{:9} {COLOR}{}{RESET}\n',
                    pid_prefix,
                    thread_prefix,
                    empty_filename_prefix,
                    '   |',
                    line,
                    COLOR=self.event_colors.get(event.kind),
                )
            self.output(
                '{}{}{}{KIND}{:9} {COLOR}{}{RESET}\n',
                pid_prefix,
                thread_prefix,
                empty_filename_prefix,
                '   *',
                lines[-1],
                COLOR=self.event_colors.get(event.kind),
            )

        if event.kind in ('return', 'exception'):
            self.output(
                '{}{}{}{CONT}{:9} {COLOR}{} value: {NORMAL}{}{RESET}\n',
                pid_prefix,
                thread_prefix,
                self.filename_prefix(),
                '...',
                event.kind,
                self.try_str(event.arg) if event.detached else self.try_repr(event.arg),
                COLOR=self.event_colors.get(event.kind),
            )


class CallPrinter(CodePrinter):
    """
    An action that just prints the code being executed, but unlike :obj:`hunter.CodePrinter` it indents based on
    callstack depth and it also shows ``repr()`` of function arguments.

    Args:
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        force_colors (bool): Force coloring. Default: ``False``.
        repr_limit (bool): Limit length of ``repr()`` output. Default: ``512``.
        repr_func (string or callable): Function to use instead of ``repr``.
            If string must be one of 'repr' or 'safe_repr'. Default: ``'safe_repr'``.

    .. versionadded:: 1.2.0
    """
    EVENT_COLORS = CALL_COLORS

    locals = defaultdict(list)

    @classmethod
    def cleanup(cls):
        cls.locals = defaultdict(list)

    def __init__(self, *args, **kwargs):
        super(CallPrinter, self).__init__(*args, **kwargs)

    def __call__(self, event):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also
        prints values.
        """
        ident = event.module, event.function

        thread = threading.current_thread()
        stack = self.locals[thread.ident]

        pid_prefix = self.pid_prefix()
        thread_prefix = self.thread_prefix(event)
        filename_prefix = self.filename_prefix(event)

        if event.kind == 'call':
            if event.builtin:
                self.output(
                    '{}{}{}{KIND}{:9} {}{COLOR} >{BUILTIN} {}.{}: {}{RESET}\n',
                    pid_prefix,
                    thread_prefix,
                    filename_prefix,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.module,
                    event.function,
                    self.try_source(event).strip(),
                    COLOR=self.event_colors.get(event.kind),
                )
            else:
                code = event.code
                stack.append(ident)
                self.output(
                    '{}{}{}{KIND}{:9} {}{COLOR}=>{NORMAL} {}({}{COLOR}{NORMAL}){RESET}\n',
                    pid_prefix,
                    thread_prefix,
                    filename_prefix,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.function,
                    ', '.join('{VARS}{0}{VARS-NAME}{1}{VARS}={RESET}{2}'.format(
                        prefix,
                        var_display,
                        self.try_str(event.locals.get(var_lookup, MISSING))
                        if event.detached
                        else self.try_repr(event.locals.get(var_lookup, MISSING)),
                        **self.other_colors
                    ) for prefix, var_lookup, var_display in get_arguments(code)),
                    COLOR=self.event_colors.get(event.kind),
                )
        elif event.kind == 'exception':
            if event.builtin:
                self.output(
                    '{}{}{}{KIND}{:9} {}{COLOR} ! {BUILTIN}{}.{}{RESET}\n',
                    pid_prefix,
                    thread_prefix,
                    filename_prefix,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.module,
                    event.function,
                    COLOR=self.event_colors.get(event.kind),
                )
            else:
                self.output(
                    '{}{}{}{KIND}{:9} {}{COLOR} !{NORMAL} {}: {RESET}{}\n',
                    pid_prefix,
                    thread_prefix,
                    filename_prefix,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.function,
                    self.try_str(event.arg) if event.detached else self.try_repr(event.arg),
                    COLOR=self.event_colors.get(event.kind),
                )
        elif event.kind == 'return':
            if event.builtin:
                self.output(
                    '{}{}{}{KIND}{:9} {}{COLOR} <{BUILTIN} {}.{}{RESET}\n',
                    pid_prefix,
                    thread_prefix,
                    filename_prefix,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.module,
                    event.function,
                    COLOR=self.event_colors.get(event.kind),
                )
            else:
                self.output(
                    '{}{}{}{KIND}{:9} {}{COLOR}<={NORMAL} {}{}{RESET}{}\n',
                    pid_prefix,
                    thread_prefix,
                    filename_prefix,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.function,
                    '' if event.builtin else ': ',
                    '' if event.builtin else (self.try_str(event.arg) if event.detached else self.try_repr(event.arg)),
                    COLOR=self.event_colors.get(event.kind),
                )
                if stack and stack[-1] == ident:
                    stack.pop()
        else:
            self.output(
                '{}{}{}{KIND}{:9} {RESET}{}{}{RESET}\n',
                pid_prefix,
                thread_prefix,
                filename_prefix,
                event.kind,
                '   ' * len(stack),
                self.try_source(event).strip(),
            )


class VarsPrinter(ColorStreamAction):
    """
    An action that prints local variables and optionally global variables visible from the current executing frame.

    Args:
        *names (strings): Names to evaluate. Expressions can be used (will only try to evaluate if all the variables are
            present on the frame.
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        force_colors (bool): Force coloring. Default: ``False``.
        repr_limit (bool): Limit length of ``repr()`` output. Default: ``512``.
        repr_func (string or callable): Function to use instead of ``repr``.
            If string must be one of 'repr' or 'safe_repr'. Default: ``'safe_repr'``.
    """

    def __init__(self, *names, **options):
        if not names:
            raise TypeError('VarsPrinter requires at least one variable name/expression.')
        self.names = {
            name: set(iter_symbols(name))
            for name in names
        }
        super(VarsPrinter, self).__init__(**options)

    def __call__(self, event):
        """
        Handle event and print the specified variables.
        """
        first = True

        frame_symbols = set(event.locals)
        frame_symbols.update(BUILTIN_SYMBOLS)
        frame_symbols.update(event.globals)

        pid_prefix = self.pid_prefix()
        thread_prefix = self.thread_prefix(event)
        filename_prefix = self.filename_prefix(event)
        empty_filename_prefix = self.filename_prefix()

        for code, symbols in self.names.items():
            try:
                obj = eval(code, dict(vars(builtins), **event.globals), event.locals)
            except (AttributeError, KeyError):
                continue
            except Exception as exc:
                printout = '{INTERNAL-FAILURE}FAILED EVAL: {INTERNAL-DETAIL}{!r}'.format(exc, **self.other_colors)
            else:
                printout = self.try_str(obj) if event.detached else self.try_repr(obj)

            if frame_symbols >= symbols:
                if first:
                    self.output(
                        '{}{}{}{KIND}{:9} {VARS}[{VARS-NAME}{} {VARS}=> {RESET}{}{VARS}]{RESET}\n',
                        pid_prefix,
                        thread_prefix,
                        filename_prefix,
                        event.kind,
                        code,
                        printout,
                    )
                    first = False
                else:
                    self.output(
                        '{}{}{}{CONT}...       {VARS}[{VARS-NAME}{} {VARS}=> {RESET}{}{VARS}]{RESET}\n',
                        pid_prefix,
                        thread_prefix,
                        empty_filename_prefix,
                        code,
                        printout,
                    )


class VarsSnooper(ColorStreamAction):
    """
    A PySnooper-inspired action, similar to :class:`~hunter.actions.VarsPrinter`, but only show variable changes.

    .. warning:: Should be considered experimental. Use judiciously.

        * It stores reprs for all seen variables, therefore it can use lots of memory.
        * Will leak memory if you filter the return events (eg: ``~Q(kind="return")``).
        * Not thoroughly tested. May misbehave on code with closures/nonlocal variables.

    Args:
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        force_colors (bool): Force coloring. Default: ``False``.
        repr_limit (bool): Limit length of ``repr()`` output. Default: ``512``.
        repr_func (string or callable): Function to use instead of ``repr``.
            If string must be one of 'repr' or 'safe_repr'. Default: ``'safe_repr'``.
    """

    def __init__(self, **options):
        super(VarsSnooper, self).__init__(**options)
        self.stored_reprs = defaultdict(dict)

    def __call__(self, event):
        """
        Handle event and print the specified variables.
        """
        first = True

        pid_prefix = self.pid_prefix()
        thread_prefix = self.thread_prefix(event)
        filename_prefix = self.filename_prefix(event)
        empty_filename_prefix = self.filename_prefix()

        current_reprs = {
            name: self.try_str(value) if event.detached else self.try_repr(value)
            for name, value in event.locals.items()
        }
        scope_key = event.code or event.function
        scope = self.stored_reprs[scope_key]
        for name, current_repr in sorted(current_reprs.items()):
            previous_repr = scope.get(name)
            if previous_repr is None:
                scope[name] = current_repr
                if first:
                    self.output(
                        '{}{}{}{KIND}{:9} {VARS}[{VARS-NAME}{} {VARS}:= {RESET}{}{VARS}]{RESET}\n',
                        pid_prefix,
                        thread_prefix,
                        filename_prefix,
                        event.kind,
                        name,
                        current_repr,
                    )
                    first = False
                else:
                    self.output(
                        '{}{}{}{CONT}{:9} {VARS}[{VARS-NAME}{} {VARS}:= {RESET}{}{VARS}]{RESET}\n',
                        pid_prefix,
                        thread_prefix,
                        empty_filename_prefix,
                        '...',
                        name,
                        current_repr,
                    )
            elif previous_repr != current_repr:
                scope[name] = current_repr
                if first:
                    self.output(
                        '{}{}{}{KIND}{:9} {VARS}[{VARS-NAME}{} {VARS}: {RESET}{}{VARS} => {RESET}{}{VARS}]{RESET}\n',
                        pid_prefix,
                        thread_prefix,
                        filename_prefix,
                        event.kind,
                        name,
                        previous_repr,
                        current_repr,
                    )
                    first = False
                else:
                    self.output(
                        '{}{}{}{CONT}{:9} {VARS}[{VARS-NAME}{} {VARS}: {RESET}{}{VARS} => {RESET}{}{VARS}]{RESET}\n',
                        pid_prefix,
                        thread_prefix,
                        empty_filename_prefix,
                        '...',
                        name,
                        previous_repr,
                        current_repr,
                    )
        if event.kind == 'return':
            del self.stored_reprs[scope_key]


RETURN_VALUE = opcode.opmap['RETURN_VALUE']
if not PY3:
    RETURN_VALUE = chr(RETURN_VALUE)


class ErrorSnooper(CodePrinter):
    """
    An action that prints events around silenced exceptions. Note that it inherits the output of :class:`~hunter.actions.CodePrinter` so no
    fancy call indentation.

    .. warning::

        Should be considered experimental. May show lots of false positives especially if you're tracing lots of clumsy code like:

        .. sourcecode:: python

            try:
                stuff = something[key]
            except KeyError:
                stuff = "default"

    Args:
        max_backlog (int): Maximum number of events to record and display before the silenced exception is raised.
            Set to 0 to disable and get a speed boost. Default: ``10``.
        max_events (int): Maximum number of events to record and display for each detected silenced exception. Default: ``50``.
        max_depth (int): Increase if you want to drill into subsequent calls after an exception is raised. If you increase this you might
            want to also increase ``max_events`` since subsequent calls may have so many events you won't get to see the return event.
            Default: ``0`` (doesn't drill into any calls).

        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        force_colors (bool): Force coloring. Default: ``False``.
        repr_limit (bool): Limit length of ``repr()`` output. Default: ``512``.
        repr_func (string or callable): Function to use instead of ``repr``.
            If string must be one of 'repr' or 'safe_repr'. Default: ``'safe_repr'``.

    .. versionadded:: 3.1.0
    """

    def __init__(self, *args, **kwargs):
        self.max_backlog = kwargs.pop('max_backlog', 10)
        self.backlog = collections.deque(maxlen=self.max_backlog)
        self.max_events = kwargs.pop('max_events', 50)
        self.max_depth = kwargs.pop('max_depth', 0)
        self.origin = None
        self.events = None
        super(ErrorSnooper, self).__init__(*args, **kwargs)

    def __call__(self, event):
        if self.max_backlog:
            detached_event = event.detach(self.try_repr)
            self.backlog.append(detached_event)
        else:
            detached_event = None

        if event.kind == 'exception':  # something interesting happened ;)
            if detached_event is None:
                detached_event = event.detach(self.try_repr)
            if self.origin:
                self.events.append(detached_event)
                if self.origin.depth > event.depth:
                    self.origin = detached_event
            else:
                self.events = list(self.backlog)
                self.origin = detached_event
        elif self.origin:
            if event.kind == 'return':
                if detached_event is None:
                    detached_event = event.detach(self.try_repr)
                self.events.append(detached_event)
                if event.depth == self.origin.depth - 1:  # stop if the same function returned (depth is -1)
                    if event.instruction == RETURN_VALUE:
                        self.dump_events()
                        self.output('{BRIGHT}{fore(BLACK)}{} function exit{RESET}\n', '-' * 46)
                    self.origin = None
                    self.events = None
            elif event.depth > self.origin.depth + self.max_depth:  # too many details
                return
            elif len(self.events) > self.max_events:
                self.dump_events()
                self.output('{BRIGHT}{fore(BLACK)}{} too many lines{RESET}\n', '-' * 46)
            else:
                if detached_event is None:
                    detached_event = event.detach(self.try_repr)
                self.events.append(detached_event)

    def dump_events(self):
        self.output('{BRIGHT}{fore(BLUE)}{} tracing {fore(YELLOW)}{}{fore(BLUE)} on {fore(RED)}{}{RESET}\n',
                    '>' * 46, self.origin.function, self.origin.arg)
        for event in self.events:
            super(ErrorSnooper, self).__call__(event)
        self.origin = None
        self.events = None


class StackPrinter(ColorStreamAction):
    """
    An action that prints a one-line stacktrace.

    Args:
        depth (int): The maximum number of frames to show.
        limit (int): The maximum number of components to show in path. Eg: ``limit=2`` means it will show 1 parent: ``foo/bar.py``.
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        force_colors (bool): Force coloring. Default: ``False``.
        repr_limit (bool): Limit length of ``repr()`` output. Default: ``512``.
        repr_func (string or callable): Function to use instead of ``repr``.
            If string must be one of 'repr' or 'safe_repr'. Default: ``'safe_repr'``.
    """

    def __init__(self, depth=15, limit=2, **options):
        self.limit = limit
        self.depth = depth
        super(StackPrinter, self).__init__(**options)

    def __call__(self, event):
        """
        Handle event and print the stack.
        """
        pid_prefix = self.pid_prefix()
        thread_prefix = self.thread_prefix(event)
        filename_prefix = self.filename_prefix(event).rstrip()
        sep = os.path.sep

        if event.frame and event.frame.f_back:
            template = '{}{}{}{CONT}:{BRIGHT}{fore(BLUE)}%s {KIND}<={RESET} %s' % (
                event.function,
                ' {KIND}<={RESET} '.join(
                    '%s{CONT}:{RESET}%s{CONT}:{BRIGHT}{fore(BLUE)}%s' % (
                        '/'.join(frame.f_code.co_filename.split(sep)[-self.limit:]),
                        frame.f_lineno,
                        frame.f_code.co_name
                    )
                    for frame in islice(frame_iterator(event.frame.f_back), self.depth)
                )
            )
        else:
            template = '{}{}{}{CONT}:{BRIGHT}{fore(BLUE)}%s {KIND}<= {BRIGHT}{fore(YELLOW)}no frames available {NORMAL}(detached=%s)' % (
                event.function,
                event.detached,
            )
        template += '{RESET}\n'
        self.output(
            template,
            pid_prefix,
            thread_prefix,
            filename_prefix,
        )
