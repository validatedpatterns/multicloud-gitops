import difflib
import logging
import os
import re
import subprocess

import pytest
from validatedpatterns_tests.interop import subscription

from . import __loggername__

logger = logging.getLogger(__loggername__)


@pytest.mark.subscription_status_hub
def test_subscription_status_hub(openshift_dyn_client):
    # These are the operator subscriptions and their associated namespaces
    expected_subs = {
        "openshift-gitops-operator": ["openshift-operators"],
        "advanced-cluster-management": ["open-cluster-management"],
        "multicluster-engine": ["multicluster-engine"],
    }

    (
        operator_versions,
        missing_subs,
        unhealthy_subs,
        missing_installplans,
        upgrades_pending,
    ) = subscription.subscription_status(openshift_dyn_client, expected_subs)

    if missing_subs:
        logger.error(f"FAIL: The following subscriptions are missing: {missing_subs}")
    if unhealthy_subs:
        logger.error(
            f"FAIL: The following subscriptions are unhealthy: {unhealthy_subs}"
        )
    if missing_installplans:
        logger.error(
            f"FAIL: The install plan for the following subscriptions is missing: {missing_installplans}"
        )
    if upgrades_pending:
        logger.error(
            f"FAIL: The following subscriptions are in UpgradePending state: {upgrades_pending}"
        )

    cluster_version = subscription.openshift_version(openshift_dyn_client)
    logger.info(f"Openshift version:\n{cluster_version.instance.status.history}")

    if os.getenv("EXTERNAL_TEST") != "true":
        shortversion = re.sub("(.[0-9]+$)", "", os.getenv("OPENSHIFT_VER"))
        currentfile = os.getcwd() + "/operators_hub_current"
        sourceFile = open(currentfile, "w")
        for line in operator_versions:
            logger.info(line)
            print(line, file=sourceFile)
        sourceFile.close()

        logger.info("Clone operator-versions repo")
        try:
            operator_versions_repo = (
                "git@gitlab.cee.redhat.com:mpqe/mps/vp/operator-versions.git"
            )
            clone = subprocess.run(
                ["git", "clone", operator_versions_repo], capture_output=True, text=True
            )
            logger.info(clone.stdout)
            logger.info(clone.stderr)
        except Exception:
            pass

        previouspath = os.getcwd() + f"/operator-versions/mcgitops_hub_{shortversion}"
        previousfile = f"mcgitops_hub_{shortversion}"

        logger.info("Ensure previous file exists")
        checkpath = os.path.exists(previouspath)
        logger.info(checkpath)

        if checkpath is True:
            logger.info("Diff current operator list with previous file")
            diff = opdiff(open(previouspath).readlines(), open(currentfile).readlines())
            diffstring = "".join(diff)
            logger.info(diffstring)

            logger.info("Write diff to file")
            sourceFile = open("operator_diffs_hub.log", "w")
            print(diffstring, file=sourceFile)
            sourceFile.close()
        else:
            logger.info("Skipping operator diff - previous file not found")

    if missing_subs or unhealthy_subs or missing_installplans or upgrades_pending:
        err_msg = "Subscription status check failed"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        # Only push the new operarator list if the test passed
        # and we are not testing a pre-release operator nor
        # running externally
        if os.getenv("EXTERNAL_TEST") != "true":
            if checkpath is True and not os.environ["INDEX_IMAGE"]:
                os.remove(previouspath)
                os.rename(currentfile, previouspath)

                cwd = os.getcwd() + "/operator-versions"
                logger.info(f"CWD: {cwd}")

                logger.info("Push new operator list")
                subprocess.run(["git", "add", previousfile], cwd=cwd)
                subprocess.run(
                    ["git", "commit", "-m", "Update operator versions list"],
                    cwd=cwd,
                )
                subprocess.run(["git", "push"], cwd=cwd)

        logger.info("PASS: Subscription status check passed")


def opdiff(*args):
    return filter(lambda x: not x.startswith(" "), difflib.ndiff(*args))
