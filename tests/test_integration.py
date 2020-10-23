from __future__ import print_function

import inspect
import os
import subprocess
import sys
from pprint import pprint

import pytest

from hunter import Backlog
from hunter import CallPrinter
from hunter import CodePrinter
from hunter import Debugger
from hunter import ErrorSnooper
from hunter import Q
from hunter import StackPrinter
from hunter import Tracer
from hunter import VarsPrinter
from hunter import VarsSnooper
from hunter import When
from hunter import trace
from hunter import wrap

from utils import DebugCallPrinter

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

pytest_plugins = 'pytester',


def _get_func_spec(func):
    if hasattr(inspect, 'signature'):
        return str(inspect.signature(func))
    if hasattr(inspect, 'getfullargspec'):
        spec = inspect.getfullargspec(func)
    else:
        spec = inspect.getargspec(func)
    return inspect.formatargspec(spec.args, spec.varargs)


def test_pth_activation():
    module_name = os.path.__name__
    expected_module = '{0}.py'.format(module_name)
    hunter_env = 'action=CodePrinter,module={!r},function="join"'.format(module_name)
    func_spec = _get_func_spec(os.path.join)
    expected_call = 'call      def join{0}:'.format(func_spec)

    output = subprocess.check_output(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'sample.py')],
        env=dict(os.environ, PYTHONHUNTER=hunter_env),
        stderr=subprocess.STDOUT,
    )
    assert expected_module.encode() in output
    assert expected_call.encode() in output


def test_pth_sample4():
    env = dict(os.environ, PYTHONHUNTER='CodePrinter')
    env.pop('COVERAGE_PROCESS_START', None)
    env.pop('COV_CORE_SOURCE', None)
    output = subprocess.check_output(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'sample4.py')],
        env=env,
        stderr=subprocess.STDOUT,
    )
    assert output


def test_pth_sample2(LineMatcher):
    env = dict(os.environ, PYTHONHUNTER="module='__main__',action=CodePrinter")
    env.pop('COVERAGE_PROCESS_START', None)
    env.pop('COV_CORE_SOURCE', None)
    output = subprocess.check_output(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'sample2.py')],
        env=env,
        stderr=subprocess.STDOUT,
    )
    lm = LineMatcher(output.decode('utf-8').splitlines())
    lm.fnmatch_lines([
        '*tests*sample2.py:* call      if __name__ == "__main__":  #*',
        '*tests*sample2.py:* line      if __name__ == "__main__":  #*',
        '*tests*sample2.py:* line          import functools',
        '*tests*sample2.py:* line          def deco(opt):',
        '*tests*sample2.py:* line          @deco(1)',
        '*tests*sample2.py:* call          def deco(opt):',
        '*tests*sample2.py:* line              def decorator(func):',
        '*tests*sample2.py:* line              return decorator',
        '*tests*sample2.py:* return            return decorator',
        '*                 * ...       return value: <function deco*',
        '*tests*sample2.py:* line          @deco(2)',
        '*tests*sample2.py:* call          def deco(opt):',
        '*tests*sample2.py:* line              def decorator(func):',
        '*tests*sample2.py:* line              return decorator',
        '*tests*sample2.py:* return            return decorator',
        '*                 * ...       return value: <function deco*',
        '*tests*sample2.py:* line          @deco(3)',
        '*tests*sample2.py:* call          def deco(opt):',
        '*tests*sample2.py:* line              def decorator(func):',
        '*tests*sample2.py:* line              return decorator',
        '*tests*sample2.py:* return            return decorator',
        '*                 * ...       return value: <function deco*',
        '*tests*sample2.py:* call              def decorator(func):',
        '*tests*sample2.py:* line                  @functools.wraps(func)',
        '*tests*sample2.py:* line                  return wrapper',
        '*tests*sample2.py:* return                return wrapper',
        '*                 * ...       return value: <function foo *',
        '*tests*sample2.py:* call              def decorator(func):',
        '*tests*sample2.py:* line                  @functools.wraps(func)',
        '*tests*sample2.py:* line                  return wrapper',
        '*tests*sample2.py:* return                return wrapper',
        '*                 * ...       return value: <function foo *',
        '*tests*sample2.py:* call              def decorator(func):',
        '*tests*sample2.py:* line                  @functools.wraps(func)',
        '*tests*sample2.py:* line                  return wrapper',
        '*tests*sample2.py:* return                return wrapper',
        '*                 * ...       return value: <function foo *',
        '*tests*sample2.py:* line          foo(',
        "*tests*sample2.py:* line              'a*',",
        "*tests*sample2.py:* line              'b'",
        '*tests*sample2.py:* call                  @functools.wraps(func)',
        '*                 *    [*]                  def wrapper(*args):',
        '*tests*sample2.py:* line                      return func(*args)',
        '*tests*sample2.py:* call                  @functools.wraps(func)',
        '*                 *    [*]                  def wrapper(*args):',
        '*tests*sample2.py:* line                      return func(*args)',
        '*tests*sample2.py:* call                  @functools.wraps(func)',
        '*                 *    [*]                  def wrapper(*args):',
        '*tests*sample2.py:* line                      return func(*args)',
        '*tests*sample2.py:* call          @deco(1)',
        '*                 *    |          @deco(2)',
        '*                 *    |          @deco(3)',
        '*                 *    [*]          def foo(*args):',
        '*tests*sample2.py:* line              return args',
        '*tests*sample2.py:* return            return args',
        "*                 * ...       return value: ('a*', 'b')",
        "*tests*sample2.py:* return                    return func(*args)",
        "*                 * ...       return value: ('a*', 'b')",
        "*tests*sample2.py:* return                    return func(*args)",
        "*                 * ...       return value: ('a*', 'b')",
        "*tests*sample2.py:* return                    return func(*args)",
        "*                 * ...       return value: ('a*', 'b')",
        "*tests*sample2.py:* line          try:",
        "*tests*sample2.py:* line              None(",
        "*tests*sample2.py:* line                  'a',",
        "*tests*sample2.py:* line                  'b'",
        "*tests*sample2.py:* exception *",
        "*                 * ...       exception value: *",
        "*tests*sample2.py:* line          except:",
        "*tests*sample2.py:* line              pass",
        "*tests*sample2.py:* return            pass",
        "*                   ...       return value: None",
    ])


