========
Cookbook
========

.. highlights::

    When in doubt, use Hunter.

Walkthrough
===========

Sometimes you just want to get an overview of an unfamiliar application code, eg: only see calls/returns/exceptions.

In this situation, you could use something like
``~Q(kind="line"),~Q(module_in=["six","pkg_resources"]),~Q(filename=""),stdlib=False``. Lets break that down:

* ``~Q(kind="line")`` means skip line events (``~`` is a negation of the filter).
* ``stdlib=False`` means we don't want to see anything from stdlib.
* ``~Q(module_in=["six","pkg_resources")]`` means we're tired of seeing stuff from those modules in site-packages.
* ``~Q(filename="")`` is necessary for filtering out events that come from code without a source (like the interpreter
  bootstrap stuff).

You would run the application (in Bash) like:

.. sourcecode:: shell

    PYTHONHUNTER='~Q(kind="line"),~Q(module_in=["six","pkg_resources"]),~Q(filename=""),stdlib=False' myapp (or python myapp.py)


Additionally you can also add a depth filter (eg: ``depth_lt=10``) to avoid too deep output.

Packaging
=========

I frequently use Hunter to figure out how distutils/setuptools work. It's very hard to figure out what's going on by just
looking at the code - lots of stuff happens at runtime. If you ever tried to write a custom command you know what I mean.

To show everything that is being run:

.. sourcecode:: shell

    PYTHONHUNTER='module_startswith=["setuptools", "distutils", "wheel"]' python setup.py bdist_wheel

If you want too see some interesting variables:

.. sourcecode:: shell

    PYTHONHUNTER='module_startswith=["setuptools", "distutils", "wheel"], actions=[CodePrinter, VarsPrinter("self.bdist_dir")]' python setup.py bdist_wheel

Typical
=======

Normally you'd only want to look at your code. For that purpose, there's the ``stdlib`` option. Set it to ``False``.

Building a bit on the previous example, if I have a ``build`` Distutils command and I only want to see my code then I'd run
this:

.. sourcecode:: shell

    PYTHONHUNTER='stdlib=False' python setup.py build

But this also means I'd be seeing anything from ``site-packages``. I could filter on only the events from the current
directory (assuming the filename is going to be a relative path):

.. sourcecode:: shell

    PYTHONHUNTER='~Q(filename_startswith="/")' python setup.py build

Debugging a test
================

In tests it is convenient to ignore everything that is in ``stdlib`` and ``site-packages`` and start hunter right before
the tested function.

.. sourcecode:: python

    from hunter import trace, Q
    trace(Q(stdlib=False), ~Q(filename_contains='site-packages'))

It also helps to save output into a file to compare different runs. An example below uses ``pytest`` with ``-k`` option
to select and tun a test or tests with string ``some`` in name. The output is then piped to ``testout1`` file.

.. sourcecode:: python

    pytest test/test_simple.py -k some &> testout1


Needle in the haystack
======================

If the needle might be though the stdlib then you got not choice. But some of the `hay` is very verbose and useless, like
stuff from the ``re`` module.

Note that there are few "hidden" modules like ``sre``, ``sre_parse``, ``sre_compile`` etc. You can filter that out with:

.. sourcecode:: python

    ~Q(module_regex="(re|sre.*)$")

Although filtering out that regex stuff can cut down lots of useless output you usually still get lots of output.

Another way, if you got at least some vague idea of what might be going on is to "grep" for sourcecode. Example, to show all
the code that does something with a ``build_dir`` property:

.. sourcecode:: python

    source_contains=".build_dir"

You could even extend that a bit to dump some variables:

.. sourcecode:: python

    source_contains=".build_dir", actions=[CodePrinter, VarsPrinter("self.build_dir")]


Stop after N calls
==================

Say you want to stop tracing after 1000 events, you'd do this:

.. sourcecode:: python

    ~Q(calls_gt=1000, action=Stop)

..

    Explanation:

        ``Q(calls_gt=1000, action=Stop)`` will translate to ``When(Query(calls_gt=1000), Stop)``

        ``Q(calls_gt=1000)`` will return ``True`` when 1000 call count is hit.

        ``When(something, Stop)`` will call ``Stop`` when ``something`` returns ``True``. However it will also return the result of ``something`` - the net effect being nothing being shown up to 1000 calls. Clearly not what we want ...

        So then we invert the result, ``~When(...)`` is the same as ``Not(When)``.

        This may not seem intuitive but for now it makes internals simpler. If ``When`` would always return ``True`` then
        ``Or(When, When)`` would never run the second ``When`` and we'd need to have all sorts of checks for this. This may
        change in the future however.

