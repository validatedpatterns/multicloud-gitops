import logging
import os
import subprocess

import pytest
from ocp_resources.namespace import Namespace
from ocp_resources.pod import Pod
from ocp_resources.route import Route
from openshift.dynamic.exceptions import NotFoundError

from . import __loggername__
from .crd import ArgoCD
from .edge_util import get_long_live_bearer_token, get_site_response

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
    version_out = subprocess.run(["oc", "version"], capture_output=True)
    version_out = version_out.stdout.decode("utf-8")
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

    bearer_token = get_long_live_bearer_token(dyn_client=openshift_dyn_client)
    if not bearer_token:
        assert False, "Bearer token is missing for hub site"

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
    failed_pods = []
    missing_pods = []
    missing_projects = []
    projects = [
        "openshift-operators",
        "open-cluster-management-agent",
        "open-cluster-management-agent-addon",
        "openshift-gitops",
    ]

    for project in projects:
        # Check for missing project
        try:
            namespaces = Namespace.get(dyn_client=openshift_dyn_client, name=project)
            next(namespaces)
        except NotFoundError:
            missing_projects.append(project)
            continue
        # Check for absence of pods in project
        try:
            pods = Pod.get(dyn_client=openshift_dyn_client, namespace=project)
            pod = next(pods)
        except StopIteration:
            missing_pods.append(project)
            continue

    for project in projects:
        pods = Pod.get(dyn_client=openshift_dyn_client, namespace=project)
        logger.info(f"Checking pods in namespace '{project}'")
        for pod in pods:
            for container in pod.instance.status.containerStatuses:
                logger.info(
                    f"{pod.instance.metadata.name} : {container.name} :"
                    f" {container.state}"
                )
                if container.state.terminated:
                    if container.state.terminated.reason != "Completed":
                        logger.info(
                            f"Pod {pod.instance.metadata.name} in"
                            f" {pod.instance.metadata.namespace} namespace is"
                            " FAILED:"
                        )
                        failed_pods.append(pod.instance.metadata.name)
                        logger.info(describe_pod(project, pod.instance.metadata.name))
                        logger.info(
                            get_log_output(
                                project,
                                pod.instance.metadata.name,
                                container.name,
                            )
                        )
                elif not container.state.running:
                    logger.info(
                        f"Pod {pod.instance.metadata.name} in"
                        f" {pod.instance.metadata.namespace} namespace is"
                        " FAILED:"
                    )
                    failed_pods.append(pod.instance.metadata.name)
                    logger.info(describe_pod(project, pod.instance.metadata.name))
                    logger.info(
                        get_log_output(
                            project, pod.instance.metadata.name, container.name
                        )
                    )

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


def describe_pod(project, pod):
    cmd_out = subprocess.run(
        [oc, "describe", "pod", "-n", project, pod], capture_output=True
    )
    if cmd_out.stdout:
        return cmd_out.stdout.decode("utf-8")
    else:
        assert False, cmd_out.stderr


def get_log_output(project, pod, container):
    cmd_out = subprocess.run(
        [oc, "logs", "-n", project, pod, "-c", container], capture_output=True
    )
    if cmd_out.stdout:
        return cmd_out.stdout.decode("utf-8")
    else:
        assert False, cmd_out.stderr


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
        sub_string="openshift-gitops-argocd-server-token",
    )
    if not bearer_token:
        err_msg = f"Bearer token is missing for argocd-server in {namespace} namespace"
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
    namespace = "oepnshift-gitops"

    argocd_apps_status = dict()
    logger.info("Get all applications deployed by argocd on edge site")

    for app in ArgoCD.get(dyn_client=openshift_dyn_client, namespace=namespace):
        app_name = app.instance.metadata.name
        app_health = app.health
        argocd_apps_status[app_name] = app_health
        logger.info(f"Health status of {app_name} is: {app_health}")

    if False in (argocd_apps_status.values()):
        err_msg = f"Some or all applications deployed on edge site are Degraded/Unhealthy: {argocd_apps_status}"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: All applications deployed on edge site are healthy.")