def test_tracing_bare(LineMatcher):
    lines = StringIO()
    with trace(CodePrinter(stream=lines)):
        def a():
            return 1

        b = a()
        b = 2
        try:
            raise Exception('BOOM!')
        except Exception:
            pass
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*test_*.py* call              def a():",
        "*test_*.py* line                  return 1",
        "*test_*.py* return                return 1",
        "* ...       return value: 1",
    ])


@pytest.mark.parametrize('module', ['sys', 'builtins'])
def test_profile_mode(LineMatcher, module):
    lines = StringIO()
    with trace(profile=True, action=CallPrinter(stream=lines)):
        def a():
            foo = 1
            sys.getsizeof(foo, 2)
            return getattr(a, 'b', foo)

        a()
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    if module == 'sys':
        lm.fnmatch_lines([
            '*test_integration.py:* call   * > sys.getsizeof: *',
            '*test_integration.py:* return * < sys.getsizeof',
        ])
    else:
        lm.fnmatch_lines([
            "*test_integration.py:* call   * > *builtin*.getattr: *",
            '*test_integration.py:* return * < *builtin*.getattr',
        ])


def test_tracing_reinstall(LineMatcher):
    lines = StringIO()
    with trace(CodePrinter(stream=lines)):
        def foo():
            a = 2
            sys.settrace(sys.gettrace())
            a = 3

        def bar():
            a = 1
            foo()
            a = 4

        bar()
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*test_*.py:*   call              def bar():",
        "*test_*.py:*   line                  a = 1",
        "*test_*.py:*   line                  foo()",
        "*test_*.py:*   call              def foo():",
        "*test_*.py:*   line                  a = 2",
        "*test_*.py:*   line                  sys.settrace(sys.gettrace())",
        "*test_*.py:*   line                  a = 3",
        "*test_*.py:*   return                a = 3",
        "*                   ...       return value: None",
        "*test_*.py:*   line                  a = 4",
        "*test_*.py:*   return                a = 4",
        "*                   ...       return value: None",

    ])


def test_tracer_autostop():
    with trace(lambda: garbage) as tracer:
        if os.environ.get("SETUPPY_CFLAGS") == "-DCYTHON_TRACE=1":
            assert sys.gettrace() is not tracer
        else:
            assert sys.gettrace() is None


