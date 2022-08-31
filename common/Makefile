NAME=$(shell basename `pwd`)
# This is to ensure that whether we start with a git@ or https:// URL, we end up with an https:// URL
# This is because we expect to use tokens for repo authentication as opposed to SSH keys
TARGET_ORIGIN ?= origin
TARGET_REPO=$(shell git remote show $(TARGET_ORIGIN) | grep Push | sed -e 's/.*URL:[[:space:]]*//' -e 's%^git@%%' -e 's%^https://%%' -e 's%:%/%' -e 's%^%https://%')
# git branch --show-current is also available as of git 2.22, but we will use this for compatibility
TARGET_BRANCH=$(shell git rev-parse --abbrev-ref HEAD)
HUBCLUSTER_APPS_DOMAIN=$(shell oc get ingresses.config/cluster -o jsonpath={.spec.domain})

# --set values always take precedence over the contents of -f
HELM_OPTS=-f values-global.yaml --set main.git.repoURL="$(TARGET_REPO)" --set main.git.revision=$(TARGET_BRANCH) \
	--set global.hubClusterDomain=$(HUBCLUSTER_APPS_DOMAIN)
TEST_OPTS= -f common/examples/values-secret.yaml -f values-global.yaml --set global.repoURL="https://github.com/pattern-clone/mypattern" \
	--set main.git.repoURL="https://github.com/pattern-clone/mypattern" --set main.git.revision=main --set global.pattern="mypattern" \
	--set global.namespace="pattern-namespace" --set global.hubClusterDomain=hub.example.com --set global.localClusterDomain=region.example.com \
	--set "clusterGroup.imperative.jobs[0].name"="test" --set "clusterGroup.imperative.jobs[0].playbook"="ansible/test.yml" \
	--set clusterGroup.insecureUnsealVaultInsideCluster=true
PATTERN_OPTS=-f common/examples/values-example.yaml
EXECUTABLES=git helm oc ansible

.PHONY: help
help: ## This help message
	@printf "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s :)\n"

#  Makefiles in the individual patterns should call these targets explicitly
#  e.g. from industrial-edge: make -f common/Makefile show
show: ## show the starting template without installing it
	helm template common/install/ --name-template $(NAME) $(HELM_OPTS)

CHARTS=$(shell find . -type f -iname 'Chart.yaml' -exec dirname "{}"  \; | sed -e 's/.\///')
test: ## run helm tests
# Test that all values used by the chart are in values.yaml with the same defaults as the pattern
	@for t in $(CHARTS); do common/scripts/test.sh $$t naked ""; if [ $$? != 0 ]; then exit 1; fi; done
# Test the charts as the pattern would drive them
	@for t in $(CHARTS); do common/scripts/test.sh $$t normal "$(TEST_OPTS) $(PATTERN_OPTS)"; if [ $$? != 0 ]; then exit 1; fi; done

helmlint: ## run helm lint
	@for t in $(CHARTS); do helm lint $(TEST_OPTS) $(PATTERN_OPTS) $$t; if [ $$? != 0 ]; then exit 1; fi; done

API_URL ?= https://raw.githubusercontent.com/hybrid-cloud-patterns/ocp-schemas/main/openshift/4.10/
KUBECONFORM_SKIP ?= -skip 'CustomResourceDefinition'
# We need to skip 'CustomResourceDefinition' as openapi2jsonschema seems to be unable to generate them ATM
kubeconform: ## run helm kubeconform
	@for t in $(CHARTS); do helm template $(TEST_OPTS) $(PATTERN_OPTS) $$t | kubeconform -strict $(KUBECONFORM_SKIP) -verbose -schema-location $(API_URL); if [ $$? != 0 ]; then exit 1; fi; done

validate-prereq: ## verify pre-requisites
	@for t in $(EXECUTABLES); do if ! which $$t > /dev/null 2>&1; then echo "No $$t in PATH"; exit 1; fi; done
	@echo "Prerequisites checked '$(EXECUTABLES)': OK"
	@ansible -m ansible.builtin.command -a "{{ ansible_python_interpreter }} -c 'import kubernetes'" localhost > /dev/null 2>&1
	@echo "Python kubernetes module: OK"
	@echo -n "Check for kubernetes.core collection: "
	@if ! ansible-galaxy collection list | grep kubernetes.core > /dev/null 2>&1; then echo "Not found"; exit 1; fi
	@echo "OK"

validate-origin: ## verify the git origin is available
	@echo Checking repo $(TARGET_REPO) - branch $(TARGET_BRANCH)
	@git ls-remote --exit-code --heads $(TARGET_REPO) $(TARGET_BRANCH) >/dev/null && \
		echo "$(TARGET_REPO) - $(TARGET_BRANCH) exists" || \
		(echo "$(TARGET_BRANCH) not found in $(TARGET_REPO)"; exit 1)

# Default targets are "deploy" and "upgrade"; they can "move" to whichever install mechanism should be default.
# legacy-deploy and legacy-upgrade should be present so that patterns don't need to depend on "deploy" and "upgrade"
# pointing to one place or another, and don't need to change when they do (provide they use either legacy- or operator-
# targets)
deploy upgrade legacy-deploy legacy-upgrade: validate-prereq validate-origin ## deploys the pattern
	helm upgrade --install $(NAME) common/install/ $(HELM_OPTS)

operator-deploy operator-upgrade: validate-origin ## runs helm install
	helm upgrade --install $(NAME) common/operator-install/ $(HELM_OPTS)

uninstall: ## runs helm uninstall
	helm uninstall $(NAME)

vault-init: ## inits, unseals and configured the vault
	common/scripts/vault-utils.sh vault_init common/pattern-vault.init
	common/scripts/vault-utils.sh vault_unseal common/pattern-vault.init
	common/scripts/vault-utils.sh vault_secrets_init common/pattern-vault.init

vault-unseal: ## unseals the vault
	common/scripts/vault-utils.sh vault_unseal common/pattern-vault.init

load-secrets: ## loads the secrets into the vault
	common/scripts/vault-utils.sh push_secrets common/pattern-vault.init

super-linter: ## Runs super linter locally
	podman run -e RUN_LOCAL=true -e USE_FIND_ALGORITHM=true	\
					-e VALIDATE_BASH=false \
					-e VALIDATE_JSCPD=false \
					-e VALIDATE_KUBERNETES_KUBEVAL=false \
					-e VALIDATE_YAML=false \
					$(DISABLE_LINTERS) \
					-v $(PWD):/tmp/lint:rw,z docker.io/github/super-linter:slim-v4

ansible-lint: ## run ansible lint on ansible/ folder
	podman run -it -v $(PWD):/workspace:rw,z --workdir /workspace --entrypoint "/usr/local/bin/ansible-lint" quay.io/ansible/creator-ee:latest  "-vvv" "ansible/"

.phony: install test

