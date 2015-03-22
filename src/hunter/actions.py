from __future__ import unicode_literals

import linecache
import os
import pdb
import sys

from fields import Fields

DEFAULT_MIN_FILENAME_ALIGNMENT = 15


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


class CodePrinter(Fields.stream.filename_alignment, Action):
    """
    An action that just prints the code being executed.
    """
    def __init__(self, stream=sys.stderr, filename_alignment=DEFAULT_MIN_FILENAME_ALIGNMENT):
        self.stream = stream
        self.filename_alignment = filename_alignment

    def _getline(self, filename, lineno, getline=linecache.getline):
        """
        Get a line from ``linecache``. Ignores failures somewhat.
        """
        try:
            return getline(filename, lineno)
        except Exception as exc:
            return "??? no source: {} ???".format(exc)

    def __call__(self, event, basename=os.path.basename):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also prints values.
        """
        filename = event.filename or "<???>"
        # TODO: support auto-alignment, need a context object for this, eg:
        # alignment = context.filename_alignment = max(getattr(context, 'filename_alignment', self.filename_alignment), len(filename))
        self.stream.write("{:>{align}}:{:<5} {:9} {}\n".format(
            basename(filename),
            event.lineno,
            event.kind,
            self._getline(filename, event.lineno).rstrip(),
            align=self.filename_alignment
        ))
        if event.kind in ('return', 'exception'):
            self.stream.write("{:>{align}}       {:9} {} value: {!r}\n".format(
                "",
                "...",
                event.kind,
                event.arg,
                align=self.filename_alignment
            ))


class VarsPrinter(Fields.names.globals.stream.filename_alignment, Action):
    """
    An action that prints local variables and optinally global variables visible from the current executing frame.
    """
    def __init__(self, name=None, names=(), globals=False, stream=sys.stderr, filename_alignment=DEFAULT_MIN_FILENAME_ALIGNMENT):
        self.stream = stream
        self.filename_alignment = filename_alignment
        self.names = list(names)
        if name:
            self.names.append(name)
        self.globals = globals

    def __call__(self, event):
        """
        Handle event and print the specified variables.
        """
        first = True
        for key, value in event.locals.items():
            if key in self.names or not self.names:
                self.stream.write("{:>{align}}       {:9} {} -> {!r}\n".format(
                    "",
                    "vars" if first else "...",
                    key,
                    value,
                    align=self.filename_alignment
                ))
                first = False
        if self.globals:
            for key, value in event.globals.items():
                if key in self.names or not self.names:
                    self.stream.write("{:>{align}}       {:9} {} => {!r}\n".format(
                        "",
                        "vars" if first else "...",
                        key,
                        value,
                        align=self.filename_alignment
                    ))
                    first = False
