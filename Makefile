NAME ?= $(shell basename "`pwd`")

ifneq ($(origin TARGET_SITE), undefined)
  TARGET_SITE_OPT=--set main.clusterGroupName=$(TARGET_SITE)
endif

# Set this to true if you want to skip any origin validation
DISABLE_VALIDATE_ORIGIN ?= false
ifeq ($(DISABLE_VALIDATE_ORIGIN),true)
  VALIDATE_ORIGIN :=
else
  VALIDATE_ORIGIN := validate-origin
endif

# This variable can be set in order to pass additional helm arguments from the
# the command line. I.e. we can set things without having to tweak values files
EXTRA_HELM_OPTS ?=

# This variable can be set in order to pass additional ansible-playbook arguments from the
# the command line. I.e. we can set -vvv for more verbose logging
EXTRA_PLAYBOOK_OPTS ?=

# INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:394248
# or
# INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:394248,registry-proxy.engineering.redhat.com/rh-osbs/iib:394249
INDEX_IMAGES ?=

# git branch --show-current is also available as of git 2.22, but we will use this for compatibility
TARGET_BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)

#default to the branch remote
TARGET_ORIGIN ?= $(shell git config branch.$(TARGET_BRANCH).remote)

# The URL for the configured origin (could be HTTP/HTTPS/SSH)
TARGET_REPO_RAW := $(shell git ls-remote --get-url --symref $(TARGET_ORIGIN))

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
  # SSH agents are not created for public repos (repos with no secret token) by the patterns operator so we convert to HTTPS
  TARGET_REPO := $(shell echo "$(TARGET_REPO_RAW)" | sed 's/^git@\(.*\):\(.*\)/https:\/\/\1\/\2/')
  SECRET_OPTS :=
else
  TARGET_REPO := $(TARGET_REPO_RAW)
  SECRET_OPTS := --set main.tokenSecret=$(TOKEN_SECRET) --set main.tokenSecretNamespace=$(TOKEN_NAMESPACE)
endif

HELM_OPTS := -f values-global.yaml \
             --set main.git.repoURL="$(TARGET_REPO)" \
             --set main.git.revision=$(TARGET_BRANCH) \
             $(SECRET_OPTS) \
             $(TARGET_SITE_OPT) \
             $(UUID_HELM_OPTS) \
             $(EXTRA_HELM_OPTS)

# Helm does the right thing and fetches all the tags and detects the newest one
PATTERN_INSTALL_CHART ?= oci://quay.io/hybridcloudpatterns/pattern-install

##@ Pattern Common Tasks

.PHONY: help
help: ## This help message
	@echo "Pattern: $(NAME)"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^(\s|[a-zA-Z_0-9-])+:.*?##/ { printf "  \033[36m%-35s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

#  Makefiles in the individual patterns should call these targets explicitly
#  e.g. from industrial-edge: make -f common/Makefile show
.PHONY: show
show: ## show the starting template without installing it
	helm template $(PATTERN_INSTALL_CHART) --name-template $(NAME) $(HELM_OPTS)

preview-all: ## (EXPERIMENTAL) Previews all applications on hub and managed clusters
	@echo "NOTE: This is just a tentative approximation of rendering all hub and managed clusters templates"
	@common/scripts/preview-all.sh $(TARGET_REPO) $(TARGET_BRANCH)

preview-%:
	$(eval CLUSTERGROUP ?= $(shell yq ".main.clusterGroupName" values-global.yaml))
	@common/scripts/preview.sh $(CLUSTERGROUP) $* $(TARGET_REPO) $(TARGET_BRANCH)

.PHONY: operator-deploy
operator-deploy operator-upgrade: validate-prereq $(VALIDATE_ORIGIN) validate-cluster ## runs helm install
	@common/scripts/deploy-pattern.sh $(NAME) $(PATTERN_INSTALL_CHART) $(HELM_OPTS)

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
		ansible-playbook $(EXTRA_PLAYBOOK_OPTS) rhvp.cluster_utils.iib_ci; \
	else \
		echo "No INDEX_IMAGES defined. Bailing out"; \
		exit 1; \
	fi

.PHONY: token-kubeconfig
token-kubeconfig: ## Create a local ~/.kube/config with password (not usually needed)
	common/scripts/write-token-kubeconfig.sh

##@ Validation Tasks

# If the main repoUpstreamURL field is set, then we need to check against
# that and not target_repo
.PHONY: validate-origin
validate-origin: ## verify the git origin is available
	@echo "Checking repository:"
	$(eval UPSTREAMURL := $(shell yq -r '.main.git.repoUpstreamURL // (.main.git.repoUpstreamURL = "")' values-global.yaml))
	@if [ -z "$(UPSTREAMURL)" ]; then\
		echo -n "  $(TARGET_REPO) - branch '$(TARGET_BRANCH)': ";\
		git ls-remote --exit-code --heads $(TARGET_REPO) $(TARGET_BRANCH) >/dev/null &&\
			echo "OK" || (echo "NOT FOUND"; exit 1);\
	else\
		echo "Upstream URL set to: $(UPSTREAMURL)";\
		echo -n "  $(UPSTREAMURL) - branch '$(TARGET_BRANCH)': ";\
		git ls-remote --exit-code --heads $(UPSTREAMURL) $(TARGET_BRANCH) >/dev/null &&\
			echo "OK" || (echo "NOT FOUND"; exit 1);\
	fi

