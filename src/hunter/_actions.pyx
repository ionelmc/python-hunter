# cython: linetrace=True, language_level=3str
from __future__ import absolute_import

import io
import os
import threading
import types
from collections import defaultdict
from collections import deque
from os import getpid

from colorama import AnsiToWin32

from . import config
from .util import BUILTIN_SYMBOLS
from .util import CODE_COLORS
from .util import EVENT_COLORS
from .util import MISSING
from .util import NO_COLORS
from .util import STRING_TYPES
from .util import builtins
from .util import iter_symbols

from ._event cimport Event

try:
    from threading import get_ident
except ImportError:
    from thread import get_ident


__all__ = ['Action', 'Debugger', 'Manhole', 'CodePrinter', 'CallPrinter', 'VarsPrinter']


cpdef inline safe_repr(obj, int maxdepth=5):
    if not maxdepth:
        return '...'
    obj_type = type(obj)
    cdef int newdepth = maxdepth - 1
    cdef list items

    # specifically handle few of the container builtins that would normally do repr on contained values
    if isinstance(obj, dict):
        items = []
        for k, v in obj.items():
            items.append('%s: %s' % (
                safe_repr(k, maxdepth),
                safe_repr(v, newdepth)
            ))
        if obj_type is not dict:
            return '%s({%s})' % (
                obj_type.__name__,
                ', '.join(items))
        else:
            return '{%s}' % ', '.join(items)
    elif isinstance(obj, list):
        items = []
        for i in obj:
            items.append(safe_repr(i, newdepth))
        if obj_type is not list:
            return '%s([%s])' % (obj_type.__name__, ', '.join(items))
        else:
            return '[%s]' % ', '.join(items)
    elif isinstance(obj, tuple):
        items = []
        for i in obj:
            items.append(safe_repr(i, newdepth))
        if obj_type is not tuple:
            return '%s(%s%s)' % (
                obj_type.__name__,
                ', '.join(items),
                ',' if len(obj) == 1 else '')
        else:
            return '(%s%s)' % (', '.join(items), ',' if len(obj) == 1 else '')
    elif isinstance(obj, set):
        items = []
        for i in obj:
            items.append(safe_repr(i, newdepth))
        if obj_type is not set:
            return '%s({%s})' % (obj_type.__name__, ', '.join(items))
        else:
            return '{%s}' % ', '.join(items)
    elif isinstance(obj, frozenset):
        items = []
        for i in obj:
            items.append(safe_repr(i, newdepth))
        return '%s({%s})' % (obj_type.__name__, ', '.join(items))
    elif isinstance(obj, deque):
        items = []
        for i in obj:
            items.append(safe_repr(i, newdepth))
        return '%s([%s])' % (obj_type.__name__, ', '.join(items))
    elif isinstance(obj, BaseException):
        items = []
        for i in obj.args:
            items.append(safe_repr(i, newdepth))
        return '%s(%s)' % (obj_type.__name__, ', '.join(items))
    elif obj_type in (type, types.ModuleType,
                      types.FunctionType, types.MethodType,
                      types.BuiltinFunctionType, types.BuiltinMethodType,
                      io.IOBase):
        # hardcoded list of safe things. note that isinstance ain't used
        # (we don't trust subclasses to do the right thing in __repr__)
        return repr(obj)
    elif not hasdict(obj_type, obj):
        return repr(obj)
    else:
        # if the object has a __dict__ then it's probably an instance of a pure python class, assume bad things
        #  with side-effects will be going on in __repr__ - use the default instead (object.__repr__)
        return object.__repr__(obj)

BUILTIN_REPR_FUNCS = {
    'repr': repr,
    'safe_repr': safe_repr
}


cpdef inline hasdict(obj_type, obj, tolerance=25):
    """
    A contrived mess to check that object doesn't have a __dit__ but avoid checking it if any ancestor is evil enough to
    explicitly define __dict__ (like apipkg.ApiModule has __dict__ as a property).
    """
    ancestor_types = deque()
    while obj_type is not type and tolerance:
        ancestor_types.appendleft(obj_type)
        obj_type = type(obj_type)
        tolerance -= 1
    for ancestor in ancestor_types:
        __dict__ = getattr(ancestor, '__dict__', None)
        if __dict__ is not None:
            if '__dict__' in __dict__:
                return True
    return hasattr(obj, '__dict__')


cdef class Action:
    def __call__(self, event):
        raise NotImplementedError()


cdef class Debugger(Action):
    """
    An action that starts ``pdb``.
    """
    def __init__(self, klass=config.Default('klass', lambda **kwargs: __import__('pdb').Pdb(**kwargs)), **kwargs):
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


cdef class Manhole(Action):
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


cdef dict ColorStreamAction_STREAM_CACHE = {}

