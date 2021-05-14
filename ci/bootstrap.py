#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
import pathlib
import subprocess
import sys

self_path = pathlib.Path(__file__).resolve()
base_path = self_path.parent.parent
template_path = base_path.joinpath('ci', 'templates')


def check_call(args):
    print('+', *args)
    subprocess.check_call(args)


def exec_in_env():
    env_path = base_path.joinpath('.tox', 'bootstrap')
    if sys.platform == 'win32':
        bin_path = env_path.joinpath('Scripts')
    else:
        bin_path = env_path.joinpath('bin')
    if not env_path.exists():
        print('Making bootstrap env in: {0} ...'.format(env_path))
        try:
            check_call([sys.executable, '-m', 'venv', env_path])
        except subprocess.CalledProcessError:
            try:
                check_call([sys.executable, '-m', 'virtualenv', env_path])
            except subprocess.CalledProcessError:
                check_call(['virtualenv', env_path])
        print('Installing `jinja2` into bootstrap environment...')
        check_call([bin_path.joinpath('pip'), 'install', 'jinja2', 'tox'])
    python_executable = bin_path.joinpath('python')
    if not python_executable.exists():
        python_executable = '{}.exe'.format(python_executable)
    else:
        python_executable = str(python_executable)

    print('Re-executing with: {0}'.format(python_executable))
    print('+ exec', python_executable, self_path, '--no-env')
    os.execv(python_executable, [python_executable, self_path, '--no-env'])


def main():
    import jinja2

    print('Project path: {0}'.format(base_path))

    # noinspection JinjaAutoinspect
    jinja = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_path)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    tox_environments = [
        line.strip()
        # 'tox' need not be installed globally, but must be importable
        # by the Python that is running this script.
        # This uses sys.executable the same way that the call in
        # cookiecutter-pylibrary/hooks/post_gen_project.py
        # invokes this bootstrap.py itself.
        for line in subprocess.check_output([sys.executable, '-m', 'tox', '--listenvs'], universal_newlines=True).splitlines()
    ]
    tox_environments = [line for line in tox_environments if line.startswith('py')]

    for path in template_path.rglob('*'):
        if path.is_dir():
            continue
        name = path.relative_to(template_path)
        with base_path.joinpath(name).open('w') as fh:
            fh.write(jinja.get_template(str(name)).render(tox_environments=tox_environments))
        print('Wrote {}'.format(name))
    print('DONE.')


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--no-env']:
        main()
    elif not args:
        exec_in_env()
    else:
        print('Unexpected arguments {0}'.format(args), file=sys.stderr)
        sys.exit(1)