.PHONY: validate-cluster
validate-cluster: ## Do some cluster validations before installing
	@echo "Checking cluster:"
	@echo -n "  cluster-info: "
	@oc cluster-info >/dev/null && echo "OK" || (echo "Error"; exit 1)
	@echo -n "  storageclass: "
	@if [ `oc get storageclass -o go-template='{{printf "%d\n" (len .items)}}'` -eq 0 ]; then\
		echo "WARNING: No storageclass found";\
	else\
		echo "OK";\
	fi


.PHONY: validate-schema
validate-schema: ## validates values files against schema in common/clustergroup
	$(eval VAL_PARAMS := $(shell for i in ./values-*.yaml; do echo -n "$${i} "; done))
	@echo -n "Validating clustergroup schema of: "
	@set -e; for i in $(VAL_PARAMS); do echo -n " $$i"; helm template oci://quay.io/hybridcloudpatterns/clustergroup $(HELM_OPTS) -f "$${i}" >/dev/null; done
	@echo

.PHONY: validate-prereq
validate-prereq: ## verify pre-requisites
	$(eval GLOBAL_PATTERN := $(shell yq -r .global.pattern values-global.yaml))
	@if [ $(NAME) != $(GLOBAL_PATTERN) ]; then\
		echo "";\
		echo "WARNING: folder directory is \"$(NAME)\" and global.pattern is set to \"$(GLOBAL_PATTERN)\"";\
		echo "this can create problems. Please make sure they are the same!";\
		echo "";\
	fi
	@if [ ! -f /run/.containerenv ]; then\
	  echo "Checking prerequisites:";\
	  echo -n "  Check for python-kubernetes: ";\
	  if ! ansible -m ansible.builtin.command -a "{{ ansible_python_interpreter }} -c 'import kubernetes'" localhost > /dev/null 2>&1; then echo "Not found"; exit 1; fi;\
	  echo "OK";\
	  echo -n "  Check for kubernetes.core collection: ";\
	  if ! ansible-galaxy collection list | grep kubernetes.core > /dev/null 2>&1; then echo "Not found"; exit 1; fi;\
	  echo "OK";\
	else\
		if [ -f values-global.yaml ]; then\
			OUT=`yq -r '.main.multiSourceConfig.enabled // (.main.multiSourceConfig.enabled = "false")' values-global.yaml`;\
			if [ "$${OUT,,}" = "false" ]; then\
				echo "You must set \".main.multiSourceConfig.enabled: true\" in your 'values-global.yaml' file";\
				echo "because your common subfolder is the slimmed down version with no helm charts in it";\
				exit 1;\
			fi;\
		fi;\
	fi

.PHONY: argo-healthcheck
argo-healthcheck: ## Checks if all argo applications are synced
	@echo "Checking argo applications"
	$(eval APPS := $(shell oc get applications.argoproj.io -A -o jsonpath='{range .items[*]}{@.metadata.namespace}{","}{@.metadata.name}{"\n"}{end}'))
	@NOTOK=0; \
	for i in $(APPS); do\
		n=`echo "$${i}" | cut -f1 -d,`;\
		a=`echo "$${i}" | cut -f2 -d,`;\
		STATUS=`oc get -n "$${n}" applications.argoproj.io/"$${a}" -o jsonpath='{.status.sync.status}'`;\
		if [[ $$STATUS != "Synced" ]]; then\
			NOTOK=$$(( $${NOTOK} + 1));\
		fi;\
		HEALTH=`oc get -n "$${n}" applications.argoproj.io/"$${a}" -o jsonpath='{.status.health.status}'`;\
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

.PHONY: qe-tests
qe-tests: ## Runs the tests that QE runs
	@set -e; if [ -f ./tests/interop/run_tests.sh ]; then \
		pushd ./tests/interop; ./run_tests.sh; popd; \
	else \
		echo "No ./tests/interop/run_tests.sh found skipping"; \
	fi

.PHONY: super-linter
super-linter: ## Runs super linter locally
	rm -rf .mypy_cache
	podman run -e RUN_LOCAL=true -e USE_FIND_ALGORITHM=true	\
					-e VALIDATE_ANSIBLE=false \
					-e VALIDATE_BASH=false \
					-e VALIDATE_CHECKOV=false \
					-e VALIDATE_DOCKERFILE_HADOLINT=false \
					-e VALIDATE_JSCPD=false \
					-e VALIDATE_JSON_PRETTIER=false \
					-e VALIDATE_MARKDOWN_PRETTIER=false \
					-e VALIDATE_KUBERNETES_KUBECONFORM=false \
					-e VALIDATE_PYTHON_PYLINT=false \
					-e VALIDATE_SHELL_SHFMT=false \
					-e VALIDATE_TEKTON=false \
					-e VALIDATE_YAML=false \
					-e VALIDATE_YAML_PRETTIER=false \
					$(DISABLE_LINTERS) \
					-v $(PWD):/tmp/lint:rw,z \
					-w /tmp/lint \
					ghcr.io/super-linter/super-linter:slim-v7

.PHONY: deploy upgrade legacy-deploy legacy-upgrade
deploy upgrade legacy-deploy legacy-upgrade:
	@echo "UNSUPPORTED TARGET: please switch to 'operator-deploy'"; exit 1
