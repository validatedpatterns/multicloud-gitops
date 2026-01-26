import json
import os
import subprocess
import sys
from datetime import datetime

from junitparser import JUnitXml

# Use os.environ.get() with fallback to avoid KeyError
home_dir = os.environ.get("HOME", "/tmp")
oc = os.path.join(home_dir, "oc_client", "oc")

ci_badge = {
    "schemaVersion": 1,
    "label": "Community test",
    "message": "",
    "color": "red",
    "openshiftVersion": "",
    "infraProvider": os.environ.get("INFRA_PROVIDER"),
    "patternName": os.environ.get("PATTERN_NAME"),
    "patternRepo": "",
    "patternBranch": "",
    "date": datetime.today().strftime("%Y-%m-%d"),
    "testSource": "Community",
    "debugInfo": None,
}


def get_openshift_version():
    """Get OpenShift version from cluster.

    Returns:
        tuple: (full_version, major_minor) on success
        None: on any error
    """
    try:
        version_ret = subprocess.run(
            [oc, "version", "-o", "json"], capture_output=True, check=False
        )
        if version_ret.returncode != 0:
            print(f"Error running oc version: {version_ret.stderr.decode('utf-8')}")
            return None
        version_out = version_ret.stdout.decode("utf-8")
        openshift_version = json.loads(version_out)["openshiftVersion"]
        major_minor = ".".join(openshift_version.split(".")[:-1])
        return openshift_version, major_minor
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        print(f"Error getting OpenShift version: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    versions = get_openshift_version()
    if versions is None:
        print("Failed to get OpenShift version, exiting")
        sys.exit(1)

    ci_badge["openshiftVersion"] = versions[0]

    pattern_repo = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True
    )
    pattern_branch = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True
    )

    ci_badge["patternRepo"] = pattern_repo.stdout.strip()
    ci_badge["patternBranch"] = pattern_branch.stdout.strip()

    # Check each xml file for failures
    results_dir = os.environ.get("WORKSPACE")
    if results_dir is None:
        print("WORKSPACE environment variable is not set, exiting")
        sys.exit(1)

    if not os.path.isdir(results_dir):
        print(f"WORKSPACE directory does not exist: {results_dir}")
        sys.exit(1)

    failures = 0

    for file in os.listdir(results_dir):
        if file.startswith("test_") and file.endswith(".xml"):
            with open(os.path.join(results_dir, file), "r") as result_file:
                xml = JUnitXml.fromfile(result_file)
                for suite in xml:
                    for case in suite:
                        if case.result:
                            failures += 1

    # Determine badge color from results
    if failures == 0:
        ci_badge["color"] = "green"

    # For now we assume `message` is the same as patternBranch
    ci_badge["message"] = ci_badge["patternBranch"]

    # Validate required environment variables for filename
    pattern_shortname = os.environ.get("PATTERN_SHORTNAME")
    infra_provider = os.environ.get("INFRA_PROVIDER")

    if not pattern_shortname:
        print("PATTERN_SHORTNAME environment variable is not set, exiting")
        sys.exit(1)
    if not infra_provider:
        print("INFRA_PROVIDER environment variable is not set, exiting")
        sys.exit(1)

    ci_badge_json_basename = (
        pattern_shortname
        + "-"
        + infra_provider
        + "-"
        + versions[1]
        + "-stable-badge.json"
    )
    ci_badge_json_filename = os.path.join(results_dir, ci_badge_json_basename)
    print(f"Creating CI badge file at: {ci_badge_json_filename}")

    with open(ci_badge_json_filename, "w") as ci_badge_file:
        json.dump(ci_badge, ci_badge_file)
