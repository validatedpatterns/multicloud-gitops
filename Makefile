BOOTSTRAP=1
SECRETS=~/values-secret.yaml
NAME=$(shell basename `pwd`)
TARGET_REPO=$(shell git remote show origin | grep Push | sed -e 's/.*URL:[[:space:]]*//' -e 's%:[a-z].*@%@%' -e 's%:%/%' -e 's%git@%https://%' )
# git branch --show-current is also available as of git 2.22, but we will use this for compatibility
TARGET_BRANCH=$(shell git rev-parse --abbrev-ref HEAD)
HUBCLUSTER_APPS_DOMAIN=$(shell oc get ingresses.config/cluster -o jsonpath={.spec.domain})

# --set values always take precedence over the contents of -f
HELM_OPTS=-f values-global.yaml -f $(SECRETS) --set main.git.repoURL="$(TARGET_REPO)" --set main.git.revision=$(TARGET_BRANCH) --set main.options.bootstrap=$(BOOTSTRAP) --set global.hubClusterDomain=$(HUBCLUSTER_APPS_DOMAIN)
TEST_OPTS= -f common/examples/values-secret.yaml -f values-global.yaml --set global.repoURL="https://github.com/pattern-clone/mypattern" --set main.git.repoURL="https://github.com/pattern-clone/mypattern" --set main.git.revision=main --set main.options.bootstrap=$(BOOTSTRAP) --set global.valuesDirectoryURL="https://github.com/pattern-clone/mypattern/raw/main" --set global.pattern="mypattern" --set global.namespace="pattern-namespace" --set global.hubClusterDomain=hub.example.com --set global.localClusterDomain=region.example.com
PATTERN_OPTS=-f common/examples/values-example.yaml

#  Makefiles that use this target must provide:
#  	PATTERN: The name of the pattern that is using it.  This will be used programmatically for the source namespace
#  	TARGET_NAMESPACE: target namespace to install the secret into
#  	COMPONENT: The component of the target namespace.  In industrial edge, factory or datacenter - and for the secret
#  		it needs to be datacenter because that's where the CI components run.
#  	SECRET_NAME: The name of the secret to manage
argosecret:
	PATTERN="$(PATTERN)" TARGET_NAMESPACE="$(TARGET_NAMESPACE)" COMPONENT="$(COMPONENT)" SECRET_NAME="$(SECRET_NAME)" common/scripts/secret.sh

#  Makefiles in the individual patterns should call these targets explicitly
#  e.g. from industrial-edge: make -f common/Makefile show
show:
	helm template common/install/ --name-template $(NAME) $(HELM_OPTS)

CHARTS=install clustergroup acm

test:
# Test that all values used by the chart are in values.yaml with the same defaults as the pattern
	@for t in $(CHARTS); do common/scripts/test.sh $$t naked ""; if [ $$? != 0 ]; then exit 1; fi; done
# Test the charts as the pattern would drive them
	@for t in $(CHARTS); do common/scripts/test.sh $$t normal "$(TEST_OPTS) $(PATTERN_OPTS)"; if [ $$? != 0 ]; then exit 1; fi; done

init:
	git submodule update --init --recursive

deploy:
	helm install $(NAME) common/install/ $(HELM_OPTS)

upgrade:
	helm upgrade $(NAME) common/install/ $(HELM_OPTS)

uninstall:
	helm uninstall $(NAME)

vault-init:
	common/scripts/vault-utils.sh vault_init common/pattern-vault.init

vault-unseal:
	common/scripts/vault-utils.sh vault_unseal common/pattern-vault.init

.phony: install test
