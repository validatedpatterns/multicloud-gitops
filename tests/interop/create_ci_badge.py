import json
import os
import subprocess
from datetime import datetime

from junitparser import JUnitXml

oc = os.environ["HOME"] + "/oc_client/oc"

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
    try:
        version_ret = subprocess.run([oc, "version", "-o", "json"], capture_output=True)
        version_out = version_ret.stdout.decode("utf-8")
        openshift_version = json.loads(version_out)["openshiftVersion"]
        major_minor = ".".join(openshift_version.split(".")[:-1])
        return openshift_version, major_minor
    except KeyError as e:
        print("KeyError:" + str(e))
        return None


if __name__ == "__main__":
    versions = get_openshift_version()
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
    failures = 0

    for file in os.listdir(results_dir):
        if file.startswith("test_") and file.endswith(".xml"):
            with open(os.path.join(results_dir, file), "r") as result_file:  # type: ignore
                xml = JUnitXml.fromfile(result_file)  # type: ignore
                for suite in xml:
                    for case in suite:
                        if case.result:
                            failures += 1

    # Determine badge color from results
    if failures == 0:
        ci_badge["color"] = "green"

    # For now we assume `message` is the same as patternBranch
    ci_badge["message"] = ci_badge["patternBranch"]

    ci_badge_json_basename = (
        os.environ.get("PATTERN_SHORTNAME")  # type: ignore
        + "-"
        + os.environ.get("INFRA_PROVIDER")
        + "-"
        + versions[1]
        + "-stable-badge.json"
    )
    ci_badge_json_filename = os.path.join(results_dir, ci_badge_json_basename)  # type: ignore
    print(f"Creating CI badge file at: {ci_badge_json_filename}")

    with open(ci_badge_json_filename, "w") as ci_badge_file:
        json.dump(ci_badge, ci_badge_file)
