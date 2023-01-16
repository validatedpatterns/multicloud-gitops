# This filter takes a bunch of acm secrets that represent the remote clusters
# (Usually it is all secrets that are labeled with:
# "apps.open-cluster-management.io/secret-type=acm-cluster")

# These secrets are usually in the form of:
# data:
#   config: ewogIC...
#   name: bWNnLW9uZQ==
#   server: aHR0cHM6Ly9hcGkubWNnLW9uZS5ibHVlcHJpbnRzLnJoZWNvZW5nLmNvbTo2NDQz

# The filter parses the secret (name, server, config) and returns a dictionary of secrets in the
# following form:
# <acm-name>:
#  name: <acm-name>
#  cluster_fqdn: <fqdn-without-api-prefix>
#  server_api: https://api.<cluster_fqdn>:6443
#  bearerToken: <bearerToken to access remote cluster>
#  tlsClientConfig: <tlsClientConfig in ACM config field>
#  vault_path: "hub" when it is the ACM hub or <fqdn-without-api-prefix> in the other cases

import json
from base64 import b64decode


# These are the labels of an acm secret
# labels:
#   apps.open-cluster-management.io/cluster-name: local-cluster
#   apps.open-cluster-management.io/cluster-server: api.mcg-hub.blueprints.rhecoeng.com
#   apps.open-cluster-management.io/secret-type: acm-cluster
def get_cluster_name(secret):
    if "metadata" in secret and "labels" in secret["metadata"]:
        return secret["metadata"]["labels"].get(
            "apps.open-cluster-management.io/cluster-name", None
        )
    return None


def is_cluster_a_hub(name):
    if name == "local-cluster":
        return True
    return False


def get_cluster_fqdn(secret):
    if "metadata" in secret and "labels" in secret["metadata"]:
        server = secret["metadata"]["labels"].get(
            "apps.open-cluster-management.io/cluster-server", None
        )
        # It is rather hard to override this in an OCP deployment so we are
        # okay in just dropping 'api.'
        return server.removeprefix("api.")
    return None


def parse_acm_secrets(secrets):
    ret = {}
    for secret in secrets:
        cluster = get_cluster_name(secret)
        if cluster is None:
            continue

        ret[cluster] = {}
        name = b64decode(secret["data"]["name"])
        ret[cluster]["name"] = name
        ret[cluster]["server_api"] = b64decode(secret["data"]["server"])
        fqdn = get_cluster_fqdn(secret)
        ret[cluster]["cluster_fqdn"] = fqdn
        if is_cluster_a_hub(name):
            ret[cluster]["vault_path"] = "hub"
        else:
            ret[cluster]["vault_path"] = fqdn

        config = b64decode(secret["data"]["config"])
        parsed_config = json.loads(config)
        ret[cluster]["bearerToken"] = parsed_config["bearerToken"]
        ret[cluster]["tlsClientConfig"] = parsed_config["tlsClientConfig"]

    return ret


class FilterModule:
    def filters(self):
        return {"parse_acm_secrets": parse_acm_secrets}
