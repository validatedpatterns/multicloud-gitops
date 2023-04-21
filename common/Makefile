NAME=$(shell basename "`pwd`")
ifneq ($(origin TARGET_SITE), undefined)
  TARGET_SITE_OPT=--set main.clusterGroupName=$(TARGET_SITE)
endif

# INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:394248
INDEX_IMAGES ?= 
INDEX_OPTIONS=$(shell echo $(INDEX_IMAGES) | tr ',' '\n' | awk -F: 'match($$1,"/"){print "--set main.extraParameters."NR".name=clusterGroup.indexImages."NR".image --set main.extraParameters."NR".value="$$1":"$$2}')

TARGET_ORIGIN ?= origin
# This is to ensure that whether we start with a git@ or https:// URL, we end up with an https:// URL
# This is because we expect to use tokens for repo authentication as opposed to SSH keys
TARGET_REPO=$(shell git ls-remote --get-url --symref $(TARGET_ORIGIN) | sed -e 's/.*URL:[[:space:]]*//' -e 's%^git@%%' -e 's%^https://%%' -e 's%:%/%' -e 's%^%https://%')
# git branch --show-current is also available as of git 2.22, but we will use this for compatibility
TARGET_BRANCH=$(shell git rev-parse --abbrev-ref HEAD)

# --set values always take precedence over the contents of -f
HELM_OPTS=-f values-global.yaml --set main.git.repoURL="$(TARGET_REPO)" --set main.git.revision=$(TARGET_BRANCH) $(TARGET_SITE_OPT) $(INDEX_OPTIONS)

##@ Pattern Common Tasks

.PHONY: help
help: ## This help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^(\s|[a-zA-Z_0-9-])+:.*?##/ { printf "  \033[36m%-35s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

#  Makefiles in the individual patterns should call these targets explicitly
#  e.g. from industrial-edge: make -f common/Makefile show
.PHONY: show
show: ## show the starting template without installing it
	helm template common/operator-install/ --name-template $(NAME) $(HELM_OPTS)

# Only call helm install if the CRD is missing. If it already exists just
# push the templated files.
# The reason we have two helm template calls in the else branch is to avoid
# warnings when the chart gets applied the first time, but the resources were
# created first via the VP operator's UI
.PHONY: operator-deploy
operator-deploy operator-upgrade: validate-prereq validate-origin ## runs helm install
	@set -e; if ! oc get crds patterns.gitops.hybrid-cloud-patterns.io >/dev/null 2>&1; then \
	  echo "Running helm:"; \
	  helm upgrade --install $(NAME) common/operator-install/ $(HELM_OPTS); \
	else \
	  echo "Reapplying helm chart:"; \
	  helm template --name-template $(NAME) common/operator-install/ $(HELM_OPTS) | oc apply set-last-applied --create-annotation -f-; \
	  helm template --name-template $(NAME) common/operator-install/ $(HELM_OPTS) | oc apply -f-; \
	fi

.PHONY: uninstall
uninstall: ## runs helm uninstall
	$(eval CSV := $(shell oc get subscriptions -n openshift-operators openshift-gitops-operator -ojsonpath={.status.currentCSV}))
	helm uninstall $(NAME)
	@oc delete csv -n openshift-operators $(CSV)

.PHONY: load-secrets
load-secrets: ## loads the secrets into the vault
	common/scripts/vault-utils.sh push_secrets $(NAME)

##@ Validation Tasks

# We only check the remote ssh git branch's existance if we're not running inside a container
# as getting ssh auth working inside a container seems a bit brittle
.PHONY: validate-origin
validate-origin: ## verify the git origin is available
	@echo "Checking repository:"
	@echo -n "  $(TARGET_REPO) - branch $(TARGET_BRANCH): "
	@if [ ! -f /run/.containerenv ]; then\
		git ls-remote --exit-code --heads $(TARGET_REPO) $(TARGET_BRANCH) >/dev/null &&\
				echo "OK" ||\
				(echo "NOT FOUND"; exit 1);\
	else\
		echo "Running inside a container: Skipping git ssh checks";\
	fi

.PHONY: validate-schema
validate-schema: ## validates values files against schema in common/clustergroup
	$(eval VAL_PARAMS := $(shell for i in ./values-*.yaml; do echo -n "$${i} "; done))
	@echo -n "Validating clustergroup schema of: "
	@set -e; for i in $(VAL_PARAMS); do echo -n " $$i"; helm template common/clustergroup $(HELM_OPTS) -f "$${i}" >/dev/null; done
	@echo

