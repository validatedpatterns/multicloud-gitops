#!/bin/bash
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
helm template $target --name-template $name ${CHART_OPTS} > ${OUTPUT}
rc=$?
if [ $rc -ne 0 ]; then
    echo "FAIL on helm template $target --name-template $name ${CHART_OPTS}"
    exit 1
fi
#cp ${OUTPUT} ${REFERENCE}
if [ ! -e ${REFERENCE} ]; then
    touch ${REFERENCE}
fi
diff -u ${REFERENCE}  ${OUTPUT}
rc=$?
if [ $rc = 0 ]; then
    rm -f ${OUTPUT}
fi

if [ $TEST_VARIANT = normal -a $rc = 0 ]; then
    # Another method of finding variables missing from values.yaml, eg.
    # -    name: -datacenter
    # +    name: pattern-name-datacenter
    # Alas we can't make it fatal because there *should* be some differences
    diff -u ${TESTDIR}/${name}-naked.expected.yaml ${TESTDIR}/${name}-normal.expected.yaml
fi

if [ $rc = 0 ]; then
	echo "PASS on $target $TEST_VARIANT with opts [$CHART_OPTS]"
else
	echo "FAIL on $target $TEST_VARIANT with opts [$CHART_OPTS]"
fi

exit $rc
