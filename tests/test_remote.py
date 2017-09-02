import os
import platform
import signal
import sys

import process_tests
import pytest

TIMEOUT = int(os.getenv('HUNTER_TEST_TIMEOUT', 10))


@pytest.mark.skipif('platform.system() == "Windows"')
def test_manhole():
    with process_tests.TestProcess(sys.executable, '-mtarget', 'manhole') as target, \
         process_tests.dump_on_error(target.read):

            process_tests.wait_for_strings(target.read, TIMEOUT, 'Oneshot activation is done by signal')

            with process_tests.TestProcess('hunter-trace', '-p', str(target.proc.pid), 'stdlib=False') as tracer,\
                 process_tests.dump_on_error(tracer.read):

                process_tests.wait_for_strings(
                    tracer.read, TIMEOUT,
                    'Output stream active. Starting tracer',
                    'call      => stuff()',
                    'line         time.sleep(1)',
                    'return    <= stuff: None',
                )
            process_tests.wait_for_strings(target.read, TIMEOUT, 'Broken pipe. Stopping tracer.')


@pytest.mark.skipif('platform.system() == "Windows"')
def test_manhole_clean_exit():
    with process_tests.TestProcess(sys.executable, '-mtarget', 'manhole') as target, \
         process_tests.dump_on_error(target.read):

            process_tests.wait_for_strings(target.read, TIMEOUT, 'Oneshot activation is done by signal')

            with process_tests.TestProcess('hunter-trace', '-p', str(target.proc.pid), 'stdlib=False') as tracer,\
                 process_tests.dump_on_error(tracer.read):

                process_tests.wait_for_strings(
                    tracer.read, TIMEOUT,
                    'Output stream active. Starting tracer',
                    'call      => stuff()',
                    'line         time.sleep(1)',
                    'return    <= stuff: None',
                )
                target.reset()
                tracer.proc.send_signal(signal.SIGINT)
            process_tests.wait_for_strings(target.read, TIMEOUT,
                                           'remote.deactivate()',
                                           'Doing stuff',
                                           'Doing stuff',
                                           'Doing stuff')


@pytest.mark.skipif('platform.system() == "Windows"')
@pytest.mark.skipif('platform.python_implementation() == "PyPy"')
def test_gdb():
    with process_tests.TestProcess(sys.executable, '-mtarget', 'manhole') as target, \
         process_tests.dump_on_error(target.read):
            with process_tests.TestProcess('hunter-trace', '-p', str(target.proc.pid),
                                           '--gdb', 'stdlib=False') as tracer,\
                 process_tests.dump_on_error(tracer.read):

                process_tests.wait_for_strings(
                    tracer.read, TIMEOUT,
                    'WARNING: Using GDB may deadlock the process or create unpredictable results!',
                    'Output stream active. Starting tracer',
                    'call      => stuff()',
                    'line         time.sleep(1)',
                    'return    <= stuff: None',
                )
            process_tests.wait_for_strings(target.read, TIMEOUT, 'Broken pipe. Stopping tracer.')


@pytest.mark.skipif('platform.system() == "Windows"')
@pytest.mark.skipif('platform.python_implementation() == "PyPy"')
def test_gdb_clean_exit():
    with process_tests.TestProcess(sys.executable, '-mtarget', 'manhole') as target, \
         process_tests.dump_on_error(target.read):

            with process_tests.TestProcess('hunter-trace', '-p', str(target.proc.pid),
                                           'stdlib=False', '--gdb') as tracer,\
                 process_tests.dump_on_error(tracer.read):

                process_tests.wait_for_strings(
                    tracer.read, TIMEOUT,
                    'WARNING: Using GDB may deadlock the process or create unpredictable results!',
                    'Output stream active. Starting tracer',
                    'call      => stuff()',
                    'line         time.sleep(1)',
                    'return    <= stuff: None',
                )
                target.reset()
                tracer.proc.send_signal(signal.SIGINT)
            process_tests.wait_for_strings(target.read, TIMEOUT,
                                           'Doing stuff',
                                           'Doing stuff',
                                           'Doing stuff')
