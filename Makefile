.PHONY: default
default: help

##@ Pattern tasks

help:
	@make -f common/Makefile MAKEFILE_LIST="Makefile common/Makefile" help

%:
	make -f common/Makefile $*

install: operator-deploy post-install ## installs the pattern and loads the secrets
	@echo "Installed"

post-install: ## Post-install tasks
	make load-secrets
	@echo "Done"

test:
	@make -f common/Makefile PATTERN_OPTS="-f values-global.yaml -f values-hub.yaml" test
