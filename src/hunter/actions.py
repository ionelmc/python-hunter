from __future__ import absolute_import

import ast
import os
import sys
import threading
from collections import defaultdict
from itertools import chain
from os import getpid

from colorama import AnsiToWin32
from colorama import Back
from colorama import Fore
from colorama import Style
from six import string_types

from .config import DEFAULTS
from .util import rudimentary_repr

try:
    from threading import get_ident
except ImportError:
    from thread import get_ident

EVENT_COLORS = {
    'reset': Style.RESET_ALL,
    'normal': Style.NORMAL,
    'filename': '',
    'colon': Style.BRIGHT + Fore.BLACK,
    'lineno': Style.RESET_ALL,
    'kind': Fore.CYAN,
    'continuation': Style.BRIGHT + Fore.BLUE,
    'call': Style.BRIGHT + Fore.BLUE,
    'return': Style.BRIGHT + Fore.GREEN,
    'exception': Style.BRIGHT + Fore.RED,
    'detail': Style.NORMAL,
    'vars': Style.RESET_ALL + Fore.MAGENTA,
    'vars-name': Style.BRIGHT,
    'internal-failure': Style.BRIGHT + Back.RED + Fore.RED,
    'internal-detail': Fore.WHITE,
    'source-failure': Style.BRIGHT + Back.YELLOW + Fore.YELLOW,
    'source-detail': Fore.WHITE,
}
CODE_COLORS = {
    'call': Fore.RESET + Style.BRIGHT,
    'line': Fore.RESET,
    'return': Fore.YELLOW,
    'exception': Fore.RED,
}
NO_COLORS = {key: '' for key in chain(CODE_COLORS, EVENT_COLORS)}
MISSING = type('MISSING', (), {'__repr__': lambda _: '?'})()


class Action(object):
    def __call__(self, event):
        raise NotImplementedError()


class Debugger(Action):
    """
    An action that starts ``pdb``.
    """
    def __init__(self, klass=DEFAULTS.get('klass', lambda **kwargs: __import__('pdb').Pdb(**kwargs)), **kwargs):
        self.klass = klass
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


DEFAULT_STREAM = sys.stderr


class ColorStreamAction(Action):
    _stream_cache = {}
    _stream = None
    _tty = None

    def __init__(self,
                 stream=DEFAULTS.get('stream', None),
                 force_colors=DEFAULTS.get('force_colors', False),
                 force_pid=DEFAULTS.get('force_pid', False),
                 filename_alignment=DEFAULTS.get('filename_alignment', 40),
                 thread_alignment=DEFAULTS.get('thread_alignment', 12),
                 pid_alignment=DEFAULTS.get('pid_alignment', 9),
                 repr_limit=DEFAULTS.get('repr_limit', 1024),
                 repr_unsafe=DEFAULTS.get('repr_unsafe', False)):
        self.force_colors = force_colors
        self.force_pid = force_pid
        self.stream = DEFAULT_STREAM if stream is None else stream
        self.filename_alignment = filename_alignment
        self.thread_alignment = thread_alignment
        self.pid_alignment = pid_alignment
        self.repr_limit = repr_limit
        self.repr_unsafe = repr_unsafe
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
            and self.repr_unsafe == other.repr_unsafe
        )

    def __str__(self):
        return '{0.__class__.__name__}(stream={0.stream}, force_colors={0.force_colors}, ' \
               'filename_alignment={0.filename_alignment}, thread_alignment={0.thread_alignment}, ' \
               'pid_alignment={0.pid_alignment} repr_limit={0.repr_limit}, ' \
               'repr_unsafe={0.repr_unsafe})'.format(self)

    def __repr__(self):
        return '{0.__class__.__name__}(stream={0.stream!r}, force_colors={0.force_colors!r}, ' \
               'filename_alignment={0.filename_alignment!r}, thread_alignment={0.thread_alignment!r}, ' \
               'pid_alignment={0.pid_alignment!r} repr_limit={0.repr_limit!r}, ' \
               'repr_unsafe={0.repr_unsafe!r})'.format(self)

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, value):
        if isinstance(value, string_types):
            if value in self._stream_cache:
                value = self._stream_cache[value]
            else:
                value = self._stream_cache[value] = open(value, 'a', buffering=0)

        isatty = getattr(value, 'isatty', None)
        if self.force_colors or (isatty and isatty() and os.name != 'java'):
            self._stream = AnsiToWin32(value, strip=False)
            self._tty = True
            self.event_colors = EVENT_COLORS
            self.code_colors = CODE_COLORS
        else:
            self._tty = False
            self._stream = value
            self.event_colors = NO_COLORS
            self.code_colors = NO_COLORS

    def _safe_repr(self, obj):
        limit = self.repr_limit
        try:
            if self.repr_unsafe:
                s = repr(obj)
            else:
                s = rudimentary_repr(obj)

            s = s.replace('\n', r'\n')
            if len(s) > limit:
                cutoff = limit // 2
                return "{} {continuation}[...]{reset} {}".format(s[:cutoff], s[-cutoff:], **self.event_colors)
            else:
                return s
        except Exception as exc:
            return "{internal-failure}!!! FAILED REPR: {internal-detail}{!r}{reset}".format(exc, **self.event_colors)
        else:
            return "<{} object at 0x{continuation}[...]{reset} {}".format(s[:cutoff], s[-cutoff:], **self.event_colors)


