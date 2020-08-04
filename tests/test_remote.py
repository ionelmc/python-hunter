import distutils.spawn
import os
import platform
import signal
import sys

import pytest
from process_tests import TestProcess
from process_tests import dump_on_error
from process_tests import wait_for_strings

TIMEOUT = int(os.getenv('HUNTER_TEST_TIMEOUT', 10))

platform, distutils.spawn


@pytest.mark.skipif('platform.system() == "Windows"')
def test_manhole():
    with TestProcess('python', '-mtarget', 'manhole') as target, dump_on_error(target.read):
        wait_for_strings(target.read, TIMEOUT, 'Oneshot activation is done by signal')

        with TestProcess('hunter-trace', '-p', str(target.proc.pid), 'stdlib=False') as tracer, dump_on_error(tracer.read):
            wait_for_strings(
                tracer.read, TIMEOUT,
                'Output stream active. Starting tracer',
                'call      => stuff()',
                'line         time.sleep(1)',
                'return    <= stuff: None',
            )
        wait_for_strings(target.read, TIMEOUT, 'Broken pipe', 'Stopping tracer.')


@pytest.mark.skipif('platform.system() == "Windows"')
def test_manhole_clean_exit():
    with TestProcess('python', '-mtarget', 'manhole') as target, dump_on_error(target.read):
        wait_for_strings(target.read, TIMEOUT, 'Oneshot activation is done by signal')

        with TestProcess('hunter-trace', '-p', str(target.proc.pid), 'stdlib=False') as tracer, dump_on_error(tracer.read):
            wait_for_strings(
                tracer.read, TIMEOUT,
                'Output stream active. Starting tracer',
                'call      => stuff()',
                'line         time.sleep(1)',
                'return    <= stuff: None',
            )
            target.reset()
            tracer.proc.send_signal(signal.SIGINT)
        wait_for_strings(target.read, TIMEOUT,
                         'remote.deactivate()',
                         'Doing stuff',
                         'Doing stuff',
                         'Doing stuff')


@pytest.mark.skipif('platform.system() == "Windows"')
@pytest.mark.skipif('platform.machine() == "aarch64"')
@pytest.mark.skipif('platform.python_implementation() == "PyPy"')
@pytest.mark.skipif('not distutils.spawn.find_executable("gdb")')
def test_gdb():
    with TestProcess('python', '-mtarget', 'manhole') as target, dump_on_error(target.read):
        with TestProcess('hunter-trace', '-p', str(target.proc.pid),
                         '--gdb', 'stdlib=False') as tracer, dump_on_error(tracer.read):
            wait_for_strings(
                tracer.read, TIMEOUT,
                'WARNING: Using GDB may deadlock the process or create unpredictable results!',
                'Output stream active. Starting tracer',
                'call      => stuff()',
                'line         time.sleep(1)',
                'return    <= stuff: None',
            )
        wait_for_strings(target.read, TIMEOUT, 'Broken pipe', 'Stopping tracer.')


@pytest.mark.skipif('platform.system() == "Windows"')
@pytest.mark.skipif('platform.machine() == "aarch64"')
@pytest.mark.skipif('platform.python_implementation() == "PyPy"')
@pytest.mark.skipif('not distutils.spawn.find_executable("gdb")')
def test_gdb_clean_exit():
    with TestProcess(sys.executable, '-mtarget', 'manhole') as target, dump_on_error(target.read):
        with TestProcess('hunter-trace', '-p', str(target.proc.pid),
                         'stdlib=False', '--gdb') as tracer, dump_on_error(tracer.read):
            wait_for_strings(
                tracer.read, TIMEOUT,
                'WARNING: Using GDB may deadlock the process or create unpredictable results!',
                'Output stream active. Starting tracer',
                'call      => stuff()',
                'line         time.sleep(1)',
                'return    <= stuff: None',
            )
            target.reset()
            tracer.proc.send_signal(signal.SIGINT)
        wait_for_strings(target.read, TIMEOUT,
                         'Doing stuff',
                         'Doing stuff',
                         'Doing stuff')
