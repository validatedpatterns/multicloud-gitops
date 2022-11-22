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

from collections.abc import MutableMapping

import yaml


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