@pytest.mark.skipif(sys.platform == 'win32', reason='no fork on windows')
@pytest.mark.parametrize('Action', [CodePrinter, CallPrinter])
@pytest.mark.parametrize('force_pid', [True, False])
def test_pid_prefix(LineMatcher, Action, force_pid, capfd):
    def main():
        a = 1
        pid = os.fork()
        if pid:
            os.waitpid(pid, 0)
        else:
            os._exit(0)  # child

    with trace(actions=[Action(force_pid=force_pid, stream=sys.stdout),
                        VarsPrinter('a', force_pid=force_pid, stream=sys.stdout)],
               stdlib=False,
               threading_support=True):
        main()
    out, err = capfd.readouterr()
    print('OUT', out)
    print('ERR', err)
    lm = LineMatcher(out.splitlines())
    prefix = '[[]*[]] *' if force_pid else ''
    lm.fnmatch_lines_random([
        prefix + "MainThread  *test_*.py:*  line * a = 1",
        prefix + "MainThread  *test_*.py:*  line * if pid:",
        prefix + "MainThread  *test_*.py:*  line * [[]a => 1[]]",
        prefix + "MainThread  *test_*.py:*  line * os.waitpid(pid, 0)",
        "[[]*[]] *MainThread  *test_*.py:*  line * os._exit(0)  # child",
        "[[]*[]] *MainThread  *test_*.py:*  line * [[]a => 1[]]",
    ])


def test_debugger(LineMatcher):
    out = StringIO()
    calls = []

    class FakePDB:
        def __init__(self, foobar=1):
            calls.append(foobar)

        def set_trace(self, frame):
            calls.append(frame.f_code.co_name)

    with trace(
        lambda event: event.locals.get('node') == 'Foobar',
        module=__name__,
        function='foo',
        actions=[CodePrinter,
                 VarsPrinter('a', 'node', 'foo', 'test_debugger', stream=out),
                 Debugger(klass=FakePDB, foobar=2)]
    ):
        def foo():
            a = 1
            node = 'Foobar'
            node += 'x'
            a += 2
            return a

        foo()
    print(out.getvalue())
    assert calls == [2, 'foo']
    lm = LineMatcher(out.getvalue().splitlines())
    pprint(lm.lines)
    lm.fnmatch_lines_random([
        "*      [[]test_debugger => <function test_debugger at *[]]",
        "*      [[]node => 'Foobar'[]]",
        "*      [[]a => 1[]]",
    ])


@pytest.mark.parametrize('depth', [2, 3, 4], ids='depth_lt={}'.format)
def test_depth_limit(LineMatcher, depth):
    buff = StringIO()
    from sample7 import one
    tracer = Tracer()
    predicate = When(Q(depth_lt=depth), CallPrinter(stream=buff))
    try:
        tracer.trace(predicate)
        one()
    finally:
        tracer.stop()
    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "* call      => one()",
        "* line         for i in range(1):  # one",
        "* line         two()",
        "* call         => two()",
        "* return       <= two: None",
        "* line         for i in range(1):  # one",
        "* return    <= one: None",
    ])
    if depth < 3:
        assert 'three' not in output
    if depth < 4:
        assert 'four' not in output
    if depth < 5:
        assert 'five' not in output


@pytest.mark.parametrize('depth', [2, 3, 4], ids='depth_lt={}'.format)
def test_depth_limit_subprocess(LineMatcher, depth):
    hunter_env = "action=CallPrinter,depth_lt={!r},kind_in=['call','return'],stdlib=0".format(depth + 1)
    output = subprocess.check_output(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'sample7.py')],
        env=dict(os.environ, PYTHONHUNTER=hunter_env, COV_CORE_DATAFILE=''),
        stderr=subprocess.STDOUT,
    )
    output = output.decode('utf8')
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "* call    * => one()",
        "* call    *    => two()",
        "* return  *    <= two: None",
        "* return  * <= one: None",
    ])
    if depth < 3:
        assert '=> three' not in output
    if depth < 4:
        assert '=> four' not in output
    if depth < 5:
        assert '=> five' not in output


