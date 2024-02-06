import os

import pytest
from kubernetes import config
from kubernetes.client import Configuration
from openshift.dynamic import DynamicClient

from . import __loggername__
from .css_logger import CSS_Logger


def pytest_addoption(parser):
    parser.addoption(
        "--kubeconfig",
        action="store",
        default=None,
        help="The full path to the kubeconfig file to be used",
    )


@pytest.fixture(scope="session")
def get_kubeconfig(request):
    if request.config.getoption("--kubeconfig"):
        k8config = request.config.getoption("--kubeconfig")
    elif "KUBECONFIG" in os.environ.keys() and os.environ["KUBECONFIG"]:
        k8config = os.environ["KUBECONFIG"]
    else:
        raise ValueError(
            "A kubeconfig file was not provided. Please provide one either "
            "via the --kubeconfig command option or by setting a KUBECONFIG "
            "environment variable"
        )
    return k8config


@pytest.fixture(scope="session")
def kube_config(get_kubeconfig):
    kc = Configuration
    config.load_kube_config(config_file=get_kubeconfig, client_configuration=kc)
    return kc


@pytest.fixture(scope="session")
def openshift_dyn_client(get_kubeconfig):
    return DynamicClient(client=config.new_client_from_config(get_kubeconfig))


@pytest.fixture(scope="session", autouse=True)
def setup_logger():
    logger = CSS_Logger(__loggername__)
    return logger
