import logging

import pytest
from ocp_resources.cluster_version import ClusterVersion
from ocp_resources.subscription import Subscription

from . import __loggername__

logger = logging.getLogger(__loggername__)


@pytest.mark.subscription_status_edge
def test_subscription_status_edge(openshift_dyn_client):
    # These are the operator subscriptions and their associated namespaces
    expected_subs = {
        "openshift-gitops-operator": ["openshift-operators"],
    }

    operator_versions = []
    missing_subs = []
    unhealthy_subs = []
    missing_installplans = []
    upgrades_pending = []

    for key in expected_subs.keys():
        for val in expected_subs[key]:
            try:
                subs = Subscription.get(
                    dyn_client=openshift_dyn_client, name=key, namespace=val
                )
                sub = next(subs)
            except StopIteration:
                missing_subs.append(f"{key} in {val} namespace")
                continue

            logger.info(
                f"State for {sub.instance.metadata.name}: {sub.instance.status.state}"
            )
            if sub.instance.status.state == "UpgradePending":
                upgrades_pending.append(
                    f"{sub.instance.metadata.name} in {sub.instance.metadata.namespace} namespace"
                )

            logger.info(
                f"CatalogSourcesUnhealthy: {sub.instance.status.conditions[0].status}"
            )
            if sub.instance.status.conditions[0].status != "False":
                logger.info(f"Subscription {sub.instance.metadata.name} is unhealthy")
                unhealthy_subs.append(sub.instance.metadata.name)
            else:
                operator_versions.append(
                    f"installedCSV: {sub.instance.status.installedCSV}"
                )

            logger.info(f"installPlanRef: {sub.instance.status.installPlanRef}")
            if not sub.instance.status.installPlanRef:
                logger.info(
                    f"No install plan found for subscription {sub.instance.metadata.name} "
                    f"in {sub.instance.metadata.namespace} namespace"
                )
                missing_installplans.append(
                    f"{sub.instance.metadata.name} in {sub.instance.metadata.namespace} namespace"
                )

            logger.info("")

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

    for line in operator_versions:
        logger.info(line)

    versions = ClusterVersion.get(dyn_client=openshift_dyn_client)
    version = next(versions)
    logger.info(f"Openshift version:\n{version.instance.status.history}")

    if missing_subs or unhealthy_subs or missing_installplans or upgrades_pending:
        err_msg = "Subscription status check failed"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Subscription status check passed")