cdef class ColorStreamAction(Action):
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
        self.stream = config.DEFAULT_STREAM if config.resolve(stream) is None else stream
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
        if isinstance(value, STRING_TYPES):
            if value in ColorStreamAction_STREAM_CACHE:
                value = ColorStreamAction_STREAM_CACHE[value]
            else:
                value = ColorStreamAction_STREAM_CACHE[value] = open(value, 'a', buffering=0)

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

    cdef inline _try_repr(self, obj):
        cdef str s
        limit = self.repr_limit
        try:
            repr_func = self.repr_func
            if repr_func is safe_repr:
                s = safe_repr(obj)
            else:
                s = repr_func(obj)
            s = s.replace('\n', r'\n')
            if len(s) > limit:
                cutoff = limit // 2
                return '{} {continuation}[...]{reset} {}'.format(s[:cutoff], s[-cutoff:], **self.event_colors)
            else:
                return s
        except Exception as exc:
            return '{internal-failure}!!! FAILED REPR: {internal-detail}{!r}{reset}'.format(exc, **self.event_colors)

    cdef inline _format_filename(self, event):
        filename = event.filename or '<???>'
        if len(filename) > self.filename_alignment:
            filename = '[...]{}'.format(filename[5 - self.filename_alignment:])
        return filename


cdef class CodePrinter(ColorStreamAction):
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
    cdef inline _safe_source(self, event):
        try:
            lines = event._raw_fullsource.rstrip().splitlines()
            if lines:
                return lines
            else:
                return '{source-failure}??? NO SOURCE: {source-detail}' \
                       'Source code string for module {!r} is empty.'.format(event.module, **self.event_colors),
        except Exception as exc:
            return '{source-failure}??? NO SOURCE: {source-detail}{!r}'.format(exc, **self.event_colors),

    def __call__(self, event):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also
        prints values.
        """
        fast_CodePrinter_call(self, event)

cdef inline fast_CodePrinter_call(CodePrinter self, Event event):
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
            pid = '[{}] '.format(pid)
            pid_align = self.pid_alignment
        else:
            pid = pid_align = ''

        self.stream.write(
            '{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} '
            '{code}{}{reset}\n'.format(
                self._format_filename(event),
                event.lineno,
                event.kind,
                lines[0],
                pid=pid, pid_align=pid_align,
                thread=thread_name, thread_align=thread_align,
                align=self.filename_alignment,
                code=self.code_colors[event.kind],
                **self.event_colors))
        if len(lines) > 1:
            for line in lines[1:-1]:
                self.stream.write(
                    '{pid:{pid_align}}{thread:{thread_align}}{:>{align}}       {kind}{:9} {code}{}{reset}\n'.format(
                        '',
                        '   |',
                        line,
                        pid=pid, pid_align=pid_align,
                        thread=thread_name, thread_align=thread_align,
                        align=self.filename_alignment,
                        code=self.code_colors[event.kind],
                        **self.event_colors))
            self.stream.write(
                '{pid:{pid_align}}{thread:{thread_align}}{:>{align}}       {kind}{:9} {code}{}{reset}\n'.format(
                    '',
                    '   *',
                    lines[-1],
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    code=self.code_colors[event.kind],
                    **self.event_colors))

        if event.kind in ('return', 'exception'):
            self.stream.write(
                '{pid:{pid_align}}{thread:{thread_align}}{:>{align}}       {continuation}{:9} {color}{} '
                'value: {detail}{}{reset}\n'.format(
                    '',
                    '...',
                    event.kind,
                    self._try_repr(event.arg),
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    color=self.event_colors[event.kind],
                    **self.event_colors))

cdef class CallPrinter(CodePrinter):
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

    def __init__(self, **options):
        super(CallPrinter, self).__init__(**options)
        self.locals = defaultdict(list)

    def __call__(self, event):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also
        prints values.
        """
        fast_CallPrinter_call(self, event)

