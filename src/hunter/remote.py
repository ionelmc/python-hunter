from __future__ import print_function

import argparse
import errno
import os
import signal
import socket
import sys
import time
from contextlib import closing

import manhole
from manhole.cli import parse_signal
from manhole import get_peercred
from . import stop, trace
from . import actions


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


def connect_manhole(pid, timeout, signal, gdb):
    if gdb:
        pass
    else:
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


def deactivate():
    actions.DEFAULT_STREAM = sys.stderr
    stop()

parser = argparse.ArgumentParser(description='Connect to a manhole.')
parser.add_argument('-p', '--pid', metavar='PID', type=int, required=True,
                    help='A numerical process id, or a path in the form: /tmp/manhole-1234')
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

    stdout = os.fdopen(sys.stdout.fileno(), 'wb', 0)
    encoding = getattr(sys.stdout, 'encoding', 'utf-8')
    payload = 'from hunter import remote; remote.activate(%r, %r, %r, %r)\nexit()' % (
        sink_path,
        sys.stdout.isatty(),
        encoding,
        ','.join(i.strip(',') for i in args.options)
    )
    manhole = connect_manhole(args.pid, args.timeout, args.signal, args.gdb)
    manhole.send(payload.encode('utf-8'))
    manhole.close()
    try:
        with closing(sink), closing(manhole), closing(sink.accept()[0]) as conn:
            pid, _, _ = get_peercred(conn)
            if pid != args.pid:
                raise Exception("Unexpected pid %r connected to output socket. Was expecting %s." % (pid, args.pid))
            data = conn.recv(1024)
            while data:
                stdout.write(data)
                data = conn.recv(1024)
    finally:
        manhole = connect_manhole(args.pid, args.timeout, args.signal, args.gdb)
        manhole.send(b'from hunter import remote; remote.deactivate()')
        manhole.close()

