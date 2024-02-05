from ocp_resources.resource import NamespacedResource, Resource


class ArgoCD(NamespacedResource):
    """
    OpenShift ArgoCD / GitOps object.
    """

    api_group = "argoproj.io"
    api_version = NamespacedResource.ApiVersion.V1ALPHA1
    kind = "Application"

    @property
    def health(self):
        """
        Check the health of of the argocd application
        :return: boolean
        """

        if (
            self.instance.status.operationState.phase == "Succeeded"
            and self.instance.status.health.status == "Healthy"
        ):
            return True
        return False


class ManagedCluster(Resource):
    """
    OpenShift Managed Cluster object.
    """

    api_version = "cluster.open-cluster-management.io/v1"

    @property
    def self_registered(self):
        """
        Check if managed cluster is self registered in to ACM running on hub site
        :param name: (str) name of managed cluster
        :param namespace: namespace
        :return: Tuple of boolean and dict on success
        """
        is_joined = False
        status = dict()

        for condition in self.instance.status.conditions:
            if condition["type"] == "HubAcceptedManagedCluster":
                status["HubAcceptedManagedCluster"] = condition["status"]
            elif condition["type"] == "ManagedClusterConditionAvailable":
                status["ManagedClusterConditionAvailable"] = condition["status"]
            elif condition["type"] == "ManagedClusterJoined":
                is_joined = True
                status["ManagedClusterJoined"] = condition["status"]

        return is_joined, status
