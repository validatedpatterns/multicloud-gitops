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

# Configurable timeout settings (can be overridden via environment)
CONTENT_UPDATE_TIMEOUT_MINUTES = int(
    os.environ.get("CONTENT_UPDATE_TIMEOUT_MINUTES", "10")
)
CONTENT_UPDATE_POLL_SECONDS = int(os.environ.get("CONTENT_UPDATE_POLL_SECONDS", "30"))

# Configurable repository path (can be overridden via environment)
PATTERNS_REPO_PATH = os.environ.get(
    "PATTERNS_REPO_PATH",
    os.path.join(os.environ.get("HOME", ""), "validated_patterns/multicloud-gitops"),
)


@pytest.mark.modify_web_content
def test_modify_web_content(openshift_dyn_client):
    logger.info("Find the url for the hello-world route")
    route = None
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

    if route is None:
        err_msg = "No route found for hello-world in hello-world namespace"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg

    url = "http://" + route.instance.spec.host
    response = requests.get(url)
    logger.info(f"Current page content: {response.content}")

    if os.getenv("EXTERNAL_TEST") != "true":
        chart = os.path.join(
            PATTERNS_REPO_PATH, "charts/all/hello-world/templates/hello-world-cm.yaml"
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
    patterns_repo = PATTERNS_REPO_PATH
    if os.getenv("EXTERNAL_TEST") != "true":
        git_add = subprocess.run(
            ["git", "add", chart], cwd=patterns_repo, capture_output=True, text=True
        )
        if git_add.returncode != 0:
            logger.error(f"git add failed: {git_add.stderr}")

        git_commit = subprocess.run(
            ["git", "commit", "-m", "Updating 'hello-world'"],
            cwd=patterns_repo,
            capture_output=True,
            text=True,
        )
        if git_commit.returncode != 0:
            logger.warning(f"git commit returned non-zero: {git_commit.stderr}")

        push = subprocess.run(
            ["git", "push"], cwd=patterns_repo, capture_output=True, text=True
        )
    else:
        git_add = subprocess.run(["git", "add", chart], capture_output=True, text=True)
        if git_add.returncode != 0:
            logger.error(f"git add failed: {git_add.stderr}")

        git_commit = subprocess.run(
            ["git", "commit", "-m", "Updating 'hello-world'"],
            capture_output=True,
            text=True,
        )
        if git_commit.returncode != 0:
            logger.warning(f"git commit returned non-zero: {git_commit.stderr}")

        push = subprocess.run(["git", "push"], capture_output=True, text=True)

    if push.returncode != 0:
        logger.error(f"git push failed with return code {push.returncode}")
    logger.info(push.stdout)
    logger.info(push.stderr)

    logger.info("Checking for updated page content")
    timeout = time.time() + 60 * CONTENT_UPDATE_TIMEOUT_MINUTES
    new_content = None
    while time.time() < timeout:
        time.sleep(CONTENT_UPDATE_POLL_SECONDS)
        response = requests.get(url)
        logger.info(response.content)

        new_content = re.search(new_heading, str(response.content))

        logger.info(new_content)
        if new_content is not None and new_content.group() == new_heading:
            break

    if new_content is None or new_content.group() != new_heading:
        err_msg = "Did not find updated page content"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Found updated page content")
