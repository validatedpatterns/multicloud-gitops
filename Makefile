BOOTSTRAP=1

.PHONY: default
default: show

%:
	make -f common/Makefile $*

install: deploy
	make vault-init
	make load-secrets
	echo "Installed"

common-test:
	make -C common -f common/Makefile test

test:
	make -f common/Makefile CHARTS="$(wildcard charts/all/*)" PATTERN_OPTS="-f values-global.yaml -f values-hub.yaml" test
	make -f common/Makefile CHARTS="$(wildcard charts/hub/*)" PATTERN_OPTS="-f values-global.yaml -f values-hub.yaml" test
	#make -f common/Makefile CHARTS="$(wildcard charts/region/*)" PATTERN_OPTS="-f values-region-one.yaml" test

helmlint:
	# no regional charts just yet: "$(wildcard charts/region/*)"
	@for t in "$(wildcard charts/all/*)" "$(wildcard charts/hub/*)"; do helm lint $$t; if [ $$? != 0 ]; then exit 1; fi; done

