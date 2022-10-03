#!/bin/bash

# helm template (even with --dry-run) can interact with the cluster
# This won't protect us if a user has ~/.kube
# Also call helm template with a non existing --kubeconfig while we're at it
unset KUBECONFIG

target=$1
name=$(echo $1 | sed -e s@/@-@g -e s@charts-@@)
TEST_VARIANT="$2"
CHART_OPTS="$3"

TESTDIR=tests
REFERENCE=${TESTDIR}/${name}-${TEST_VARIANT}.expected.yaml
OUTPUT=${TESTDIR}/.${name}-${TEST_VARIANT}.expected.yaml
#REFERENCE=${TESTDIR}/${name}.expected.yaml
#OUTPUT=${TESTDIR}/.${name}.expected.yaml

echo "Testing $1 chart (${TEST_VARIANT})" >&2
helm template --kubeconfig /tmp/doesnotexistever $target --name-template $name ${CHART_OPTS} > ${OUTPUT}
rc=$?
if [ $rc -ne 0 ]; then
    echo "FAIL on helm template $target --name-template $name ${CHART_OPTS}"
    exit 1
fi
if [ ! -e ${REFERENCE} ]; then
    cp ${OUTPUT} ${REFERENCE}
fi
diff -u ${REFERENCE}  ${OUTPUT}
rc=$?

if [ $TEST_VARIANT = normal -a $rc = 0 ]; then
    # Another method of finding variables missing from values.yaml, eg.
    # -    name: -datacenter
    # +    name: pattern-name-datacenter
    diff -u ${TESTDIR}/${name}-naked.expected.yaml ${TESTDIR}/${name}-normal.expected.yaml | sed 's/20[0-9][0-9]-[09][0-9].*//' > ${OUTPUT}.variant

    if [ ! -e ${REFERENCE}.variant ]; then
	cp ${OUTPUT}.variant ${REFERENCE}.variant
    fi

    diff -u ${REFERENCE}.variant  ${OUTPUT}.variant
    rc=$?
fi

if [ $rc = 0 ]; then
    rm -f ${OUTPUT}
    rm -f ${OUTPUT}.variant
    echo "PASS on $target $TEST_VARIANT with opts [$CHART_OPTS]"
else
    echo "FAIL on $target $TEST_VARIANT with opts [$CHART_OPTS]"
fi

exit $rc
