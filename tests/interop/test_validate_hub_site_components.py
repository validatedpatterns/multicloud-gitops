import logging
import os

import pytest
import yaml
from ocp_resources.route import Route
from ocp_resources.storage_class import StorageClass
from validatedpatterns_tests.interop import components
from validatedpatterns_tests.interop.crd import ArgoCD, ManagedCluster
from validatedpatterns_tests.interop.edge_util import (
    get_long_live_bearer_token,
    get_site_response,
)

from . import __loggername__

logger = logging.getLogger(__loggername__)

oc = os.environ["HOME"] + "/oc_client/oc"

"""
Validate following multicloud-gitops components pods and endpoints on hub site (central server):

1) ACM (Advanced Cluster Manager) and self-registration
2) argocd
3) openshift operators
4) applications health (Applications deployed through argocd)
"""


@pytest.mark.test_validate_hub_site_components
def test_validate_hub_site_components(openshift_dyn_client):
    logger.info("Checking Openshift version on hub site")
    version_out = components.dump_openshift_version()
    logger.info(f"Openshift version:\n{version_out}")

    logger.info("Dump PVC and storageclass info")
    pvcs_out = components.dump_pvc()
    logger.info(f"PVCs:\n{pvcs_out}")

    for sc in StorageClass.get(dyn_client=openshift_dyn_client):
        logger.info(sc.instance)


@pytest.mark.validate_hub_site_reachable
def test_validate_hub_site_reachable(kube_config, openshift_dyn_client):
    logger.info("Check if hub site API end point is reachable")
    hub_api_url = kube_config.host
    if not hub_api_url:
        err_msg = "Hub site url is missing in kubeconfig file"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info(f"HUB api url : {hub_api_url}")

    bearer_token = get_long_live_bearer_token(
        dyn_client=openshift_dyn_client,
        namespace="openshift-gitops",
        sub_string="argocd-dex-server-token",
    )

    if not bearer_token:
        assert False, "Bearer token is missing for argocd-dex-server"

    hub_api_response = get_site_response(
        site_url=hub_api_url, bearer_token=bearer_token
    )

    if hub_api_response.status_code != 200:
        err_msg = "Hub site is not reachable. Please check the deployment."
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Hub site is reachable")


@pytest.mark.check_pod_status_hub
def test_check_pod_status(openshift_dyn_client):
    logger.info("Checking pod status")

    err_msg = []
    projects = [
        "openshift-operators",
        "open-cluster-management",
        "open-cluster-management-hub",
        "openshift-gitops",
        "vault",
    ]

    missing_projects = components.check_project_absense(openshift_dyn_client, projects)
    missing_pods = []
    failed_pods = []

    for project in projects:
        logger.info(f"Checking pods in namespace '{project}'")
        missing_pods += components.check_pod_absence(openshift_dyn_client, project)
        failed_pods += components.check_pod_status(openshift_dyn_client, projects)

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


@pytest.mark.validate_acm_self_registration_managed_clusters
def test_validate_acm_self_registration_managed_clusters(openshift_dyn_client):
    logger.info("Check ACM self registration for edge site")

    kubefile = os.getenv("KUBECONFIG_EDGE")
    kubefile_exp = os.path.expandvars(kubefile)
    with open(kubefile_exp) as stream:
        try:
            out = yaml.safe_load(stream)
            site_name = out["clusters"][0]["name"]
        except yaml.YAMLError:
            err_msg = "Failed to load kubeconfig file"
            logger.error(f"FAIL: {err_msg}")
            assert False, err_msg

    clusters = ManagedCluster.get(dyn_client=openshift_dyn_client, name=site_name)
    cluster = next(clusters)
    is_managed_cluster_joined, managed_cluster_status = cluster.self_registered

    logger.info(f"Cluster Managed : {is_managed_cluster_joined}")
    logger.info(f"Managed Cluster Status : {managed_cluster_status}")

    if not is_managed_cluster_joined:
        err_msg = f"{site_name} is not self registered"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info(f"PASS: {site_name} is self registered")


@pytest.mark.validate_argocd_reachable_hub_site
def test_validate_argocd_reachable_hub_site(openshift_dyn_client):
    namespace = "openshift-gitops"
    logger.info("Check if argocd route/url on hub site is reachable")
    try:
        for route in Route.get(
            dyn_client=openshift_dyn_client,
            namespace=namespace,
            name="openshift-gitops-server",
        ):
            argocd_route_url = route.instance.spec.host
    except StopIteration:
        err_msg = "Argocd url/route is missing in open-cluster-management namespace"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg

    final_argocd_url = f"{'http://'}{argocd_route_url}"
    logger.info(f"ACM route/url : {final_argocd_url}")

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
        err_msg = "Argocd is not reachable. Please check the deployment"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Argocd is reachable")


@pytest.mark.validate_argocd_applications_health_hub_site
def test_validate_argocd_applications_health_hub_site(openshift_dyn_client):
    unhealthy_apps = []
    logger.info("Get all applications deployed by argocd on hub site")
    projects = ["openshift-gitops", "multicloud-gitops-hub"]
    for project in projects:
        for app in ArgoCD.get(dyn_client=openshift_dyn_client, namespace=project):
            app_name = app.instance.metadata.name
            app_health = app.instance.status.health.status
            app_sync = app.instance.status.sync.status

            logger.info(f"Status for {app_name} : {app_health} : {app_sync}")

            if "Healthy" != app_health or "Synced" != app_sync:
                logger.info(f"Dumping failed resources for app: {app_name}")
                unhealthy_apps.append(app_name)
                for res in app.instance.status.resources:
                    if (
                        res.health and res.health.status != "Healthy"
                    ) or res.status != "Synced":
                        logger.info(f"\n{res}")
    if unhealthy_apps:
        err_msg = "Some or all applications deployed on hub site are unhealthy"
        logger.error(f"FAIL: {err_msg}:\n{unhealthy_apps}")
        assert False, err_msg
    else:
        logger.info("PASS: All applications deployed on hub site are healthy.")
