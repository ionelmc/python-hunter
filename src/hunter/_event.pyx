cdef class Event:
    """
    Event wrapper for ``frame, kind, arg`` (the arguments the settrace function gets).

    Provides few convenience properties.
    """
    cdef:
        FrameType frame
        public str kind
        public object arg
        public Tracer tracer
        object _module
        object _filename

    def __cinit__(self, FrameType frame, str kind, object arg, Tracer tracer):
        self.frame = frame
        self.kind = kind
        self.arg = arg
        self.tracer = tracer
        self._module = None

    property locals:
        def __get__(self):
            """
            A dict with local variables.
            """
            return self.frame.f_locals

    property globals:
        def __get__(self):
            """
            A dict with global variables.
            """
            return self.frame.f_globals

    property function:
        def __get__(self):
            """
            A string with function name.
            """
            return self.code.co_name

    property module:
        """
        A string with module name (eg: ``"foo.bar"``).
        """
        def __get__(self):
            if self._module is None:
                module = self.frame.f_globals.get('__name__', '')
                if module is None:
                    module = ''

                self._module = module
            return self._module

    property filename:
        def __get__(self):
            """
            A string with absolute path to file.
            """
            if self._filename is None:
                filename = self.frame.f_globals.get('__file__', '')
                if filename is None:
                    filename = ''

                if filename.endswith(('.pyc', '.pyo')):
                    filename = filename[:-1]

                self._filename = filename
            return self._filename

    property lineno:
        def __get__(self):
            """
            An integer with line number in file.
            """
            return self.frame.f_lineno

    property code:
        def __get__(self):
            """
            A code object (not a string).
            """
            return self.frame.f_code

    property stdlib:
        def __get__(self):
            """
            A boolean flag. ``True`` if frame is in stdlib.
            """
            if self.filename.startswith(SITE_PACKAGES_PATH):
                # if it's in site-packages then its definitely not stdlib
                return False
            if self.filename.startswith(SYS_PREFIX_PATHS):
                return True
    property fullsource:
        def __get__(self):
            """
            A string with the sourcecode for the current statement (from ``linecache`` - failures are ignored).

            May include multiple lines if it's a class/function definition (will include decorators).
            """
            try:
                return self._raw_fullsource
            except Exception as exc:
                return "??? NO SOURCE: {!r}".format(exc)

    def source(self, getline=linecache.getline):
        """
        A string with the sourcecode for the current line (from ``linecache`` - failures are ignored).

        Fast but sometimes incomplete.
        """
        try:
            return getline(self.filename, self.lineno)
        except Exception as exc:
            return "??? NO SOURCE: {!r}".format(exc)

    def _raw_fullsource(self, getlines=linecache.getlines, getline=linecache.getline):
        if self.kind == 'call' and self.code.co_name != "<module>":
            lines = []
            try:
                for _, token, _, _, line in tokenize.generate_tokens(partial(
                    next,
                    yield_lines(self.filename, self.lineno - 1, lines.append)
                )):
                    if token in ("def", "class", "lambda"):
                        return ''.join(lines)
            except tokenize.TokenError:
                pass

        return getline(self.filename, self.lineno)

    __getitem__ = object.__getattribute__
