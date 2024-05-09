NAME ?= $(shell basename "`pwd`")

ifneq ($(origin TARGET_SITE), undefined)
  TARGET_SITE_OPT=--set main.clusterGroupName=$(TARGET_SITE)
endif

# This variable can be set in order to pass additional helm arguments from the
# the command line. I.e. we can set things without having to tweak values files
EXTRA_HELM_OPTS ?=

# INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:394248
# or
# INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:394248,registry-proxy.engineering.redhat.com/rh-osbs/iib:394249
INDEX_IMAGES ?=

TARGET_ORIGIN ?= origin
# This is to ensure that whether we start with a git@ or https:// URL, we end up with an https:// URL
# This is because we expect to use tokens for repo authentication as opposed to SSH keys
TARGET_REPO=$(shell git ls-remote --get-url --symref $(TARGET_ORIGIN) | sed -e 's/.*URL:[[:space:]]*//' -e 's%^git@%%' -e 's%^https://%%' -e 's%:%/%' -e 's%^%https://%')
# git branch --show-current is also available as of git 2.22, but we will use this for compatibility
TARGET_BRANCH=$(shell git rev-parse --abbrev-ref HEAD)

UUID_FILE ?= ~/.config/validated-patterns/pattern-uuid
UUID_HELM_OPTS ?=

# --set values always take precedence over the contents of -f
ifneq ("$(wildcard $(UUID_FILE))","")
	UUID := $(shell cat $(UUID_FILE))
	UUID_HELM_OPTS := --set main.analyticsUUID=$(UUID)
endif

# Set the secret name *and* its namespace when deploying from private repositories
# The format of said secret is documented here: https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/#repositories
TOKEN_SECRET ?=
TOKEN_NAMESPACE ?=

ifeq ($(TOKEN_SECRET),)
  HELM_OPTS=-f values-global.yaml --set main.git.repoURL="$(TARGET_REPO)" --set main.git.revision=$(TARGET_BRANCH) $(TARGET_SITE_OPT) $(UUID_HELM_OPTS) $(EXTRA_HELM_OPTS)
else
  # When we are working with a private repository we do not escape the git URL as it might be using an ssh secret which does not use https://
  TARGET_CLEAN_REPO=$(shell git ls-remote --get-url --symref $(TARGET_ORIGIN))
  HELM_OPTS=-f values-global.yaml --set main.tokenSecret=$(TOKEN_SECRET) --set main.tokenSecretNamespace=$(TOKEN_NAMESPACE) --set main.git.repoURL="$(TARGET_CLEAN_REPO)" --set main.git.revision=$(TARGET_BRANCH) $(TARGET_SITE_OPT) $(UUID_HELM_OPTS) $(EXTRA_HELM_OPTS)
endif


##@ Pattern Common Tasks

.PHONY: help
help: ## This help message
	@echo "Pattern: $(NAME)"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^(\s|[a-zA-Z_0-9-])+:.*?##/ { printf "  \033[36m%-35s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

#  Makefiles in the individual patterns should call these targets explicitly
#  e.g. from industrial-edge: make -f common/Makefile show
.PHONY: show
show: ## show the starting template without installing it
	helm template common/operator-install/ --name-template $(NAME) $(HELM_OPTS)

preview-all: ## (EXPERIMENTAL) Previews all applications on hub and managed clusters
	@echo "NOTE: This is just a tentative approximation of rendering all hub and managed clusters templates"
	@common/scripts/preview-all.sh $(TARGET_REPO) $(TARGET_BRANCH)

preview-%:
	$(eval CLUSTERGROUP ?= $(shell yq ".main.clusterGroupName" values-global.yaml))
	@common/scripts/preview.sh $(CLUSTERGROUP) $* $(TARGET_REPO) $(TARGET_BRANCH)

.PHONY: operator-deploy
operator-deploy operator-upgrade: validate-prereq validate-origin validate-cluster ## runs helm install
	@set -e -o pipefail
	# Retry five times because the CRD might not be fully installed yet
	for i in {1..5}; do \
		helm template --include-crds --name-template $(NAME) common/operator-install/ $(HELM_OPTS) | oc apply -f- && break || sleep 10; \
	done

