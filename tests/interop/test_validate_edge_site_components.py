import logging
import os

import pytest
from ocp_resources.route import Route
from validatedpatterns_tests.interop import components
from validatedpatterns_tests.interop.crd import ArgoCD
from validatedpatterns_tests.interop.edge_util import (
    get_long_live_bearer_token,
    get_site_response,
)

from . import __loggername__

logger = logging.getLogger(__loggername__)

oc = os.environ["HOME"] + "/oc_client/oc"

"""
Validate following multicloud-gitops components pods and endpoints on edge site (line server):

1) argocd
2) ACM agents
3) applications health (Applications deployed through argocd)
"""


@pytest.mark.test_validate_edge_site_components
def test_validate_edge_site_components():
    logger.info("Checking Openshift version on edge site")
    version_out = components.dump_openshift_version()
    logger.info(f"Openshift version:\n{version_out}")


@pytest.mark.validate_edge_site_reachable
def test_validate_edge_site_reachable(kube_config, openshift_dyn_client):
    logger.info("Check if edge site API end point is reachable")
    edge_api_url = kube_config.host
    if not edge_api_url:
        err_msg = "Edge site url is missing in kubeconfig file"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info(f"EDGE api url : {edge_api_url}")

    bearer_token = get_long_live_bearer_token(
        dyn_client=openshift_dyn_client,
        namespace="openshift-gitops",
        sub_string="argocd-dex-server-token",
    )

    if not bearer_token:
        assert False, "Bearer token is missing for argocd-dex-server"

    edge_api_response = get_site_response(
        site_url=edge_api_url, bearer_token=bearer_token
    )

    if edge_api_response.status_code != 200:
        err_msg = "Edge site is not reachable. Please check the deployment."
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Edge site is reachable")


@pytest.mark.check_pod_status_edge
def test_check_pod_status(openshift_dyn_client):
    logger.info("Checking pod status")

    err_msg = []
    projects = [
        "openshift-operators",
        "open-cluster-management-agent",
        "open-cluster-management-agent-addon",
        "openshift-gitops",
    ]

    missing_projects = components.check_project_absense(openshift_dyn_client, projects)
    missing_pods = []
    failed_pods = []

    for project in projects:
        missing_pods += components.check_pod_absence(openshift_dyn_client, project)
        failed_pods += components.check_pod_status(openshift_dyn_client, project)

    if missing_projects:
        err_msg.append(f"The following namespaces are missing: {missing_projects}")

    if missing_pods:
        err_msg.append(
            f"The following namespaces have no pods deployed: {missing_pods}"
        )

    if failed_pods:
        err_msg.append(f"The following pods are failed: {failed_pods}")

    if err_msg:
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Pod status check succeeded.")


@pytest.mark.validate_argocd_reachable_edge_site
def test_validate_argocd_reachable_edge_site(openshift_dyn_client):
    namespace = "openshift-gitops"

    try:
        for route in Route.get(
            dyn_client=openshift_dyn_client,
            namespace=namespace,
            name="openshift-gitops-server",
        ):
            argocd_route_url = route.instance.spec.host
    except StopIteration:
        err_msg = f"Argocd url/route is missing in {namespace} namespace"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg

    logger.info("Check if argocd route/url on hub site is reachable")
    if not argocd_route_url:
        err_msg = f"Argocd url/route is missing in {namespace} namespace"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        final_argocd_url = f"{'https://'}{argocd_route_url}"
        logger.info(f"Argocd route/url : {final_argocd_url}")

    bearer_token = get_long_live_bearer_token(
        dyn_client=openshift_dyn_client,
        namespace=namespace,
        sub_string="argocd-dex-server-token",
    )
    if not bearer_token:
        err_msg = "Bearer token is missing for argocd-dex-server"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.debug(f"Argocd bearer token : {bearer_token}")

    argocd_route_response = get_site_response(
        site_url=final_argocd_url, bearer_token=bearer_token
    )

    logger.info(f"Argocd route response : {argocd_route_response}")

    if argocd_route_response.status_code != 200:
        err_msg = "Argocd is not reachable. Please check the deployment."
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Argocd is reachable")


@pytest.mark.validate_argocd_applications_health_edge_site
def test_validate_argocd_applications_health_edge_site(openshift_dyn_client):
    unhealthy_apps = []
    logger.info("Get all applications deployed by argocd on edge site")
    projects = ["openshift-gitops"]
    for project in projects:
        logger.info(f"PROJECT: {project}")
        for app in ArgoCD.get(dyn_client=openshift_dyn_client, namespace=project):
            app_name = app.instance.metadata.name
            app_health = app.instance.status.health.status
            app_sync = app.instance.status.sync.status

            logger.info(f"Status for {app_name} : {app_health} : {app_sync}")

            if "Healthy" != app_health or "Synced" != app_sync:
                logger.info(f"Dumping failed resources for app: {app_name}")
                unhealthy_apps.append(app_name)
                try:
                    for res in app.instance.status.resources:
                        if (
                            res.health and res.health.status != "Healthy"
                        ) or res.status != "Synced":
                            logger.info(f"\n{res}")
                except TypeError:
                    logger.info(f"No resources found for app: {app_name}")

    if unhealthy_apps:
        err_msg = "Some or all applications deployed on edge site are unhealthy"
        logger.error(f"FAIL: {err_msg}:\n{unhealthy_apps}")
        assert False, err_msg
    else:
        logger.info("PASS: All applications deployed on edge site are healthy.")
