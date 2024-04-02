import logging

import pytest
from validatedpatterns_tests.interop import subscription

from . import __loggername__

logger = logging.getLogger(__loggername__)


@pytest.mark.subscription_status_edge
def test_subscription_status_edge(openshift_dyn_client):
    # These are the operator subscriptions and their associated namespaces
    expected_subs = {
        "openshift-gitops-operator": ["openshift-operators"],
    }

    (
        operator_versions,
        missing_subs,
        unhealthy_subs,
        missing_installplans,
        upgrades_pending,
    ) = subscription.subscription_status(openshift_dyn_client, expected_subs)

    for line in operator_versions:
        logger.info(line)

    cluster_version = subscription.openshift_version(openshift_dyn_client)
    logger.info(f"Openshift version:\n{cluster_version.instance.status.history}")

    if missing_subs or unhealthy_subs or missing_installplans or upgrades_pending:
        err_msg = "Subscription status check failed"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Subscription status check passed")
