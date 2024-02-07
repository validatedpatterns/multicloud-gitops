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

import configparser
from collections.abc import MutableMapping


def find_dupes(array):
    """
    Returns duplicate items in a list

    Parameters:
        l(list): Array to check for duplicate entries

    Returns:
        dupes(list): Array containing all the duplicates and [] is there are none
    """
    seen = set()
    dupes = []
    for x in array:
        if x in seen:
            dupes.append(x)
        else:
            seen.add(x)
    return dupes


def get_version(syaml):
    """
    Return the version: of the parsed yaml object. If it does not exist
    return 1.0

    Returns:
        ret(str): The version value in of the top-level 'version:' key
    """
    return str(syaml.get("version", "1.0"))


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


def get_ini_value(inifile, inisection, inikey):
    """
    Return a value from an ini-file or 'None' if it does not exist

    Parameters:
        inifile(str): The path to the ini-file

        inisection(str): The section in the ini-file to look for the key

        inikey(str): The key to look up inside the ini-file's section

    Returns:

        obj: The value of the key or None if it does not exist
    """
    config = configparser.ConfigParser()
    config.read(inifile)
    return config.get(inisection, inikey, fallback=None)


def stringify_dict(input_dict):
    """
    Return a dict whose keys and values are all co-erced to strings, for creating labels and annotations in the
    python Kubernetes module

    Parameters:
        input_dict(dict): A dictionary of keys and values

    Returns:

        obj: The same dict in the same order but with the keys coerced to str
    """
    output_dict = {}

    for key, value in input_dict.items():
        output_dict[str(key)] = str(value)

    return output_dict
