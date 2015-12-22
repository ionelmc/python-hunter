from __future__ import absolute_import

import ast
import os
import pdb
import sys

from colorama import AnsiToWin32
from colorama import Back
from colorama import Fore
from colorama import Style
from fields import Fields
from six import string_types

DEFAULT_MIN_FILENAME_ALIGNMENT = 40
NO_COLORS = {
    'reset': '',
    'filename': '',
    'colon': '',
    'lineno': '',
    'kind': '',
    'continuation': '',
    'return': '',
    'exception': '',
    'detail': '',
    'vars': '',
    'vars-name': '',
    'call': '',
    'line': '',
    'internal-failure': '',
    'internal-detail': '',
    'source-failure': '',
    'source-detail': '',
}
EVENT_COLORS = {
    'reset': Style.RESET_ALL,
    'filename': '',
    'colon': Fore.BLACK + Style.BRIGHT,
    'lineno': Style.RESET_ALL,
    'kind': Fore.CYAN,
    'continuation': Fore.BLUE,
    'return': Style.BRIGHT + Fore.GREEN,
    'exception': Style.BRIGHT + Fore.RED,
    'detail': Style.NORMAL,
    'vars': Style.RESET_ALL + Fore.MAGENTA,
    'vars-name': Style.BRIGHT,
    'internal-failure': Back.RED + Style.BRIGHT + Fore.RED,
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


class Action(object):
    def __call__(self, event):
        raise NotImplementedError()


class Debugger(Fields.klass.kwargs, Action):
    """
    An action that starts ``pdb``.
    """

    def __init__(self, klass=pdb.Pdb, **kwargs):
        self.klass = klass
        self.kwargs = kwargs

    def __call__(self, event):
        """
        Runs a ``pdb.set_trace`` at the matching frame.
        """
        self.klass(**self.kwargs).set_trace(event.frame)


class ColorStreamAction(Action):
    _stream_cache = {}
    _stream = None
    _tty = None
    default_stream = sys.stderr
    force_colors = False

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
            self._stream = AnsiToWin32(value)
            self._tty = True
            self.event_colors = EVENT_COLORS
            self.code_colors = CODE_COLORS
        else:
            self._tty = False
            self._stream = value
            self.event_colors = NO_COLORS
            self.code_colors = NO_COLORS

    def _safe_repr(self, obj):
        try:
            return repr(obj)
        except Exception as exc:
            return "{internal-failure}!!! FAILED REPR: {internal-detail}{!r}".format(exc, **self.event_colors)


class CodePrinter(Fields.stream.filename_alignment, ColorStreamAction):
    """
    An action that just prints the code being executed.

    Args:
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
    """

    def __init__(self,
                 stream=ColorStreamAction.default_stream, force_colors=False,
                 filename_alignment=DEFAULT_MIN_FILENAME_ALIGNMENT):
        self.stream = stream
        self.force_colors = force_colors
        self.filename_alignment = max(5, filename_alignment)

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

    def __call__(self, event, sep=os.path.sep, join=os.path.join):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also
        prints values.
        """
        filename = event.filename or "<???>"
        if len(filename) > self.filename_alignment:
            filename = '[...]{}'.format(filename[5 - self.filename_alignment:])

        # context = event.tracer
        # alignment = context.filename_alignment = max(
        #     getattr(context, 'filename_alignment', 5),
        #     len(filename)
        # )
        lines = self._safe_source(event)
        self.stream.write("{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {code}{}{reset}\n".format(
            filename,
            event.lineno,
            event.kind,
            lines[0],
            align=self.filename_alignment,
            code=self.code_colors[event.kind],
            **self.event_colors
        ))
        for line in lines[1:]:
            self.stream.write("{:>{align}}       {kind}{:9} {code}{}{reset}\n".format(
                "",
                r"   |",
                line,
                align=self.filename_alignment,
                code=self.code_colors[event.kind],
                **self.event_colors
            ))

        if event.kind in ('return', 'exception'):
            self.stream.write("{:>{align}}       {continuation}{:9} {color}{} value: {detail}{}{reset}\n".format(
                "",
                "...",
                event.kind,
                self._safe_repr(event.arg),
                align=self.filename_alignment,
                color=self.event_colors[event.kind],
                **self.event_colors
            ))


class VarsPrinter(Fields.names.globals.stream.filename_alignment, ColorStreamAction):
    """
    An action that prints local variables and optionally global variables visible from the current executing frame.

    Args:
        *names (strings): Names to evaluate. Expressions can be used (will only try to evaluate if all the variables are
            present on the frame.
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filename column (files are right-aligned). Default: ``40``.
        globals (bool): Allow access to globals. Default: ``False`` (only looks at locals).
    """

    def __init__(self, *names, **options):
        if not names:
            raise TypeError("Must give at least one name/expression.")
        self.stream = options.pop('stream', self.default_stream)
        self.force_colors = options.pop('force_colors', False)
        self.filename_alignment = max(5, options.pop('filename_alignment', DEFAULT_MIN_FILENAME_ALIGNMENT))
        self.names = {
            name: set(self._iter_symbols(name))
            for name in names
            }
        self.globals = options.pop('globals', False)

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

    def _safe_eval(self, code, event):
        """
        Try to evaluate the given code on the given frame. If failure occurs, returns some ugly string with exception.
        """
        try:
            return eval(code, event.globals if self.globals else {}, event.locals)
        except Exception as exc:
            return "{internal-failure}FAILED EVAL: {internal-detail}{!r}".format(exc, **self.event_colors)

    def __call__(self, event):
        """
        Handle event and print the specified variables.
        """
        first = True
        frame_symbols = set(event.locals)
        if self.globals:
            frame_symbols |= set(event.globals)

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
                self.stream.write("{:>{align}}       {vars}{:9} {vars-name}{} {vars}=> {reset}{}{reset}\n".format(
                    "",
                    "vars" if first else "...",
                    code,
                    printout,
                    align=self.filename_alignment,
                    **self.event_colors
                ))
                first = False
