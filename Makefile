.PHONY: default
default: help

.PHONY: help
# No need to add a comment here as help is described in common/
help:
	@printf "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) common/Makefile | sort | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s :)\n"

%:
	make -f common/Makefile $*

install: deploy ## installs the pattern, inits the vault and loads the secrets
	@if grep -v -e '^\s\+#' "values-hub.yaml" | grep -q -e "insecureUnsealVaultInsideCluster:\s\+true"; then \
	  echo "Skipping 'make vault-init' as we're unsealing the vault from inside the cluster"; \
	else \
	  make vault-init; \
	fi
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
	@for t in "$(wildcard charts/*/*)"; do helm lint $$t; if [ $$? != 0 ]; then exit 1; fi; done

.PHONY: kubeval
kubeconform:
	make -f common/Makefile CHARTS="$(wildcard charts/all/*)" kubeconform
	make -f common/Makefile CHARTS="$(wildcard charts/hub/*)" kubeconform

super-linter: ## Runs super linter locally
	podman run -e RUN_LOCAL=true -e USE_FIND_ALGORITHM=true	\
					-e VALIDATE_BASH=false \
					-e VALIDATE_JSCPD=false \
					-e VALIDATE_KUBERNETES_KUBEVAL=false \
					-e VALIDATE_YAML=false \
					-e VALIDATE_ANSIBLE=false \
					-v $(PWD):/tmp/lint:rw,z docker.io/github/super-linter:slim-v4