"Probe" - lightweight tracing
=============================

Based on Robert Brewer's `FunctionProbe <https://github.com/ionelmc/python-hunter/issues/45#issuecomment-453754832>`_
example.

The use-case is that you'd like to trace a huge application and running a tracer (even a cython one) would have a too
great impact. To solve this you'd start the tracer only in placer where it's actually needed.

To make this work you'd monkeypatch the function that needs the tracing. This example uses `aspectlib
<https://python-aspectlib.readthedocs.io/>`_:

.. sourcecode:: python

    def probe(qualname, *actions, **filters):
        def tracing_decorator(func):
            @functools.wraps(func)
            def tracing_wrapper(*args, **kwargs):
                # create the Tracer manually to avoid spending time in likely useless things like:
                # - loading PYTHONHUNTERCONFIG
                # - setting up the clear_env_var or thread_support options
                # - atexit cleanup registration
                with hunter.Tracer().trace(hunter.When(hunter.Query(**filters), *actions)):
                    return func(*args, **kwargs)

            return tracing_wrapper

        aspectlib.weave(qualname, tracing_decorator)  # this does the monkeypatch

Suggested use:

* to get the regular tracing for that function:

  .. sourcecode:: python

        probe('module.func', hunter.VarsPrinter('var1', 'var2'))

* to log some variables at the end of the target function, and nothing deeper:

  .. sourcecode:: python

        probe('module.func', hunter.VarsPrinter('var1', 'var2'), kind="return", depth=0)

Another interesting thing is that you may note that you can reduce the implementation of the ``probe`` function down to
just:

.. sourcecode:: python

    def probe(qualname, *actions, **kwargs):
        aspectlib.weave(qualname, functools.partial(hunter.wrap, actions=actions, **kwargs))

It will work the same, :obj:`hunter.wrap` being a decorator. However, while :obj:`hunter.wrap` offers the convenience
of tracing just inside the target function (eg: ``probe('module.func', local=True)``) it will also add a lot of extra
filtering to trim irrelevant events from around the function (like return from tracer setup, and the internals of the
decorator), in addition to what :func:`hunter.trace` does. Not exactly lightweight...

.. _silenced-exception-runtime-analysis:

Silenced exception runtime analysis
===================================

Finding code that discards exceptions is sometimes really hard.

.. note::

    This was made available in :class:`hunter.actions.ErrorSnooper` for convenience. This cookbook entry will remain for educational
    purposes.

While this is easy to find with a ``grep "except:" -R .``:

.. code-block:: python

    def silenced_easy():
        try:
            error()
        except:
            pass

Variants of this ain't easy to grep:

.. code-block:: python

    def silenced_easy():
        try:
            error()
        except Exception:
            pass

If you can't simply review all the sourcecode then runtime analysis is one way to tackle this:

.. code-block:: python

    class DumpExceptions(hunter.CodePrinter):
        events = ()
        depth = 0
        count = 0
        exc = None

        def __init__(self, max_count=10, **kwargs):
            self.max_count = max_count
            self.backlog = collections.deque(maxlen=5)
            super(DumpExceptions, self).__init__(**kwargs)

        def __call__(self, event):
            self.count += 1
            if event.kind == 'exception':  # something interesting happened ;)
                self.events = list(self.backlog)
                self.events.append(event.detach(self.try_repr))
                self.exc = self.try_repr(event.arg[1])
                self.depth = event.depth
                self.count = 0
            elif self.events:
                if event.depth > self.depth:  # too many details
                    return
                elif event.depth < self.depth and event.kind == 'return':  # stop if function returned
                    op = event.instruction
                    op = op if isinstance(op, int) else ord(op)
                    if op in RETURN_OPCODES:
                        self.output("{BRIGHT}{fore(BLUE)}{} tracing {} on {}{RESET}\n",
                                    ">" * 46, event.function, self.exc)
                        for event in self.events:
                            super(DumpExceptions, self).__call__(event)
                        if self.count > 10:
                            self.output("{BRIGHT}{fore(BLACK)}{} too many lines{RESET}\n",
                                        "-" * 46)
                        else:
                            self.output("{BRIGHT}{fore(BLACK)}{} function exit{RESET}\n",
                                        "-" * 46)
                    self.events = []
                    self.exc = None
                elif self.count < self.max_count:
                    self.events.append(event.detach(self.try_repr))
            else:
                self.backlog.append(event.detach(self.try_repr))

Take note about the use of :meth:`~hunter.event.Event.detach` and :meth:`~hunter.actions.ColorStreamAction.output`.