class CodePrinter(ColorStreamAction):
    """
    An action that just prints the code being executed.

    Args:
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        force_colors (bool): Force coloring. Default: ``False``.
        repr_limit (bool): Limit length of ``repr()`` output. Default: ``512``.
    """
    def _safe_source(self, event):
        try:
            lines = event._raw_fullsource.rstrip().splitlines()
            if lines:
                return lines
            else:
                return "{source-failure}??? NO SOURCE: {source-detail}" \
                       "Source code string for module {!r} is empty.".format(event.module, **self.event_colors),
            return lines
        except Exception as exc:
            return "{source-failure}??? NO SOURCE: {source-detail}{!r}".format(exc, **self.event_colors),

    def _format_filename(self, event):
        filename = event.filename or "<???>"
        if len(filename) > self.filename_alignment:
            filename = '[...]{}'.format(filename[5 - self.filename_alignment:])
        return filename

    def __call__(self, event):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also
        prints values.
        """
        lines = self._safe_source(event)
        self.seen_threads.add(get_ident())
        if event.tracer.threading_support is False:
            threading_support = False
        elif event.tracer.threading_support:
            threading_support = True
        else:
            threading_support = len(self.seen_threads) > 1
        thread_name = threading.current_thread().name if threading_support else ''
        thread_align = self.thread_alignment if threading_support else ''

        pid = getpid()
        if self.force_pid or self.seen_pid != pid:
            pid = "[{}] ".format(pid)
            pid_align = self.pid_alignment
        else:
            pid = pid_align = ''

        self.stream.write(
            "{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} "
            "{code}{}{reset}\n".format(
                self._format_filename(event),
                event.lineno,
                event.kind,
                lines[0],
                pid=pid, pid_align=pid_align,
                thread=thread_name, thread_align=thread_align,
                align=self.filename_alignment,
                code=self.code_colors[event.kind],
                **self.event_colors))

        for line in lines[1:]:
            self.stream.write(
                "{pid:{pid_align}}{thread:{thread_align}}{:>{align}}       {kind}{:9} {code}{}{reset}\n".format(
                    "",
                    r"   |",
                    line,
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    code=self.code_colors[event.kind],
                    **self.event_colors))

        if event.kind in ('return', 'exception'):
            self.stream.write(
                "{pid:{pid_align}}{thread:{thread_align}}{:>{align}}       {continuation}{:9} {color}{} "
                "value: {detail}{}{reset}\n".format(
                    "",
                    "...",
                    event.kind,
                    self._safe_repr(event.arg),
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    color=self.event_colors[event.kind],
                    **self.event_colors))


class CallPrinter(CodePrinter):
    """
    An action that just prints the code being executed, but unlike :obj:`hunter.CodePrinter` it indents based on
    callstack depth and it also shows ``repr()`` of function arguments.

    Args:
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        force_colors (bool): Force coloring. Default: ``False``.
        repr_limit (bool): Limit length of ``repr()`` output. Default: ``512``.

    .. versionadded:: 1.2.0
    """

    def __init__(self, **options):
        super(CallPrinter, self).__init__(**options)
        self.locals = defaultdict(list)

    def __call__(self, event):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also
        prints values.
        """
        filename = self._format_filename(event)
        ident = event.module, event.function

        self.seen_threads.add(get_ident())
        if event.tracer.threading_support is False:
            threading_support = False
        elif event.tracer.threading_support:
            threading_support = True
        else:
            threading_support = len(self.seen_threads) > 1
        thread = threading.current_thread()
        thread_name = thread.name if threading_support else ''
        thread_align = self.thread_alignment if threading_support else ''
        stack = self.locals[thread.ident]

        pid = getpid()
        if self.force_pid or self.seen_pid != pid:
            pid = "[{}] ".format(pid)
            pid_align = self.pid_alignment
        else:
            pid = pid_align = ''

        if event.kind == 'call':
            code = event.code
            stack.append(ident)
            self.stream.write(
                "{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} "
                "{}{call}=>{normal} {}({}{call}{normal}){reset}\n".format(
                    filename,
                    event.lineno,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.function,
                    ', '.join('{vars}{vars-name}{0}{vars}={reset}{1}'.format(
                        var,
                        self._safe_repr(event.locals.get(var, MISSING)),
                        **self.event_colors
                    ) for var in code.co_varnames[:code.co_argcount]),
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    **self.event_colors
                ))
        elif event.kind == 'exception':
            self.stream.write(
                "{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} "
                "{exception}{} !{normal} {}: {reset}{}\n".format(
                    filename,
                    event.lineno,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.function,
                    self._safe_repr(event.arg),
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    **self.event_colors
                ))

        elif event.kind == 'return':
            self.stream.write(
                "{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} "
                "{return}{}<={normal} {}: {reset}{}\n".format(
                    filename,
                    event.lineno,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.function,
                    self._safe_repr(event.arg),
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    **self.event_colors
                ))
            if stack and stack[-1] == ident:
                stack.pop()
        else:
            self.stream.write(
                "{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {reset}{}{}\n".format(
                    filename,
                    event.lineno,
                    event.kind,
                    '   ' * len(stack),
                    event.source.strip(),
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    code=self.code_colors[event.kind],
                    **self.event_colors
                ))