cdef inline fast_CallPrinter_call(CallPrinter self, Event event):
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
            pid = '[{}] '.format(pid)
            pid_align = self.pid_alignment
        else:
            pid = pid_align = ''

        if event.kind == 'call':
            code = event.code
            stack.append(ident)
            self.stream.write(
                '{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} '
                '{}{call}=>{normal} {}({}{call}{normal}){reset}\n'.format(
                    filename,
                    event.lineno,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.function,
                    ', '.join('{vars}{vars-name}{0}{vars}={reset}{1}'.format(
                        var,
                        self._try_repr(event.locals.get(var, MISSING)),
                        **self.event_colors
                    ) for var in code.co_varnames[:code.co_argcount]),
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    **self.event_colors
                ))
        elif event.kind == 'exception':
            self.stream.write(
                '{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} '
                '{exception}{} !{normal} {}: {reset}{}\n'.format(
                    filename,
                    event.lineno,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.function,
                    self._try_repr(event.arg),
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    **self.event_colors
                ))

        elif event.kind == 'return':
            self.stream.write(
                '{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} '
                '{return}{}<={normal} {}: {reset}{}\n'.format(
                    filename,
                    event.lineno,
                    event.kind,
                    '   ' * (len(stack) - 1),
                    event.function,
                    self._try_repr(event.arg),
                    pid=pid, pid_align=pid_align,
                    thread=thread_name, thread_align=thread_align,
                    align=self.filename_alignment,
                    **self.event_colors
                ))
            if stack and stack[-1] == ident:
                stack.pop()
        else:
            self.stream.write(
                '{pid:{pid_align}}{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} '
                '{reset}{}{}\n'.format(
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


cdef class VarsPrinter(ColorStreamAction):
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
        fast_VarsPrinter_call(self, event)

cdef inline fast_VarsPrinter_call(VarsPrinter self, Event event):
        filename = self._format_filename(event)
        first = True
        frame_symbols = set(event.locals)
        frame_symbols.update(BUILTIN_SYMBOLS)
        frame_symbols.update(event.globals)

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
            pid = '[{}] '.format(pid)
            pid_align = self.pid_alignment
        else:
            pid = pid_align = ''

        for code, symbols in self.names.items():
            try:
                obj = eval(code, dict(vars(builtins), **event.globals), event.locals)
            except AttributeError:
                continue
            except Exception as exc:
                printout = '{internal-failure}FAILED EVAL: {internal-detail}{!r}'.format(exc, **self.event_colors)
            else:
                printout = self._try_repr(obj)

            if frame_symbols >= symbols:
                if first:
                    self.stream.write(
                        '{pid:{pid_align}}{thread:{thread_align}}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {vars}['
                        '{vars-name}{} {vars}=> {reset}{}{vars}]{reset}\n'.format(
                            filename,
                            event.lineno,
                            event.kind,
                            code,
                            printout,
                            pid=pid, pid_align=pid_align,
                            thread=thread_name, thread_align=thread_align,
                            align=self.filename_alignment,
                            **self.event_colors
                        )
                    )
                else:
                    self.stream.write(
                        '{pid:{pid_align}}{thread:{thread_align}}{:>{align}}       {continuation}...       {vars}['
                        '{vars-name}{} {vars}=> {reset}{}{vars}]{reset}\n'.format(
                            '',
                            code,
                            printout,
                            pid=pid, pid_align=pid_align,
                            thread=thread_name, thread_align=thread_align,
                            align=self.filename_alignment,
                            **self.event_colors
                        )
                    )
                first = False


cdef class VarsSnooper(ColorStreamAction):
    def __init__(self, **options):
        super(VarsSnooper, self).__init__(**options)
        self.stored_reprs = defaultdict(dict)

    def __call__(self, event):
        """
        Handle event and print the specified variables.
        """
        fast_VarsSnooper_call(self, event)

cdef inline fast_VarsSnooper_call(VarsSnooper self, Event event):
        filename = self._format_filename(event)
        first = True

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
            pid = '[{}] '.format(pid)
            pid_align = self.pid_alignment
        else:
            pid = pid_align = ''

        current_reprs = {
            name: self._try_repr(value)
            for name, value in event.locals.items()
        }
        scope_key = event.code or event.function
        scope = self.stored_reprs[scope_key]
        for name, current_repr in sorted(current_reprs.items()):
            previous_repr = scope.get(name)
            if previous_repr is None:
                scope[name] = current_repr
                if first:
                    self.stream.write(
                        '{pid:{pid_align}}{thread:{thread_align}}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {vars}['
                        '{vars-name}{} {vars}:= {reset}{}{vars}]{reset}\n'.format(
                            filename,
                            event.lineno,
                            event.kind,
                            name,
                            current_repr,
                            pid=pid, pid_align=pid_align,
                            thread=thread_name, thread_align=thread_align,
                            align=self.filename_alignment,
                            **self.event_colors
                        )
                    )
                    first = False
                else:
                    self.stream.write(
                        '{pid:{pid_align}}{thread:{thread_align}}{:>{align}}       {continuation}...       {vars}['
                        '{vars-name}{} {vars}:= {reset}{}{vars}]{reset}\n'.format(
                            '',
                            name,
                            current_repr,
                            pid=pid, pid_align=pid_align,
                            thread=thread_name, thread_align=thread_align,
                            align=self.filename_alignment,
                            **self.event_colors
                        )
                    )
            elif previous_repr != current_repr:
                scope[name] = current_repr
                if first:
                    self.stream.write(
                        '{pid:{pid_align}}{thread:{thread_align}}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {vars}['
                        '{vars-name}{} {vars}: {reset}{}{vars} => {reset}{}{vars}]{reset}\n'.format(
                            filename,
                            event.lineno,
                            event.kind,
                            name,
                            previous_repr,
                            current_repr,
                            pid=pid, pid_align=pid_align,
                            thread=thread_name, thread_align=thread_align,
                            align=self.filename_alignment,
                            **self.event_colors
                        )
                    )
                    first = False
                else:
                    self.stream.write(
                        '{pid:{pid_align}}{thread:{thread_align}}{:>{align}}       {continuation}...       {vars}['
                        '{vars-name}{} {vars}: {reset}{}{vars} => {reset}{}{vars}]{reset}\n'.format(
                            '',
                            name,
                            previous_repr,
                            current_repr,
                            pid=pid, pid_align=pid_align,
                            thread=thread_name, thread_align=thread_align,
                            align=self.filename_alignment,
                            **self.event_colors
                        )
                    )
        if event.kind == 'return':
            del self.stored_reprs[scope_key]