Profiling
=========

Hunter can be used to implement profiling (measure function timings).

The most basic implementation that only measures timings looks like this:

.. code-block:: python

    from hunter.actions import Action
    from hunter.actions import RETURN_OPCODES

    class ProfileAction(Action):
        def __init__(self):
            self.timings = {}

        def __call__(self, event):
            if event.kind == 'call':
                self.timings[id(event.frame)] = time()
            elif event.kind == 'return':
                start_time = self.timings.pop(id(event.frame), None)
                if start_time is None:
                    return
                delta = time() - start_time
                print(f'{event.function} returned: {event.arg}. Duration: {delta:.4f}s\n')

If you don't care about exceptions at all this will be fine, but then you might just as well use a real profiler.

When exceptions occur Python send this to the tracer:

* .. code-block:: python

    event.kind="exception", event.arg=(exc_value, exc_type, tb)

* .. code-block:: python

    event.kind="return", event.arg=None

Unfortunately Python emits the return event even if the exception wasn't discarded so we need to do some extra checks around the last
bytecode instruction that run at the return event.

This means that we have to store the exception for a little while, and do the check at return:

.. code-block:: python

    from hunter.actions import Action
    from hunter.actions import RETURN_OPCODES

    class ProfileAction(Action):
        def __init__(self):
            self.timings = {}

        def __call__(self, event):
            current_time = time()
            frame_id = id(event.frame)

            if event.kind == 'call':
                self.timings[frame_id] = current_time, None
            elif frame_id in self.timings:
                start_time, depth, exception = self.timings.pop(frame_id)

                if event.kind == 'exception':
                    # store the exception
                    # (there will be a followup 'return' event in which we deal with it)
                    self.timings[frame_id] = start_time, event.arg
                elif event.kind == 'return':
                    delta = current_time - start_time
                    if event.instruction in RETURN_OPCODES:
                        # exception was discarded
                        print(f'{event.function} returned: {event.arg}. Duration: {delta:.4f}s\n')
                    else:
                        print(f'{event.function} raised exception: {exception}. Duration: {delta:.4f}s\n')

If you try that example you may notice that it's not completely equivalent to any of the profilers available out there: data for builtin
functions is missing.

Python does in fact have a profiling mode (eg: ``hunter.trace(profile=True``) and that will make hunter use ``sys.setprofile`` instead
of ``sys.setrace``. However there are some downsides with that API:

* exception data will be missing (most likely because profiling is designed for speed and tracebacks are costly to build)
* trace events for builtin functions do not have their own frame objects (so we need to cater for that)

Behold, a `ProfileAction` that works in any mode:

.. code-block:: python

    from hunter.actions import ColorStreamAction
    from hunter.actions import RETURN_OPCODES

    class ProfileAction(ColorStreamAction):
        # using ColorStreamAction brings this more in line with the other actions
        # (stream option, coloring and such, see the other examples for colors)
        def __init__(self, **kwargs):
            self.timings = {}
            super(ProfileAction, self).__init__(**kwargs)

        def __call__(self, event):
            current_time = time()
            # include event.builtin in the id so we don't have problems
            # with Python reusing frame objects from the previous call for builtin calls
            frame_id = id(event.frame), str(event.builtin)

            if event.kind == 'call':
                self.timings[frame_id] = current_time, None
            elif frame_id in self.timings:
                start_time, exception = self.timings.pop(frame_id)

                # try to find a complete function name for display
                function_object = event.function_object
                if event.builtin:
                    function = '<builtin>.{}'.format(event.arg.__name__)
                elif function_object:
                    if hasattr(function_object, '__qualname__'):
                        function = '{}.{}'.format(
                            function_object.__module__, function_object.__qualname__
                        )
                    else:
                        function = '{}.{}'.format(
                            function_object.__module__,
                            function_object.__name__
                        )
                else:
                    function = event.function

                if event.kind == 'exception':
                    # store the exception
                    # (there will be a followup 'return' event in which we deal with it)
                    self.timings[frame_id] = start_time, event.arg
                elif event.kind == 'return':
                    delta = current_time - start_time
                    if event.instruction in RETURN_OPCODES:
                        # exception was discarded
                        self.output(
                            '{fore(BLUE)}{} returned: {}. Duration: {:.4f}s{RESET}\n',
                            function, safe_repr(event.arg), delta
                        )
                    else:
                        self.output(
                            '{fore(RED)}{} raised exception: {}. Duration: {:.4f}s{RESET}\n',
                            function, safe_repr(exception), delta
                        )