class VarsPrinter(ColorStreamAction):
    """
    An action that prints local variables and optionally global variables visible from the current executing frame.

    Args:
        *names (strings): Names to evaluate. Expressions can be used (will only try to evaluate if all the variables are
            present on the frame.
        globals (bool): Allow access to globals. Default: ``False`` (only looks at locals).
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        force_colors (bool): Force coloring. Default: ``False``.
        repr_limit (bool): Limit length of ``repr()`` output. Default: ``512``.
    """

    def __init__(self, *names, **options):
        if not names:
            raise TypeError("VarsPrinter requires at least one variable name/expression.")
        self.names = {
            name: set(self._iter_symbols(name))
            for name in names
        }
        self.globals = options.pop('globals', DEFAULTS.get('globals', False))
        super(VarsPrinter, self).__init__(**options)

    @staticmethod
    def _iter_symbols(code):
        """
        Iterate all the variable names in the given expression.

        Example:

        * ``self.foobar`` yields ``self``
        * ``self[foobar]`` yields `self`` and ``foobar``
        """
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.Name):
                yield node.id

    def __call__(self, event):
        """
        Handle event and print the specified variables.
        """
        first = True
        frame_symbols = set(event.locals)
        if self.globals:
            frame_symbols |= set(event.globals)

        self.seen_threads.add(get_ident())
        if event.tracer.threading_support is False:
            threading_support = False
        elif event.tracer.threading_support:
            threading_support = True
        else:
            threading_support = len(self.seen_threads) > 1
        thread_name = threading.current_thread().name if threading_support else ''
        thread_align = self.thread_alignment if threading_support else ''

        pid = getpid()
        if self.force_pid or self.seen_pid != pid:
            pid = "[{}] ".format(pid)
            pid_align = self.pid_alignment
        else:
            pid = pid_align = ''

        for code, symbols in self.names.items():
            try:
                obj = eval(code, event.globals if self.globals else {}, event.locals)
            except AttributeError:
                continue
            except Exception as exc:
                printout = "{internal-failure}FAILED EVAL: {internal-detail}{!r}".format(exc, **self.event_colors)
            else:
                printout = self._safe_repr(obj)

            if frame_symbols >= symbols:
                self.stream.write(
                    "{pid:{pid_align}}{thread:{thread_align}}{:>{align}}       "
                    "{vars}{:9} {vars-name}{} {vars}=> {reset}{}{reset}\n".format(
                        "",
                        "vars" if first else "...",
                        code,
                        printout,
                        pid=pid, pid_align=pid_align,
                        thread=thread_name, thread_align=thread_align,
                        align=self.filename_alignment,
                        **self.event_colors
                    )
                )
                first = False