.PHONY: uninstall
uninstall: ## runs helm uninstall
	$(eval CSV := $(shell oc get subscriptions -n openshift-operators openshift-gitops-operator -ojsonpath={.status.currentCSV}))
	helm uninstall $(NAME)
	@oc delete csv -n openshift-operators $(CSV)

.PHONY: load-secrets
load-secrets: ## loads the secrets into the backend determined by values-global setting
	common/scripts/process-secrets.sh $(NAME)

.PHONY: legacy-load-secrets
legacy-load-secrets: ## loads the secrets into vault (only)
	common/scripts/vault-utils.sh push_secrets $(NAME)

.PHONY: secrets-backend-vault
secrets-backend-vault: ## Edits values files to use default Vault+ESO secrets config
	common/scripts/set-secret-backend.sh vault
	common/scripts/manage-secret-app.sh vault present
	common/scripts/manage-secret-app.sh golang-external-secrets present
	common/scripts/manage-secret-namespace.sh validated-patterns-secrets absent
	@git diff --exit-code || echo "Secrets backend set to vault, please review changes, commit, and push to activate in the pattern"

.PHONY: secrets-backend-kubernetes
secrets-backend-kubernetes: ## Edits values file to use Kubernetes+ESO secrets config
	common/scripts/set-secret-backend.sh kubernetes
	common/scripts/manage-secret-namespace.sh validated-patterns-secrets present
	common/scripts/manage-secret-app.sh vault absent
	common/scripts/manage-secret-app.sh golang-external-secrets present
	@git diff --exit-code || echo "Secrets backend set to kubernetes, please review changes, commit, and push to activate in the pattern"

.PHONY: secrets-backend-none
secrets-backend-none: ## Edits values files to remove secrets manager + ESO
	common/scripts/set-secret-backend.sh none
	common/scripts/manage-secret-app.sh vault absent
	common/scripts/manage-secret-app.sh golang-external-secrets absent
	common/scripts/manage-secret-namespace.sh validated-patterns-secrets absent
	@git diff --exit-code || echo "Secrets backend set to none, please review changes, commit, and push to activate in the pattern"

.PHONY: load-iib
load-iib: ## CI target to install Index Image Bundles
	@set -e; if [ x$(INDEX_IMAGES) != x ]; then \
		ansible-playbook common/ansible/playbooks/iib-ci/iib-ci.yaml; \
	else \
		echo "No INDEX_IMAGES defined. Bailing out"; \
		exit 1; \
	fi


##@ Validation Tasks

# We only check the remote ssh git branch's existance if we're not running inside a container
# as getting ssh auth working inside a container seems a bit brittle
.PHONY: validate-origin
validate-origin: ## verify the git origin is available
	@echo "Checking repository:"
	@echo -n "  $(TARGET_REPO) - branch '$(TARGET_BRANCH)': "
	@git ls-remote --exit-code --heads $(TARGET_REPO) $(TARGET_BRANCH) >/dev/null &&\
		echo "OK" || (echo "NOT FOUND"; exit 1)

.PHONY: validate-cluster
validate-cluster: ## Do some cluster validations before installing
	@echo "Checking cluster:"
	@echo -n "  cluster-info: "
	@oc cluster-info >/dev/null && echo "OK" || (echo "Error"; exit 1)
	@echo -n "  storageclass: "
	@if [ `oc get storageclass -o go-template='{{printf "%d\n" (len .items)}}'` -eq 0 ]; then\
		echo "None Found"; exit 1;\
	else\
		echo "OK";\
	fi


.PHONY: validate-schema
validate-schema: ## validates values files against schema in common/clustergroup
	$(eval VAL_PARAMS := $(shell for i in ./values-*.yaml; do echo -n "$${i} "; done))
	@echo -n "Validating clustergroup schema of: "
	@set -e; for i in $(VAL_PARAMS); do echo -n " $$i"; helm template common/clustergroup $(HELM_OPTS) -f "$${i}" >/dev/null; done
	@echo