def test_varssnooper(LineMatcher):
    lines = StringIO()
    snooper = VarsSnooper(stream=lines)

    @wrap(actions=[snooper, CodePrinter(stream=lines)])
    def a():
        foo = bar = b = 1
        b = 2
        foo = 3
        foo = bar = 4
        return b

    a()

    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*test_*.py*  line              foo = bar = b = 1",
        "*test_*.py*  line      [[]b := 1[]]",
        "*         *  ...       [[]bar := 1[]]",
        "*         *  ...       [[]foo := 1[]]",
        "*test_*.py*  line              b = 2",
        "*test_*.py*  line      [[]b : 1 => 2[]]",
        "*test_*.py*  line              foo = 3",
        "*test_*.py*  line      [[]foo : 1 => 3[]]",
        "*test_*.py*  line              foo = bar = 4",
        "*test_*.py*  line      [[]bar : 1 => 4[]]",
        "*         *  ...       [[]foo : 3 => 4[]]",
        "*test_*.py*  line              return b",
        "*test_*.py*  return            return b",
        "*         *  ...       return value: 2",
    ])
    assert snooper.stored_reprs == {}


def test_errorsnooper(LineMatcher):
    lines = StringIO()
    snooper = ErrorSnooper(stream=lines, max_backlog=50, max_events=100)

    @wrap(actions=[snooper])
    def a():
        from sample8errors import notsilenced
        from sample8errors import silenced1
        from sample8errors import silenced2
        from sample8errors import silenced3
        from sample8errors import silenced4

        silenced1()
        print("Done silenced1")
        silenced2()
        print("Done silenced2")
        silenced3()
        print("Done silenced3")
        silenced4()
        print("Done silenced4")

        try:
            notsilenced()
        except ValueError:
            print("Done not silenced")

    a()

    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced1 on (*RuntimeError*)",
        "*test_*.py:*  line              silenced1()",
        "*sample8errors.py:14    call      def silenced1():",
        "*sample8errors.py:15    line          try:",
        "*sample8errors.py:16    line              error()",
        "*sample8errors.py:6     call      def error():",
        "*sample8errors.py:7     line          raise RuntimeError()",
        "*sample8errors.py:7     exception     raise RuntimeError()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:7     return        raise RuntimeError()",
        "*                       ...       return value: None",
        "*sample8errors.py:16    exception         error()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:17    line          except Exception:",
        "*sample8errors.py:18    line              pass",
        "*sample8errors.py:18    return            pass",
        "*                       ...       return value: None",
        "*---------------------- function exit",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced2 on (*RuntimeError*)",
        '*test_*.py:*  line              print("Done silenced1")',
        "*test_*.py:*  line              silenced2()",
        "*sample8errors.py:21    call      def silenced2():",
        "*sample8errors.py:22    line          try:",
        "*sample8errors.py:23    line              error()",
        "*sample8errors.py:6     call      def error():",
        "*sample8errors.py:7     line          raise RuntimeError()",
        "*sample8errors.py:7     exception     raise RuntimeError()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:7     return        raise RuntimeError()",
        "*                       ...       return value: None",
        "*sample8errors.py:23    exception         error()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:24    line          except Exception as exc:",
        "*sample8errors.py:25    line              log(exc)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*---------------------- too many lines",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced3 on (*RuntimeError*)",
        '*test_*.py:*  line              print("Done silenced2")',
        "*test_*.py:*  line              silenced3()",
        "*sample8errors.py:31    call      def silenced3():",
        "*sample8errors.py:32    line          try:",
        "*sample8errors.py:33    line              error()",
        "*sample8errors.py:6     call      def error():",
        "*sample8errors.py:7     line          raise RuntimeError()",
        "*sample8errors.py:7     exception     raise RuntimeError()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:7     return        raise RuntimeError()",
        "*                       ...       return value: None",
        "*sample8errors.py:33    exception         error()",
        "*                       ...       exception value: (*RuntimeError*)",
        '*sample8errors.py:35    line              return "mwhahaha"',
        '*sample8errors.py:35    return            return "mwhahaha"',
        "*                       ...       return value: 'mwhahaha'",
        "*---------------------- function exit",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced4 on (*RuntimeError*)",
        '*test_*.py:*  line              print("Done silenced3")',
        "*test_*.py:*  line              silenced4()",
        "*sample8errors.py:38    call      def silenced4():",
        "*sample8errors.py:39    line          try:",
        "*sample8errors.py:40    line              error()",
        "*sample8errors.py:6     call      def error():",
        "*sample8errors.py:7     line          raise RuntimeError()",
        "*sample8errors.py:7     exception     raise RuntimeError()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:7     return        raise RuntimeError()",
        "*                       ...       return value: None",
        "*sample8errors.py:40    exception         error()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:41    line          except Exception as exc:",
        "*sample8errors.py:42    line              logger.info(repr(exc))",
        "*__init__.py:*  call          def info(self, msg, *args, **kwargs):",
        "*sample8errors.py:42    return            logger.info(repr(exc))",
        "*                       ...       return value: None",
        "*---------------------- function exit",
    ])


