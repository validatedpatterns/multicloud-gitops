import base64
import fileinput
import logging
import os
import subprocess

import requests
import yaml
from ocp_resources.secret import Secret
from requests import HTTPError, RequestException
from urllib3.exceptions import InsecureRequestWarning, ProtocolError

from . import __loggername__

logger = logging.getLogger(__loggername__)


def load_yaml_file(file_path):
    """
    Load and parse the yaml file
    :param file_path: (str) file path
    :return: (dict) yaml_config_obj in the form of Python dict
    """
    yaml_config_obj = None
    with open(file_path, "r") as yfh:
        try:
            yaml_config_obj = yaml.load(yfh, Loader=yaml.FullLoader)
        except Exception as ex:
            raise yaml.YAMLError("YAML Syntax Error:\n %s" % ex)
        logger.info("Yaml Config : %s", yaml_config_obj)
    return yaml_config_obj


def find_number_of_edge_sites(dir_path):
    """
    Find the number of edge (managed cluster) sites folder
    :param dir_path: (dtr) dir path where edge site manifest resides
    :return: (list) site_names
    """
    site_names = list()
    list_of_dirs = os.listdir(path=dir_path)

    for site_dir in list_of_dirs:
        if "staging" in site_dir:
            site_names.append(site_dir)

    return site_names


def get_long_live_bearer_token(
    dyn_client, namespace="default", sub_string="default-token"
):
    """
    Get bearer token from secrets to authorize openshift cluster
    :param sub_string: (str) substring of secrets name to find actual secret name since openshift append random
    5 ascii digit at the end of every secret name
    :param namespace: (string) name of namespace where secret exist
    :return: (string) secret token for specified secret
    """
    filtered_secrets = []
    try:
        for secret in Secret.get(dyn_client=dyn_client, namespace=namespace):
            if sub_string in secret.instance.metadata.name:
                filtered_secrets.append(secret.instance.data.token)
    except StopIteration as e:
        logger.exception(
            "Specified substring %s doesn't exist in namespace %s: %s",
            sub_string,
            namespace,
            e,
        )
    except ProtocolError as e:
        # See https://github.com/kubernetes-client/python/issues/1225
        logger.info(
            "Skip %s... because kubelet disconnect client after default 10m...", e
        )

    # All secret tokens in openshift are base64 encoded.
    # Decode base64 string into byte and convert byte to str
    if len(filtered_secrets) > 0:
        bearer_token = base64.b64decode(filtered_secrets[-1]).decode()
        return bearer_token
    else:
        return None


def get_site_response(site_url, bearer_token):
    """

    :param site_url: (str) Site API end point
    :param bearer_token: (str) bearer token
    :return: (dict) site_response
    """
    site_response = None
    headers = {"Authorization": "Bearer " + bearer_token}

    try:
        # Suppress only the single warning from urllib3 needed.
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        site_response = requests.get(site_url, headers=headers, verify=False)
    except (ConnectionError, HTTPError, RequestException) as e:
        logger.exception(
            "Failed to connect %s due to refused connection or unsuccessful status code %s",
            site_url,
            e,
        )
    logger.debug("Site Response %s: ", site_response)

    return site_response


def execute_shell_command_local(cmd):
    """
    Executes a shell command in a subprocess, wait until it has completed.
    :param cmd: Command to execute.
    """
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    (out, error) = proc.communicate()
    exit_code = proc.wait()
    return exit_code, out, error


def modify_file_content(file_name):
    with open(file_name, "r") as frb:
        logger.debug(f"Current content : {frb.readlines()}")

    with fileinput.FileInput(file_name, inplace=True, backup=".bak") as file:
        for line in file:
            print(
                line.replace(
                    'SENSOR_TEMPERATURE_ENABLED: "false"',
                    'SENSOR_TEMPERATURE_ENABLED: "true"',
                ),
                end="",
            )

    with open(file_name, "r") as fra:
        contents = fra.readlines()
        logger.debug(f"Modified content : {contents}")

    return contents
