# Copyright 2022 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Module that implements some common functions
"""

import contextlib
import io
import os
import subprocess
import sys
import termios
import time
from collections.abc import MutableMapping

import yaml


def _raw_input(prompt="", stream=None, input=None):
    # This doesn't save the string in the GNU readline history.
    if not stream:
        stream = sys.stderr
    if not input:
        input = sys.stdin
    prompt = str(prompt)
    if prompt:
        try:
            stream.write(prompt)
        except UnicodeEncodeError:
            # Use replace error handler to get as much as possible printed.
            prompt = prompt.encode(stream.encoding, "replace")
            prompt = prompt.decode(stream.encoding)
            stream.write(prompt)
        stream.flush()
    # NOTE: The Python C API calls flockfile() (and unlock) during readline.
    line = input.readline()
    if not line:
        raise EOFError
    if line[-1] == "\n":
        line = line[:-1]
    return line


def get_input(prompt="", stream=None):
    """Prompt for a password, with echo turned off.
    Args:
      prompt: Written on stream to ask for the input.  Default: 'Password: '
      stream: A writable file object to display the prompt.  Defaults to
              the tty.  If no tty is available defaults to sys.stderr.
    Returns:
      The seKr3t input.
    Raises:
      EOFError: If our input tty or stdin was closed.
    Always restores terminal settings before returning.
    """
    passwd = None
    with contextlib.ExitStack() as stack:
        try:
            # Always try reading and writing directly on the tty first.
            fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
            tty = io.FileIO(fd, "w+")
            stack.enter_context(tty)
            input = io.TextIOWrapper(tty)
            stack.enter_context(input)
            if not stream:
                stream = input
        except OSError:
            # If that fails, see if stdin can be controlled.
            stack.close()
            try:
                fd = sys.stdin.fileno()
            except (AttributeError, ValueError):
                fd = None
            input = sys.stdin
            if not stream:
                stream = sys.stderr

        if fd is not None:
            try:
                old = termios.tcgetattr(fd)  # a copy to save
                new = old[:]
                # new[3] &= ~termios.ECHO  # 3 == 'lflags'
                tcsetattr_flags = termios.TCSAFLUSH
                if hasattr(termios, "TCSASOFT"):
                    tcsetattr_flags |= termios.TCSASOFT
                try:
                    termios.tcsetattr(fd, tcsetattr_flags, new)
                    passwd = _raw_input(prompt, stream, input=input)
                finally:
                    termios.tcsetattr(fd, tcsetattr_flags, old)
                    stream.flush()  # issue7208
            except termios.error:
                if passwd is not None:
                    # _raw_input succeeded.  The final tcsetattr failed.  Reraise
                    # instead of leaving the terminal in an unknown state.
                    raise
                # We can't control the tty or stdin.  Give up and use normal IO.
                if stream is not input:
                    # clean up unused file objects before blocking
                    stack.close()

        stream.write("\n")
        return passwd


def parse_values(values_file):
    """
    Parses a values-secrets.yaml file (usually placed in ~)
    and returns a Python Obect with the parsed yaml.

    Parameters:
        values_file(str): The path of the values-secrets.yaml file
        to be parsed.

    Returns:
        secrets_yaml(obj): The python object containing the parsed yaml
    """
    with open(values_file, "r", encoding="utf-8") as file:
        secrets_yaml = yaml.safe_load(file.read())
    if secrets_yaml is None:
        return {}
    return secrets_yaml


def get_version(syaml):
    """
    Return the version: of the parsed yaml object. If it does not exist
    return 1.0

    Returns:
        ret(str): The version value in of the top-level 'version:' key
    """
    return str(syaml.get("version", "1.0"))


def run_command(command, attempts=1, sleep=3):
    """
    Runs a command on the host ansible is running on. A failing command
    will raise an exception in this function directly (due to check=True)

    Parameters:
        command(str): The command to be run.
        attempts(int): Number of times to retry in case of Error (defaults to 1)
        sleep(int): Number of seconds to wait in between retry attempts (defaults to 3s)

    Returns:
        ret(subprocess.CompletedProcess): The return value from run()
    """
    for attempt in range(attempts):
        try:
            ret = subprocess.run(
                command,
                shell=True,
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=True,
            )
            return ret
        except subprocess.CalledProcessError as e:
            # We reached maximum nr of retries. Re-raise the last error
            if attempt >= attempts - 1:
                raise e
            time.sleep(sleep)


def flatten(dictionary, parent_key=False, separator="."):
    """
    Turn a nested dictionary into a flattened dictionary and also
    drop any key that has 'None' as their value

    Parameters:
        dictionary(dict): The dictionary to flatten

        parent_key(str): The string to prepend to dictionary's keys

        separator(str): The string used to separate flattened keys

    Returns:

        dictionary: A flattened dictionary where the keys represent the
        path to reach the leaves
    """

    items = []
    for key, value in dictionary.items():
        new_key = str(parent_key) + separator + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten(value, new_key, separator).items())
        elif isinstance(value, list):
            for k, v in enumerate(value):
                items.extend(flatten({str(k): v}, new_key).items())
        else:
            if value is not None:
                items.append((new_key, value))
    return dict(items)