def test_errorsnooper_fastmode(LineMatcher):
    lines = StringIO()
    snooper = ErrorSnooper(stream=lines, max_backlog=0, max_events=100)

    @wrap(actions=[snooper])
    def a():
        from sample8errors import notsilenced
        from sample8errors import silenced1
        from sample8errors import silenced2
        from sample8errors import silenced3
        from sample8errors import silenced4

        silenced1()
        print("Done silenced1")
        silenced2()
        print("Done silenced2")
        silenced3()
        print("Done silenced3")
        silenced4()
        print("Done silenced4")

        try:
            notsilenced()
        except ValueError:
            print("Done not silenced")

    a()

    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced1 on (*RuntimeError*)",
        "*sample8errors.py:17    line          except Exception:",
        "*sample8errors.py:18    line              pass",
        "*sample8errors.py:18    return            pass",
        "*                       ...       return value: None",
        "*---------------------- function exit",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced2 on (*RuntimeError*)",
        "*sample8errors.py:24    line          except Exception as exc:",
        "*sample8errors.py:25    line              log(exc)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*---------------------- too many lines",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced3 on (*RuntimeError*)",
        '*sample8errors.py:35    line              return "mwhahaha"',
        '*sample8errors.py:35    return            return "mwhahaha"',
        "*                       ...       return value: 'mwhahaha'",
        "*---------------------- function exit",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced4 on (*RuntimeError*)",
        "*sample8errors.py:41    line          except Exception as exc:",
        "*sample8errors.py:42    line              logger.info(repr(exc))",
        "*__init__.py:*  call          def info(self, msg, *args, **kwargs):",
        "*sample8errors.py:42    return            logger.info(repr(exc))",
        "*                       ...       return value: None",
        "*---------------------- function exit",
    ])


def test_stack_printer_1(LineMatcher):
    buff = StringIO()
    with trace(Q(function="five", action=StackPrinter(limit=1, stream=buff))):
        from sample7 import one
        one()

    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "*sample7.py:??:five <= sample7.py:??:four <= sample7.py:??:three <= sample7.py:??:two <= sample7.py:?:one <= test_integration.py:???:test_stack_printer*",
    ])


def test_stack_printer_2(LineMatcher):
    buff = StringIO()
    with trace(Q(function="five", action=StackPrinter(limit=2, stream=buff))):
        from sample7 import one
        one()

    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "*sample7.py:??:five <= tests/sample7.py:??:four <= tests/sample7.py:??:three <= tests/sample7.py:??:two <= tests/sample7.py:?:one <= tests/test_integration.py:???:test_stack_printer*",
    ])


