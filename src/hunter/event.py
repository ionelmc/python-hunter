from __future__ import absolute_import

import linecache
import re
import tokenize
from functools import partial

from fields import Fields

from .const import SITE_PACKAGES_PATHS
from .const import SYS_PREFIX_PATHS
from .util import cached_property

STARTSWITH_TYPES = list, tuple, set


class Event(Fields.kind.function.module.filename):
    """
    Event wrapper for ``frame, kind, arg`` (the arguments the settrace function gets). This objects is passed to your
    custom functions or predicates.

    Provides few convenience properties.

    .. warning::

        Users do not instantiate this directly.
    """
    frame = None
    kind = None
    arg = None
    tracer = None

    def __init__(self, frame, kind, arg, tracer):
        self.frame = frame
        self.kind = kind
        self.arg = arg
        self.tracer = tracer

    @cached_property
    def locals(self):
        """
        A dict with local variables.
        """
        return self.frame.f_locals

    @cached_property
    def globals(self):
        """
        A dict with global variables.
        """
        return self.frame.f_globals

    @cached_property
    def function(self):
        """
        A string with function name.
        """
        return self.code.co_name

    @cached_property
    def module(self):
        """
        A string with module name (eg: ``"foo.bar"``).
        """
        module = self.frame.f_globals.get('__name__', '')
        if module is None:
            module = ''

        return module

    @cached_property
    def filename(self):
        """
        A string with absolute path to file.
        """
        filename = self.frame.f_globals.get('__file__', '')
        if filename is None:
            filename = ''

        if filename.endswith(('.pyc', '.pyo')):
            filename = filename[:-1]
        elif filename.endswith('$py.class'):  # Jython
            filename = filename[:-9] + ".py"

        return filename

    @cached_property
    def lineno(self):
        """
        An integer with line number in file.
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
        """
        if self.filename.startswith(SITE_PACKAGES_PATHS):
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
        """
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
                leading_whitespace_re=re.compile('(^[ \t]*)(?:[^ \t\n])', re.MULTILINE)):
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
