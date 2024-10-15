import logging
import os
import re
import subprocess
import time

import pytest
import requests
from ocp_resources.route import Route
from openshift.dynamic.exceptions import NotFoundError
from validatedpatterns_tests.interop.edge_util import modify_file_content

from . import __loggername__

logger = logging.getLogger(__loggername__)


@pytest.mark.modify_web_content
def test_modify_web_content(openshift_dyn_client):
    logger.info("Find the url for the hello-world route")
    try:
        for route in Route.get(
            dyn_client=openshift_dyn_client,
            namespace="hello-world",
            name="hello-world",
        ):
            logger.info(route.instance.spec.host)
    except NotFoundError:
        err_msg = "hello-world url/route is missing in hello-world namespace"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg

    url = "http://" + route.instance.spec.host
    response = requests.get(url)
    logger.info(f"Current page content: {response.content}")

    if os.getenv("EXTERNAL_TEST") != "true":
        chart = (
            f"{os.environ['HOME']}"
            + "/validated_patterns/multicloud-gitops/charts/"
            + "all/hello-world/templates/hello-world-cm.yaml"
        )
    else:
        chart = "../../charts/all/hello-world/templates/hello-world-cm.yaml"

    logger.info("Modify the file content")
    orig_heading = "<h1>Hello World!</h1>"
    new_heading = "<h1>Validated Patterns QE was here!</h1>"
    modify_file_content(
        file_name=chart, orig_content=orig_heading, new_content=new_heading
    )

    logger.info("Merge the change")
    patterns_repo = f"{os.environ['HOME']}/validated_patterns/multicloud-gitops"
    if os.getenv("EXTERNAL_TEST") != "true":
        subprocess.run(["git", "add", chart], cwd=f"{patterns_repo}")
        subprocess.run(
            ["git", "commit", "-m", "Updating 'hello-world'"], cwd=f"{patterns_repo}"
        )
        push = subprocess.run(
            ["git", "push"], cwd=f"{patterns_repo}", capture_output=True, text=True
        )
    else:
        subprocess.run(["git", "add", chart])
        subprocess.run(["git", "commit", "-m", "Updating 'hello-world'"])
        push = subprocess.run(["git", "push"], capture_output=True, text=True)
    logger.info(push.stdout)
    logger.info(push.stderr)

    logger.info("Checking for updated page content")
    timeout = time.time() + 60 * 10
    while time.time() < timeout:
        time.sleep(30)
        response = requests.get(url)
        logger.info(response.content)

        new_content = re.search(new_heading, str(response.content))

        logger.info(new_content)
        if (new_content is None) or (new_content.group() != new_heading):
            continue
        break

    if (new_content is None) or (new_content.group() != new_heading):
        err_msg = "Did not find updated page content"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Found updated page content")
