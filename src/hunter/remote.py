from __future__ import print_function

import argparse
import errno
import json
import os
import signal
import socket
import sys
import time
from contextlib import closing
from contextlib import contextmanager
from subprocess import check_call

import manhole
from manhole import get_peercred
from manhole.cli import parse_signal

from . import actions
from . import stop
from . import trace


def install(**kwargs):
    kwargs.setdefault('oneshot_on', 'URG')
    kwargs.setdefault('connection_handler', 'exec')
    manhole.install(**kwargs)


class RemoteStream(object):
    def __init__(self, path, isatty, encoding):
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(path)
        self._isatty = isatty
        self._encoding = encoding

    def isatty(self):
        return self._isatty

    def write(self, data):
        try:
            self._sock.send(data.encode(self._encoding))
        except Exception as exc:
            print("Hunter failed to send trace output: %s. Stopping tracer." % exc, file=sys.stderr)
            stop()

    def flush(self):
        pass


@contextmanager
def manhole_bootstrap(args, activation_payload, deactivation_payload):
    activation_payload += '\nexit()\n'
    deactivation_payload += '\nexit()\n'

    activation_payload = activation_payload.encode('utf-8')
    deactivation_payload = deactivation_payload.encode('utf-8')

    with closing(connect_manhole(args.pid, args.timeout, args.signal)) as manhole:
        manhole.send(activation_payload)
    try:
        yield
    finally:
        with closing(connect_manhole(args.pid, args.timeout, args.signal)) as manhole:
            manhole.send(deactivation_payload)


@contextmanager
def gdb_bootstrap(args, activation_payload, deactivation_payload):
    print('WARNING: Using GDB may deadlock the process or create unpredictable results!')
    activation_command = [
        'gdb', '-p', str(args.pid), '-batch',
        '-ex', 'call (void)Py_AddPendingCall(PyRun_SimpleString, %s)' % json.dumps(activation_payload),
    ]
    deactivation_command = [
        'gdb', '-p', str(args.pid), '-batch',
        '-ex', 'call (void)Py_AddPendingCall(PyRun_SimpleString, %s)' % json.dumps(deactivation_payload),
    ]
    check_call(activation_command)
    try:
        yield
    finally:
        check_call(deactivation_command)


def connect_manhole(pid, timeout, signal):
    os.kill(pid, signal)

    start = time.time()
    uds_path = '/tmp/manhole-%s' % pid
    manhole = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    manhole.settimeout(timeout)
    while time.time() - start < timeout:
        try:
            manhole.connect(uds_path)
        except Exception as exc:
            if exc.errno not in (errno.ENOENT, errno.ECONNREFUSED):
                print("Failed to connect to %r: %r" % (uds_path, exc), file=sys.stderr)
        else:
            break
    else:
        print("Failed to connect to %r: Timeout" % uds_path, file=sys.stderr)
        sys.exit(5)
    return manhole


def activate(sink_path, isatty, encoding, options):
    stream = actions.DEFAULT_STREAM = RemoteStream(sink_path, isatty, encoding)
    try:
        stream.write("Output stream active. Starting tracer ...\n\n")
        eval("trace(%s)" % options)
    except Exception as exc:
        stream.write("Failed to activate: %s. %s\n" % (
            exc,
            'Tracer options where: %s.' % options if options else 'No tracer options.'
        ))
        actions.DEFAULT_STREAM = sys.stderr
        raise


trace  # used in eval above


def deactivate():
    actions.DEFAULT_STREAM = sys.stderr
    stop()


parser = argparse.ArgumentParser(description='Trace a process.')
parser.add_argument('-p', '--pid', metavar='PID', type=int, required=True,
                    help='A numerical process id.')
parser.add_argument('options', metavar='OPTIONS', nargs='*')
parser.add_argument('-t', '--timeout', dest='timeout', default=1, type=float,
                    help='Timeout to use. Default: %(default)s seconds.')
parser.add_argument('--gdb', dest='gdb', action='store_true',
                    help='Use GDB to activate tracing. WARNING: it may deadlock the process!')
parser.add_argument('-s', '--signal', dest='signal', type=parse_signal, metavar="SIGNAL", default=signal.SIGURG,
                    help='Send the given SIGNAL to the process before connecting.')


def main():
    args = parser.parse_args()

    sink = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sink_path = '/tmp/hunter-%s' % os.getpid()
    sink.bind(sink_path)
    sink.listen(1)
    os.chmod(sink_path, 0o777)

    stdout = os.fdopen(sys.stdout.fileno(), 'wb', 0)
    encoding = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
    bootstrapper = gdb_bootstrap if args.gdb else manhole_bootstrap
    payload = 'from hunter import remote; remote.activate(%r, %r, %r, %r)' % (
        sink_path,
        sys.stdout.isatty(),
        encoding,
        ','.join(i.strip(',') for i in args.options)
    )
    with bootstrapper(args, payload, 'from hunter import remote; remote.deactivate()'):
        conn, _ = sink.accept()
        os.unlink(sink_path)
        pid, _, _ = get_peercred(conn)
        if pid != args.pid:
            raise Exception("Unexpected pid %r connected to output socket. Was expecting %s." % (pid, args.pid))
        data = conn.recv(1024)
        while data:
            stdout.write(data)
            data = conn.recv(1024)
