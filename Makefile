.PHONY: default
default: help

.PHONY: help
# No need to add a comment here as help is described in common/
help:
	@printf "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) common/Makefile | sort | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s :)\n"

%:
	make -f common/Makefile $*

install: operator-deploy post-install ## installs the pattern, inits the vault and loads the secrets
	echo "Installed"

legacy-install: legacy-deploy post-install ## install the pattern the old way without the operator
	echo "Installed"

post-install: ## Post-install tasks - vault init and load-secrets
	@if grep -v -e '^\s\+#' "values-hub.yaml" | grep -q -e "insecureUnsealVaultInsideCluster:\s\+true"; then \
	  echo "Skipping 'make vault-init' as we're unsealing the vault from inside the cluster"; \
	else \
	  make vault-init; \
	fi
	make load-secrets
	echo "Done"

test:
	@make -f common/Makefile PATTERN_OPTS="-f values-global.yaml -f values-hub.yaml" test
