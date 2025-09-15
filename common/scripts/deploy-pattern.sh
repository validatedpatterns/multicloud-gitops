#!/bin/bash
set -o pipefail

RUNS=20
WAIT=15
# Retry five times because the CRD might not be fully installed yet
echo -n "Installing pattern: "
for i in $(seq 1 ${RUNS}); do \
    exec 3>&1 4>&2
    OUT=$( { helm template --include-crds --name-template $* 2>&4 | oc apply -f- 2>&4 1>&3; } 4>&1 3>&1)
    ret=$?
    exec 3>&- 4>&-
    if [ ${ret} -eq 0 ]; then
        break;
    else
        echo -n "."
        sleep "${WAIT}"
    fi
done

# All the runs failed
if [ ${i} -eq ${RUNS} ]; then
    echo "Installation failed [${i}/${RUNS}]. Error:"
    echo "${OUT}"
    exit 1
fi
echo "Done"