@pytest.mark.parametrize('stack', [5, 6], ids="stack={}".format)
def test_backlog(LineMatcher, stack):
    buff = StringIO()
    from sample7args import one
    with trace(
        Backlog(
            fullsource_has='return i', size=19, stack=stack, vars=False, action=DebugCallPrinter(' [' 'backlog' ']', stream=buff)
        ).filter(
            ~Q(function='six')
        ),
        action=DebugCallPrinter(stream=buff)
    ):
        one()
        one()  # make sure Backlog is reusable (doesn't have storage side-effects)
    output = buff.getvalue()
    import re
    print(re.sub(r'([\[\]])', r'[\1]', output))
    # print(output)
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "depth=0 calls=-1 *sample7args.py:*   call      => one(a=?, b=?, c=?) [[]backlog[]]",
        "depth=1 calls=?? *sample7args.py:*   line         two() [[]backlog[]]",
        "depth=1 calls=?? *sample7args.py:*   call         => two(a=?, b=?, c=?) [[]backlog[]]",
        "depth=2 calls=?? *sample7args.py:*   line            for i in range(1):  # two [[]backlog[]]",
        "depth=2 calls=?? *sample7args.py:*   line            a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=2 calls=?? *sample7args.py:*   line            three() [[]backlog[]]",
        "depth=2 calls=?? *sample7args.py:*   call            => three(a=?, b=?, c=?) [[]backlog[]]",
        "depth=3 calls=?? *sample7args.py:*   line               for i in range(1):  # three [[]backlog[]]",
        "depth=3 calls=?? *sample7args.py:*   line               a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=3 calls=?? *sample7args.py:*   line               four() [[]backlog[]]",
        "depth=3 calls=?? *sample7args.py:*   call               => four(a=?, b=?, c=?) [[]backlog[]]",
        "depth=4 calls=?? *sample7args.py:*   line                  for i in range(1):  # four [[]backlog[]]",
        "depth=4 calls=?? *sample7args.py:*   line                  a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=4 calls=?? *sample7args.py:*   line                  five() [[]backlog[]]",
        "depth=4 calls=?? *sample7args.py:*   call                  => five(a=?, b=?, c=?) [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     six() [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     six() [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     six() [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     a = b = c[[]'side'[]] = in_five = 'effect' [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     for i in range(1):  # five [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     return i  # five",
        "depth=4 calls=?? *sample7args.py:*   return                <= five: 0",
        "depth=0 calls=-1 *sample7args.py:*   call      => one(a=?, b=?, c=?) [[]backlog[]]",
        "depth=1 calls=?? *sample7args.py:*   line         two() [[]backlog[]]",
        "depth=1 calls=?? *sample7args.py:*   call         => two(a=?, b=?, c=?) [[]backlog[]]",
        "depth=2 calls=?? *sample7args.py:*   line            for i in range(1):  # two [[]backlog[]]",
        "depth=2 calls=?? *sample7args.py:*   line            a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=2 calls=?? *sample7args.py:*   line            three() [[]backlog[]]",
        "depth=2 calls=?? *sample7args.py:*   call            => three(a=?, b=?, c=?) [[]backlog[]]",
        "depth=3 calls=?? *sample7args.py:*   line               for i in range(1):  # three [[]backlog[]]",
        "depth=3 calls=?? *sample7args.py:*   line               a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=3 calls=?? *sample7args.py:*   line               four() [[]backlog[]]",
        "depth=3 calls=?? *sample7args.py:*   call               => four(a=?, b=?, c=?) [[]backlog[]]",
        "depth=4 calls=?? *sample7args.py:*   line                  for i in range(1):  # four [[]backlog[]]",
        "depth=4 calls=?? *sample7args.py:*   line                  a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=4 calls=?? *sample7args.py:*   line                  five() [[]backlog[]]",
        "depth=4 calls=?? *sample7args.py:*   call                  => five(a=?, b=?, c=?) [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     six() [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     six() [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     six() [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     a = b = c[[]'side'[]] = in_five = 'effect' [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     for i in range(1):  # five [[]backlog[]]",
        "depth=5 calls=?? *sample7args.py:*   line                     return i  # five",
        "depth=4 calls=?? *sample7args.py:*   return                <= five: 0",

    ])