.PHONY: validate-prereq
validate-prereq: ## verify pre-requisites
	@if [ ! -f /run/.containerenv ]; then\
	  echo "Checking prerequisites:";\
	  for t in $(EXECUTABLES); do if ! which $$t > /dev/null 2>&1; then echo "No $$t in PATH"; exit 1; fi; done;\
	  echo "  Check for '$(EXECUTABLES)': OK";\
	  echo -n "  Check for python-kubernetes: ";\
	  if ! ansible -m ansible.builtin.command -a "{{ ansible_python_interpreter }} -c 'import kubernetes'" localhost > /dev/null 2>&1; then echo "Not found"; exit 1; fi;\
	  echo "OK";\
	  echo -n "  Check for kubernetes.core collection: ";\
	  if ! ansible-galaxy collection list | grep kubernetes.core > /dev/null 2>&1; then echo "Not found"; exit 1; fi;\
	  echo "OK";\
	else\
	  echo "Skipping prerequisites check as we're running inside a container";\
	fi

.PHONY: argo-healthcheck
argo-healthcheck: ## Checks if all argo applications are synced
	@echo "Checking argo applications"
	$(eval APPS := $(shell oc get applications -A -o jsonpath='{range .items[*]}{@.metadata.namespace}{","}{@.metadata.name}{"\n"}{end}'))
	@NOTOK=0; \
	for i in $(APPS); do\
		n=`echo "$${i}" | cut -f1 -d,`;\
		a=`echo "$${i}" | cut -f2 -d,`;\
		STATUS=`oc get -n "$${n}" application/"$${a}" -o jsonpath='{.status.sync.status}'`;\
		if [[ $$STATUS != "Synced" ]]; then\
			NOTOK=$$(( $${NOTOK} + 1));\
		fi;\
		HEALTH=`oc get -n "$${n}" application/"$${a}" -o jsonpath='{.status.health.status}'`;\
		if [[ $$HEALTH != "Healthy" ]]; then\
			NOTOK=$$(( $${NOTOK} + 1));\
		fi;\
		echo "$${n} $${a} -> Sync: $${STATUS} - Health: $${HEALTH}";\
	done;\
	if [ $${NOTOK} -gt 0 ]; then\
	    echo "Some applications are not synced or are unhealthy";\
	    exit 1;\
	fi


##@ Test and Linters Tasks

CHARTS=$(shell find . -type f -iname 'Chart.yaml' -exec dirname "{}"  \; | grep -v examples | sed -e 's/.\///')
# Section related to tests and linting
TEST_OPTS= -f values-global.yaml \
	--set global.repoURL="https://github.com/pattern-clone/mypattern" \
	--set main.git.repoURL="https://github.com/pattern-clone/mypattern" \
	--set main.git.revision=main --set global.pattern="mypattern" \
	--set global.namespace="pattern-namespace" \
	--set global.hubClusterDomain=apps.hub.example.com \
	--set global.localClusterDomain=apps.region.example.com \
	--set global.clusterDomain=region.example.com \
	--set global.clusterVersion="4.12" \
	--set global.clusterPlatform=aws \
	--set "clusterGroup.imperative.jobs[0].name"="test" \
	--set "clusterGroup.imperative.jobs[0].playbook"="ansible/test.yml"
PATTERN_OPTS=-f common/examples/values-example.yaml
EXECUTABLES=git helm oc ansible

.PHONY: test
test: ## run helm tests
	@for t in $(CHARTS); do common/scripts/test.sh $$t all "$(TEST_OPTS)"; if [ $$? != 0 ]; then exit 1; fi; done

.PHONY: helmlint
helmlint: ## run helm lint
	@for t in $(CHARTS); do common/scripts/lint.sh $$t $(TEST_OPTS); if [ $$? != 0 ]; then exit 1; fi; done

API_URL ?= https://raw.githubusercontent.com/hybrid-cloud-patterns/ocp-schemas/main/openshift/4.10/
KUBECONFORM_SKIP ?= -skip 'CustomResourceDefinition,ClusterIssuer,CertManager,Certificate,ArgoCD'

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