.PHONY: validate-prereq
validate-prereq: ## verify pre-requisites
	@echo "Checking prerequisites:"
	@for t in $(EXECUTABLES); do if ! which $$t > /dev/null 2>&1; then echo "No $$t in PATH"; exit 1; fi; done
	@echo "  Check for '$(EXECUTABLES)': OK"
	@echo -n "  Check for python-kubernetes: "
	@if ! ansible -m ansible.builtin.command -a "{{ ansible_python_interpreter }} -c 'import kubernetes'" localhost > /dev/null 2>&1; then echo "Not found"; exit 1; fi
	@echo "OK"
	@echo -n "  Check for kubernetes.core collection: "
	@if ! ansible-galaxy collection list | grep kubernetes.core > /dev/null 2>&1; then echo "Not found"; exit 1; fi
	@echo "OK"

##@ Test and Linters Tasks

CHARTS=$(shell find . -type f -iname 'Chart.yaml' -exec dirname "{}"  \; | grep -v examples | sed -e 's/.\///')
# Section related to tests and linting
TEST_OPTS= -f values-global.yaml --set global.repoURL="https://github.com/pattern-clone/mypattern" \
	--set main.git.repoURL="https://github.com/pattern-clone/mypattern" --set main.git.revision=main --set global.pattern="mypattern" \
	--set global.namespace="pattern-namespace" --set global.hubClusterDomain=apps.hub.example.com --set global.localClusterDomain=apps.region.example.com --set global.clusterDomain=region.example.com\
	--set "clusterGroup.imperative.jobs[0].name"="test" --set "clusterGroup.imperative.jobs[0].playbook"="ansible/test.yml"
PATTERN_OPTS=-f common/examples/values-example.yaml
EXECUTABLES=git helm oc ansible

.PHONY: test
test: ## run helm tests
	@for t in $(CHARTS); do common/scripts/test.sh $$t all "$(TEST_OPTS)"; if [ $$? != 0 ]; then exit 1; fi; done

.PHONY: helmlint
helmlint: ## run helm lint
	@for t in $(CHARTS); do common/scripts/lint.sh $$t $(TEST_OPTS); if [ $$? != 0 ]; then exit 1; fi; done

API_URL ?= https://raw.githubusercontent.com/hybrid-cloud-patterns/ocp-schemas/main/openshift/4.10/
KUBECONFORM_SKIP ?= -skip 'CustomResourceDefinition,ClusterIssuer,CertManager,Certificate'
# We need to skip 'CustomResourceDefinition' as openapi2jsonschema seems to be unable to generate them ATM
.PHONY: kubeconform
kubeconform: ## run helm kubeconform
	@for t in $(CHARTS); do helm template $(TEST_OPTS) $(PATTERN_OPTS) $$t | kubeconform -strict $(KUBECONFORM_SKIP) -verbose -schema-location $(API_URL); if [ $$? != 0 ]; then exit 1; fi; done

.PHONY: super-linter
super-linter: ## Runs super linter locally
	rm -rf .mypy_cache
	podman run -e RUN_LOCAL=true -e USE_FIND_ALGORITHM=true	\
					-e VALIDATE_BASH=false \
					-e VALIDATE_JSCPD=false \
					-e VALIDATE_KUBERNETES_KUBECONFORM=false \
					-e VALIDATE_YAML=false \
					-e VALIDATE_ANSIBLE=false \
					-e VALIDATE_DOCKERFILE_HADOLINT=false \
					-e VALIDATE_TEKTON=false \
					$(DISABLE_LINTERS) \
					-v $(PWD):/tmp/lint:rw,z \
					-w /tmp/lint \
					docker.io/github/super-linter:slim-v5

.PHONY: ansible-lint
ansible-lint: ## run ansible lint on ansible/ folder
	podman run -it -v $(PWD):/workspace:rw,z --workdir /workspace --env ANSIBLE_CONFIG=./ansible/ansible.cfg \
		--entrypoint "/usr/local/bin/ansible-lint" quay.io/ansible/creator-ee:latest  "-vvv" "ansible/"

.PHONY: ansible-unittest
ansible-unittest: ## run ansible unit tests
	pytest -r a --fulltrace --color yes ansible/tests/unit/test_*.py

.PHONY: deploy upgrade legacy-deploy legacy-upgrade
deploy upgrade legacy-deploy legacy-upgrade:
	@echo "UNSUPPORTED TARGET: please switch to 'operator-deploy'"; exit 1