def test_backlog_subprocess(LineMatcher):
    output = subprocess.check_output(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'sample7args.py')],
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    import re
    print(re.sub(r'([\[\]])', r'[\1]', output))
    print(output)
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "depth=0 calls=0   *sample7args.py:4     call      => one(a=123, b='234', c={'3': [[]4, '5'[]]}) [[]backlog[]]",
        "depth=1 calls=1   *sample7args.py:5     line         for i in range(1):  # one [[]backlog[]]",
        "depth=1 calls=1   *sample7args.py:6     line         a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=1 calls=1   *sample7args.py:7     line         two() [[]backlog[]]",
        "depth=1 calls=1   *sample7args.py:10    call         => two(a=123, b='234', c={'3': [[]4, '5'[]]}) [[]backlog[]]",
        "depth=2 calls=2   *sample7args.py:11    line            for i in range(1):  # two [[]backlog[]]",
        "depth=2 calls=2   *sample7args.py:12    line            a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=2 calls=2   *sample7args.py:13    line            three() [[]backlog[]]",
        "depth=2 calls=2   *sample7args.py:16    call            => three(a=123, b='234', c={'3': [[]4, '5'[]]}) [[]backlog[]]",
        "depth=3 calls=3   *sample7args.py:17    line               for i in range(1):  # three [[]backlog[]]",
        "depth=3 calls=3   *sample7args.py:18    line               a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=3 calls=3   *sample7args.py:19    line               four() [[]backlog[]]",
        "depth=3 calls=3   *sample7args.py:22    call               => four(a=123, b='234', c={'3': [[]4, '5'[]]}) [[]backlog[]]",
        "depth=4 calls=4   *sample7args.py:23    line                  for i in range(1):  # four [[]backlog[]]",
        "depth=4 calls=4   *sample7args.py:24    line                  a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=4 calls=4   *sample7args.py:25    line                  five() [[]backlog[]]",
        "depth=4 calls=4   *sample7args.py:28    call                  => five(a=123, b='234', c={'3': [[]4, '5'[]]})",
        "depth=5 calls=5   *sample7args.py:29    line                     six()",
        "depth=5 calls=6   *sample7args.py:30    line                     six()",
        "depth=5 calls=7   *sample7args.py:31    line                     six()",
        "depth=5 calls=8   *sample7args.py:32    line                     a = b = c[[]'side'[]] = in_five = 'effect'",
        "depth=5 calls=8   *sample7args.py:33    line                     for i in range(1):  # five",
        "depth=5 calls=8   *sample7args.py:34    line                     return i  # five",
        "depth=4 calls=8   *sample7args.py:34    return                <= five: 0",
        "depth=0 calls=8   *sample7args.py:4     call      => one(a=123, b='234', c={*'side': 'effect'*}) [[]backlog[]]",
        "depth=1 calls=9   *sample7args.py:5     line         for i in range(1):  # one [[]backlog[]]",
        "depth=1 calls=9   *sample7args.py:6     line         a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=1 calls=9   *sample7args.py:7     line         two() [[]backlog[]]",
        "depth=1 calls=9   *sample7args.py:10    call         => two(a=123, b='234', c={*'side': 'effect'*}) [[]backlog[]]",
        "depth=2 calls=10  *sample7args.py:11    line            for i in range(1):  # two [[]backlog[]]",
        "depth=2 calls=10  *sample7args.py:12    line            a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=2 calls=10  *sample7args.py:13    line            three() [[]backlog[]]",
        "depth=2 calls=10  *sample7args.py:16    call            => three(a=123, b='234', c={*'side': 'effect'*}) [[]backlog[]]",
        "depth=3 calls=11  *sample7args.py:17    line               for i in range(1):  # three [[]backlog[]]",
        "depth=3 calls=11  *sample7args.py:18    line               a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=3 calls=11  *sample7args.py:19    line               four() [[]backlog[]]",
        "depth=3 calls=11  *sample7args.py:22    call               => four(a=123, b='234', c={*'side': 'effect'*}) [[]backlog[]]",
        "depth=4 calls=12  *sample7args.py:23    line                  for i in range(1):  # four [[]backlog[]]",
        "depth=4 calls=12  *sample7args.py:24    line                  a = b = c[[]'side'[]] = 'effect' [[]backlog[]]",
        "depth=4 calls=12  *sample7args.py:25    line                  five() [[]backlog[]]",
        "depth=4 calls=12  *sample7args.py:28    call                  => five(a=123, b='234', c={*'side': 'effect'*})",
        "depth=5 calls=13  *sample7args.py:29    line                     six()",
        "depth=5 calls=14  *sample7args.py:30    line                     six()",
        "depth=5 calls=15  *sample7args.py:31    line                     six()",
        "depth=5 calls=16  *sample7args.py:32    line                     a = b = c[[]'side'[]] = in_five = 'effect'",
        "depth=5 calls=16  *sample7args.py:33    line                     for i in range(1):  # five",
        "depth=5 calls=16  *sample7args.py:34    line                     return i  # five",
        "depth=4 calls=16  *sample7args.py:34    return                <= five: 0",
    ])
